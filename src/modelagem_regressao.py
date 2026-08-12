"""
Modelagem estatística: identifica QUAIS variáveis socioeconômicas estão associadas à
mortalidade por DCNT e COM QUE FORÇA/DIREÇÃO, controlando pelas demais variáveis
simultaneamente (o que a correlação simples não faz).

Método: Regressão Binomial Negativa com offset de população.
- Por que Binomial Negativa e não regressão linear comum? Porque a variável resposta é uma
  CONTAGEM de óbitos (não uma variável contínua normal), e frequentemente tem mais variância
  do que uma distribuição de Poisson permitiria (super-dispersão) — muito comum em dados de
  saúde pública por município.
- O "offset" de log(população) faz o modelo trabalhar em termos de TAXA por habitante, em vez
  de contagem bruta — essencial, já que municípios têm tamanhos muito diferentes.
- Os coeficientes são convertidos em "Razão de Taxas de Incidência" (IRR): um IRR de 1.20 para
  uma variável significa que, mantendo as outras constantes, um aumento de 1 desvio-padrão
  nessa variável está associado a 20% mais óbitos.

Pré-requisitos:
    python src/coleta_ibge.py
    python src/tratamento_mortalidade.py

Uso:
    python src/modelagem_regressao.py
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Lista ampliada — o script usa automaticamente só as que existirem na base consolidada.
# Agrupadas por "dimensão" para facilitar decidir o que tirar em caso de multicolinearidade alta:
#   econômica: pib_per_capita, renda_per_capita, salario_medio_admissao
#   desigualdade: gini, taxa_pobreza
#   educação: taxa_analfabetismo, idhm_educacao
#   mercado de trabalho: saldo_empregos, taxa_rotatividade
#   urbanização/estrutura: taxa_urbanizacao_pct
#   síntese (cuidado: já incorpora renda+educação+longevidade, correlaciona com quase tudo acima): idhm
VARIAVEIS_CANDIDATAS = [
    "pib_per_capita", "renda_per_capita", "gini", "taxa_pobreza",
    "taxa_analfabetismo", "taxa_urbanizacao_pct", "idhm",
    "saldo_empregos", "salario_medio_admissao", "taxa_rotatividade",
]

LIMIAR_VIF_ALERTA = 5  # VIF acima disso costuma indicar multicolinearidade preocupante


def carregar_dados():
    mortalidade = pd.read_csv(PROCESSED_DIR / "mortalidade_dcnt_sc_tratado.csv")

    # Prioriza a base consolidada (Fase de expansão); cai para a básica se ela não existir ainda
    caminho_completo = RAW_DIR / "indicadores_socioeconomicos_completos.csv"
    caminho_basico = RAW_DIR / "indicadores_socioeconomicos_sc.csv"
    if caminho_completo.exists():
        socioeconomico = pd.read_csv(caminho_completo)
        print(f"[OK] Usando base socioeconômica consolidada: {caminho_completo.name}")
    else:
        socioeconomico = pd.read_csv(caminho_basico)
        print(f"[AVISO] Base consolidada não encontrada — usando apenas: {caminho_basico.name}\n"
              f"Rode juntar_variaveis_socioeconomicas.py para incluir Atlas Brasil e CAGED.")

    mort_agg = (
        mortalidade.groupby(["codigo_ibge", "grupo_dcnt"])["obitos"]
        .sum()
        .reset_index()
    )
    base = mort_agg.merge(socioeconomico, on="codigo_ibge", how="left")
    return base


def checar_multicolinearidade(subset: pd.DataFrame, colunas_z: list[str], variaveis_originais: list[str]) -> list[str]:
    """
    Calcula o VIF (Variance Inflation Factor) de cada variável preditora. VIF alto indica que
    a variável está sendo "explicada" pelas outras do modelo — os coeficientes ficam instáveis
    e pouco confiáveis nesse caso. Retorna a lista de variáveis que ficaram dentro do limiar
    aceitável (as descartadas são reportadas, não removidas automaticamente — a decisão de
    qual retirar fica com quem está interpretando, olhando as dimensões conceituais).
    """
    X = subset[colunas_z].copy()
    X = sm.add_constant(X)

    vifs = {}
    for i, col in enumerate(colunas_z):
        try:
            vifs[col] = variance_inflation_factor(X.values, i + 1)  # +1 pula a constante
        except Exception:
            vifs[col] = np.nan

    problematicas = [var for var, col in zip(variaveis_originais, colunas_z)
                     if vifs.get(col, 0) and vifs[col] > LIMIAR_VIF_ALERTA]

    if problematicas:
        print(f"[ALERTA DE MULTICOLINEARIDADE] Variáveis com VIF > {LIMIAR_VIF_ALERTA}: {problematicas}")
        for var, col in zip(variaveis_originais, colunas_z):
            marcador = " ⚠️" if vifs.get(col, 0) and vifs[col] > LIMIAR_VIF_ALERTA else ""
            print(f"    VIF({var}) = {vifs.get(col, float('nan')):.2f}{marcador}")
        print("    Considere remover uma das variáveis do mesmo grupo conceitual (ver comentário "
              "no topo do script) e rodar novamente.\n")

    return problematicas


def padronizar(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Padroniza (z-score) as variáveis preditoras para que os coeficientes sejam comparáveis
    entre si, independente da escala original de cada uma (PIB em milhares, urbanização em %, etc.)."""
    df = df.copy()
    for col in colunas:
        media, desvio = df[col].mean(), df[col].std()
        if desvio and desvio > 0:
            df[f"{col}_z"] = (df[col] - media) / desvio
        else:
            df[f"{col}_z"] = 0
    return df


