"""
Consolida todas as fontes de dados socioeconômicos em uma única base:
- IBGE via API (coleta_ibge.py): população, PIB per capita, taxa de urbanização
- Atlas Brasil (manual): IDHM, Gini, renda per capita, pobreza, analfabetismo etc.
- CAGED (manual, via tratamento_mercado_trabalho.py): saldo de empregos, salário médio

O cruzamento entre IBGE (que já vem com código IBGE de 6 dígitos) e Atlas Brasil (que vem só
com nome do município) é feito por nome normalizado — mais sujeito a erro do que por código,
então o script avisa quantos municípios ficaram sem correspondência, para você conferir.

Pré-requisitos (rode o quanto tiver disponível — o script usa o que encontrar):
    python src/coleta_ibge.py
    (baixar manualmente data/raw/atlas_brasil_sc.csv — ver COMO_ADICIONAR_ATLAS_BRASIL.md)
    python src/tratamento_mercado_trabalho.py

Uso:
    python src/juntar_variaveis_socioeconomicas.py
"""

import pandas as pd
import unicodedata
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Ajuste se as colunas exportadas do Atlas Brasil vierem com nomes diferentes
MAPEAMENTO_ATLAS = {
    "Município": "municipio_bruto",
    "IDHM": "idhm",
    "IDHM Renda": "idhm_renda",
    "IDHM Longevidade": "idhm_longevidade",
    "IDHM Educação": "idhm_educacao",
    "Índice de Gini": "gini",
    "Renda per capita": "renda_per_capita",
    "% de pobres": "taxa_pobreza",
    "Taxa de analfabetismo": "taxa_analfabetismo",
    "Esperança de vida ao nascer": "esperanca_vida",
}


def normalizar_nome(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", str(nome)).encode("ASCII", "ignore").decode()
    return nome.strip().lower()


def carregar_ibge() -> pd.DataFrame:
    caminho = RAW_DIR / "indicadores_socioeconomicos_sc.csv"
    if not caminho.exists():
        raise FileNotFoundError("Rode python src/coleta_ibge.py primeiro.")
    df = pd.read_csv(caminho)
    df["municipio_normalizado"] = df["municipio"].apply(normalizar_nome)
    return df


def carregar_atlas_brasil() -> pd.DataFrame | None:
    caminho = RAW_DIR / "atlas_brasil_sc.csv"
    if not caminho.exists():
        print("[AVISO] atlas_brasil_sc.csv não encontrado — pulando essas variáveis. "
              "Veja COMO_ADICIONAR_ATLAS_BRASIL.md se quiser incluí-las.")
        return None

    df = pd.read_csv(caminho, sep=None, engine="python", encoding="latin1")
    colunas_presentes = {k: v for k, v in MAPEAMENTO_ATLAS.items() if k in df.columns}
    df = df.rename(columns=colunas_presentes)

    if "municipio_bruto" not in df.columns:
        print("[AVISO] Coluna de município não reconhecida no arquivo do Atlas Brasil. "
              "Ajuste MAPEAMENTO_ATLAS no topo deste script.")
        return None

    df["municipio_normalizado"] = df["municipio_bruto"].apply(normalizar_nome)

    colunas_indicadores = [v for v in MAPEAMENTO_ATLAS.values() if v in df.columns and v != "municipio_bruto"]
    return df[["municipio_normalizado"] + colunas_indicadores]


def carregar_rais_caged() -> pd.DataFrame | None:
    caminho = RAW_DIR / "rais_caged_sc.csv"
    if not caminho.exists():
        print("[AVISO] rais_caged_sc.csv não encontrado — pulando essas variáveis. "
              "Rode coleta_rais_caged.py se quiser incluí-las.")
        return None
    return pd.read_csv(caminho)


def main():
    ibge = carregar_ibge()
    atlas = carregar_atlas_brasil()
    rais_caged = carregar_rais_caged()

    base = ibge.copy()

    if atlas is not None:
        antes = len(base)
        base = base.merge(atlas, on="municipio_normalizado", how="left")
        sem_correspondencia = base[atlas.columns[1]].isna().sum() if len(atlas.columns) > 1 else 0
        print(f"[OK] Atlas Brasil cruzado. {sem_correspondencia} de {antes} municípios "
              f"sem correspondência por nome (confira grafia se for um número alto).")

    if rais_caged is not None:
        base = base.merge(rais_caged, on="codigo_ibge", how="left")
        print(f"[OK] Dados de RAIS + CAGED (via Base dos Dados) cruzados por código IBGE.")

    base = base.drop(columns=["municipio_normalizado"], errors="ignore")

    saida = RAW_DIR / "indicadores_socioeconomicos_completos.csv"
    base.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Base socioeconômica consolidada salva em: {saida}")
    print(f"Colunas disponíveis: {list(base.columns)}")


if __name__ == "__main__":
    main()
