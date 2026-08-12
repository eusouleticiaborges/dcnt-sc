"""
Análise de redução de dimensionalidade (PCA) e segmentação (cluster) dos municípios de SC
com base no perfil socioeconômico completo.

Por que isso importa aqui: com muitas variáveis socioeconômicas candidatas (IBGE + Atlas Brasil
+ RAIS/CAGED), várias medem dimensões parecidas. A PCA resume essas variáveis em poucos "eixos"
compostos (componentes principais), que capturam a maior parte da variação entre municípios sem
a redundância — e podem substituir as variáveis originais na regressão quando o VIF estiver alto.

A análise de cluster agrupa municípios com perfil socioeconômico parecido, o que ajuda a
responder de forma mais interpretável (e visual, no Power BI) perguntas como "municípios do
perfil X têm mais DCNT que municípios do perfil Y?".

Pré-requisito:
    python src/juntar_variaveis_socioeconomicas.py

Uso:
    python src/pca_e_cluster.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

sns.set_style("whitegrid")

# Ajuste conforme as variáveis que você efetivamente reuniu na base consolidada
VARIAVEIS_CANDIDATAS = [
    "pib_per_capita", "renda_per_capita", "gini", "taxa_pobreza",
    "taxa_analfabetismo", "taxa_urbanizacao_pct", "idhm",
    "salario_medio_rais", "horas_contratadas_media", "pct_vinculos_ensino_superior",
    "saldo_empregos", "admissoes", "desligamentos",
]


def carregar_base() -> pd.DataFrame:
    caminho = RAW_DIR / "indicadores_socioeconomicos_completos.csv"
    if not caminho.exists():
        raise FileNotFoundError("Rode python src/juntar_variaveis_socioeconomicas.py primeiro.")
    return pd.read_csv(caminho)


def preparar_dados(base: pd.DataFrame):
    variaveis = [v for v in VARIAVEIS_CANDIDATAS if v in base.columns]
    faltando = [v for v in VARIAVEIS_CANDIDATAS if v not in base.columns]
    if faltando:
        print(f"[AVISO] Variáveis não encontradas (ignoradas): {faltando}")

    dados = base.dropna(subset=variaveis).copy()
    if len(dados) < 10:
        raise ValueError(
            f"Apenas {len(dados)} municípios com dados completos para as variáveis "
            f"disponíveis — poucos para PCA/cluster serem confiáveis. Considere reunir mais "
            f"variáveis ou tratar valores faltantes antes de continuar."
        )

    X = StandardScaler().fit_transform(dados[variaveis])
    return dados, X, variaveis


def rodar_pca(dados: pd.DataFrame, X: np.ndarray, variaveis: list[str]) -> pd.DataFrame:
    pca = PCA()
    componentes = pca.fit_transform(X)

    variancia_explicada = pca.explained_variance_ratio_
    variancia_acumulada = np.cumsum(variancia_explicada)

    # Quantos componentes bastam para explicar 80% da variância? (regra prática comum)
    n_componentes_80pct = int(np.argmax(variancia_acumulada >= 0.80) + 1)
    print(f"[OK] {n_componentes_80pct} componentes explicam {variancia_acumulada[n_componentes_80pct-1]*100:.1f}% "
          f"da variação total entre municípios.")

    # Gráfico de variância explicada (scree plot)
    plt.figure(figsize=(8, 5))
    plt.plot(range(1, len(variancia_explicada) + 1), variancia_acumulada, marker="o")
    plt.axhline(0.80, color="red", linestyle="--", label="80% da variância")
    plt.xlabel("Número de componentes")
    plt.ylabel("Variância acumulada explicada")
    plt.title("PCA — variância explicada por componente")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "pca_variancia_explicada.png", dpi=150)
    plt.close()
    print(f"[OK] Gráfico salvo: {OUTPUTS_DIR / 'pca_variancia_explicada.png'}")

    # Cargas (loadings): quanto cada variável original contribui para cada componente —
    # é isso que permite "nomear" os componentes (ex.: "eixo econômico", "eixo educacional")
    cargas = pd.DataFrame(
        pca.components_[:n_componentes_80pct].T,
        index=variaveis,
        columns=[f"PC{i+1}" for i in range(n_componentes_80pct)],
    )
    cargas.to_csv(OUTPUTS_DIR / "pca_cargas_variaveis.csv", encoding="utf-8-sig")
    print(f"\n[OK] Cargas das variáveis em cada componente salvas em: "
          f"{OUTPUTS_DIR / 'pca_cargas_variaveis.csv'}")
    print(cargas.round(2).to_string())
    print(
        "\nComo interpretar: dentro de cada coluna (PC1, PC2...), as variáveis com maior valor "
        "absoluto são as que mais 'definem' aquele componente. Ex.: se PIB, renda e salário "
        "têm carga alta em PC1, esse componente representa um eixo geral de 'desenvolvimento "
        "econômico'."
    )

    # Adiciona os componentes principais de volta à base, para uso posterior (regressão, cluster)
    for i in range(n_componentes_80pct):
        dados[f"pca_{i+1}"] = componentes[:, i]

    return dados


def rodar_cluster(dados: pd.DataFrame, X: np.ndarray, k_min: int = 2, k_max: int = 6) -> pd.DataFrame:
    """Testa diferentes números de clusters (k) e escolhe o melhor via coeficiente de silhueta
    (mede o quão bem separados e coesos os grupos ficam — quanto mais perto de 1, melhor)."""
    melhores_scores = {}
    for k in range(k_min, k_max + 1):
        modelo = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = modelo.fit_predict(X)
        score = silhouette_score(X, labels)
        melhores_scores[k] = score

    melhor_k = max(melhores_scores, key=melhores_scores.get)
    print(f"\n[OK] Melhor número de clusters: k={melhor_k} (silhueta={melhores_scores[melhor_k]:.3f})")
    for k, score in melhores_scores.items():
        marcador = " <-- escolhido" if k == melhor_k else ""
        print(f"    k={k}: silhueta={score:.3f}{marcador}")

    modelo_final = KMeans(n_clusters=melhor_k, random_state=42, n_init=10)
    dados["cluster"] = modelo_final.fit_predict(X)

    # Perfil médio de cada cluster nas variáveis originais — ajuda a "batizar" cada grupo
    variaveis = [c for c in dados.columns if c in VARIAVEIS_CANDIDATAS]
    perfil = dados.groupby("cluster")[variaveis].mean().round(1)
    perfil.to_csv(OUTPUTS_DIR / "perfil_clusters.csv", encoding="utf-8-sig")
    print(f"\n[OK] Perfil médio de cada cluster salvo em: {OUTPUTS_DIR / 'perfil_clusters.csv'}")
    print(perfil.to_string())

    return dados


def main():
    base = carregar_base()
    dados, X, variaveis = preparar_dados(base)

    dados = rodar_pca(dados, X, variaveis)
    dados = rodar_cluster(dados, X)

    saida = PROCESSED_DIR / "municipios_com_pca_e_cluster.csv"
    dados.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Base com componentes principais e cluster salva em: {saida}")
    print("Essa base pode ser cruzada com os indicadores de DCNT para comparar clusters, "
          "ou usada em modelagem_regressao.py no lugar das variáveis originais quando o VIF "
          "estiver alto (troque VARIAVEIS_CANDIDATAS por ['pca_1', 'pca_2', ...] nesse script).")


if __name__ == "__main__":
    main()