def rodar_modelo_por_grupo(base: pd.DataFrame, grupo: str, variaveis_disponiveis: list[str]):
    subset = base[base["grupo_dcnt"] == grupo].copy()
    subset = subset.dropna(subset=["populacao_censo2022", "obitos"] + variaveis_disponiveis)

    if len(subset) < 15:
        print(f"[AVISO] {grupo}: apenas {len(subset)} municípios com dados completos — "
              f"resultado pouco confiável, pulando modelo.")
        return None

    subset = padronizar(subset, variaveis_disponiveis)
    colunas_z = [f"{v}_z" for v in variaveis_disponiveis]

    checar_multicolinearidade(subset, colunas_z, variaveis_disponiveis)

    formula = "obitos ~ " + " + ".join(colunas_z)
    offset = np.log(subset["populacao_censo2022"])

    try:
        # smf.negativebinomial estima o parâmetro de dispersão (alpha) via máxima
        # verossimilhança a partir dos próprios dados, em vez de fixá-lo em 1 — mais correto
        # estatisticamente do que usar a família NegativeBinomial do GLM com alpha padrão.
        modelo = smf.negativebinomial(
            formula=formula,
            data=subset,
            offset=offset,
        ).fit(disp=0)
    except Exception as e:
        print(f"[ERRO] Falha ao ajustar modelo para {grupo}: {e}")
        return None

    resultados = []
    for var, var_z in zip(variaveis_disponiveis, colunas_z):
        coef = modelo.params.get(var_z)
        p_valor = modelo.pvalues.get(var_z)
        if coef is None:
            continue
        irr = np.exp(coef)
        resultados.append({
            "grupo_dcnt": grupo,
            "variavel": var,
            "coeficiente": round(coef, 4),
            "irr": round(irr, 3),
            "p_valor": round(p_valor, 4),
            "significativo_5pct": p_valor < 0.05,
            "interpretacao": (
                f"+1 desvio-padrão em {var} está associado a "
                f"{'aumento' if irr > 1 else 'redução'} de {abs(irr - 1) * 100:.1f}% "
                f"na taxa de mortalidade por {grupo}"
                + ("" if p_valor < 0.05 else " (NÃO significativo — interpretar com cautela)")
            ),
        })

    return pd.DataFrame(resultados)


def main():
    base = carregar_dados()

    variaveis_disponiveis = [v for v in VARIAVEIS_CANDIDATAS if v in base.columns]
    faltando = [v for v in VARIAVEIS_CANDIDATAS if v not in base.columns]
    if faltando:
        print(f"[AVISO] Variáveis não encontradas na base (serão ignoradas): {faltando}")
        print("Se quiser incluí-las, veja data/raw/COMO_ADICIONAR_ATLAS_BRASIL.md, "
              "data/raw/COMO_BAIXAR_RAIS_CAGED.md, ou rode juntar_variaveis_socioeconomicas.py")

    if not variaveis_disponiveis:
        raise ValueError("Nenhuma variável preditora disponível. Rode coleta_ibge.py primeiro.")

    print(f"\nVariáveis usadas no modelo: {variaveis_disponiveis}\n")

    todos_resultados = []
    for grupo in base["grupo_dcnt"].dropna().unique():
        print(f"\n=== {grupo} ===")
        resultado = rodar_modelo_por_grupo(base, grupo, variaveis_disponiveis)
        if resultado is not None:
            todos_resultados.append(resultado)
            print(resultado[["variavel", "irr", "p_valor", "significativo_5pct"]].to_string(index=False))

    if todos_resultados:
        tabela_final = pd.concat(todos_resultados, ignore_index=True)
        saida = OUTPUTS_DIR / "tabela_regressao_dcnt.csv"
        tabela_final.to_csv(saida, index=False, encoding="utf-8-sig")
        print(f"\n[OK] Tabela de regressão completa salva em: {saida}")

        print("\n--- Resumo em linguagem simples ---")
        for _, linha in tabela_final[tabela_final["significativo_5pct"]].iterrows():
            print(f"- {linha['interpretacao']}")


if __name__ == "__main__":
    main()
