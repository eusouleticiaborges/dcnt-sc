"""
Análise exploratória: cruza mortalidade, internações/letalidade hospitalar (4 grupos de DCNT)
com indicadores socioeconômicos dos municípios de Santa Catarina.

Pré-requisitos:
    python src/coleta_ibge.py
    python src/tratamento_mortalidade.py
    python src/tratamento_internacoes.py

Uso:
    python src/analise_exploratoria.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

sns.set_style("whitegrid")


def carregar_bases():
    mortalidade = pd.read_csv(PROCESSED_DIR / "mortalidade_dcnt_sc_tratado.csv")
    internacoes = pd.read_csv(PROCESSED_DIR / "internacoes_dcnt_sc_tratado.csv")
    socioeconomico = pd.read_csv(RAW_DIR / "indicadores_socioeconomicos_sc.csv")
    return mortalidade, internacoes, socioeconomico


def calcular_indicadores(mortalidade, internacoes, socioeconomico) -> pd.DataFrame:
    """
    Agrega por município x grupo de DCNT (somando o período) e calcula:
    - taxa de mortalidade por 100k hab.
    - taxa de internação por 100k hab.
    - taxa de letalidade hospitalar (%)
    """
    mort_agg = (
        mortalidade.groupby(["codigo_ibge", "grupo_dcnt"])["obitos"]
        .sum()
        .reset_index()
    )

    intern_agg = (
        internacoes.groupby(["codigo_ibge", "grupo_dcnt"])[["internacoes", "obitos_hospitalares"]]
        .sum()
        .reset_index()
    )

    base = mort_agg.merge(intern_agg, on=["codigo_ibge", "grupo_dcnt"], how="outer")
    base = base.merge(socioeconomico, on="codigo_ibge", how="left")

    base[["obitos", "internacoes", "obitos_hospitalares"]] = base[
        ["obitos", "internacoes", "obitos_hospitalares"]
    ].fillna(0)

    base["taxa_mortalidade_100k"] = base["obitos"] / base["populacao_censo2022"] * 100_000
    base["taxa_internacao_100k"] = base["internacoes"] / base["populacao_censo2022"] * 100_000

    # Letalidade só faz sentido onde houve internação (evita divisão por zero)
    base["taxa_letalidade_pct"] = base.apply(
        lambda r: (r["obitos_hospitalares"] / r["internacoes"] * 100) if r["internacoes"] > 0 else None,
        axis=1,
    )

    return base


def grafico_mortalidade_por_grupo(base: pd.DataFrame):
    """Compara a taxa média de mortalidade entre os 4 grupos de DCNT."""
    resumo = base.groupby("grupo_dcnt")["taxa_mortalidade_100k"].mean().sort_values(ascending=False)

    plt.figure(figsize=(8, 5))
    sns.barplot(x=resumo.values, y=resumo.index, hue=resumo.index, palette="mako", legend=False)
    plt.xlabel("Taxa média de mortalidade (por 100 mil hab.)")
    plt.ylabel("")
    plt.title("Mortalidade média por grupo de DCNT — municípios de SC")
    plt.tight_layout()
    caminho = OUTPUTS_DIR / "mortalidade_por_grupo.png"
    plt.savefig(caminho, dpi=150)
    plt.close()
    print(f"[OK] Gráfico salvo: {caminho}")


def grafico_dispersao_pib(base: pd.DataFrame, grupo: str):
    subset = base[base["grupo_dcnt"] == grupo]

    plt.figure(figsize=(9, 6))
    sns.scatterplot(data=subset, x="pib_per_capita", y="taxa_mortalidade_100k", alpha=0.7)
    plt.xlabel("PIB per capita (R$)")
    plt.ylabel("Taxa de mortalidade (por 100 mil hab.)")
    plt.title(f"{grupo}: mortalidade x PIB per capita — municípios de SC")
    plt.tight_layout()
    nome_arquivo = f"dispersao_pib_{grupo.lower().replace(' ', '_').replace('ó','o').replace('â','a')}.png"
    caminho = OUTPUTS_DIR / nome_arquivo
    plt.savefig(caminho, dpi=150)
    plt.close()
    print(f"[OK] Gráfico salvo: {caminho}")


def tabela_correlacoes(base: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada grupo de DCNT, calcula a correlação de Spearman entre PIB per capita
    e cada um dos 3 indicadores de desfecho.
    """
    resultados = []
    indicadores = ["taxa_mortalidade_100k", "taxa_internacao_100k", "taxa_letalidade_pct"]

    for grupo in base["grupo_dcnt"].dropna().unique():
        subset = base[base["grupo_dcnt"] == grupo]
        for indicador in indicadores:
            dados_validos = subset.dropna(subset=["pib_per_capita", indicador])
            if len(dados_validos) < 5:
                continue
            r, p = stats.spearmanr(dados_validos["pib_per_capita"], dados_validos[indicador])
            resultados.append({
                "grupo_dcnt": grupo,
                "indicador": indicador,
                "correlacao_spearman": round(r, 3),
                "p_valor": round(p, 4),
                "significativo_5pct": p < 0.05,
            })

    tabela = pd.DataFrame(resultados)
    caminho = OUTPUTS_DIR / "tabela_correlacoes.csv"
    tabela.to_csv(caminho, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Tabela de correlações salva em: {caminho}")
    print(tabela.to_string(index=False))
    return tabela


def main():
    mortalidade, internacoes, socioeconomico = carregar_bases()
    base = calcular_indicadores(mortalidade, internacoes, socioeconomico)

    saida = PROCESSED_DIR / "base_final_cruzada.csv"
    base.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"[OK] Base cruzada salva em: {saida}")

    grafico_mortalidade_por_grupo(base)
    for grupo in base["grupo_dcnt"].dropna().unique():
        grafico_dispersao_pib(base, grupo)

    tabela_correlacoes(base)


if __name__ == "__main__":
    main()
