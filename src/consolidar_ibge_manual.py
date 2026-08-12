"""
Consolida os 3 arquivos baixados manualmente do SIDRA (população, urbanização, PIB) em uma
única base de indicadores socioeconômicos para Santa Catarina.

Pré-requisito: ter os 3 arquivos baixados do site sidra.ibge.gov.br salvos em data/raw/:
    - populacao_censo2022_brasil.csv  (tabela 9514)
    - urbanizacao_brasil.csv          (tabela 9923, com Total + Urbana + Rural marcados)
    - pib_total_brasil.csv            (tabela 5938, PIB total em Mil Reais, ano 2022)

Uso:
    python src/consolidar_ibge_manual.py
"""

import pandas as pd
import re
import unicodedata
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def normalizar_nome(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", str(nome)).encode("ASCII", "ignore").decode()
    return nome.strip().lower()


def extrair_uf(municipio_com_uf: str):
    """Extrai a sigla do estado a partir de um texto como 'Florianópolis (SC)'."""
    match = re.search(r"\(([A-Z]{2})\)\s*$", str(municipio_com_uf))
    return match.group(1) if match else None


def extrair_nome_sem_uf(municipio_com_uf: str) -> str:
    return re.sub(r"\s*\([A-Z]{2}\)\s*$", "", str(municipio_com_uf)).strip()


def carregar_populacao() -> pd.DataFrame:
    caminho = RAW_DIR / "populacao_censo2022_brasil.csv"
    df = pd.read_csv(
        caminho, sep=";", skiprows=6, header=None, encoding="utf-8-sig",
        names=["codigo_ibge", "municipio_uf", "forma_idade", "populacao_censo2022"],
        quotechar='"', engine="python",
    )
    df["populacao_censo2022"] = pd.to_numeric(df["populacao_censo2022"], errors="coerce")
    df = df.dropna(subset=["populacao_censo2022"])
    df["codigo_ibge"] = pd.to_numeric(df["codigo_ibge"], errors="coerce")
    df = df.dropna(subset=["codigo_ibge"])
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)

    df["uf"] = df["municipio_uf"].apply(extrair_uf)
    df["municipio"] = df["municipio_uf"].apply(extrair_nome_sem_uf)
    df["chave"] = df["municipio"].apply(normalizar_nome) + "_" + df["uf"].fillna("")

    df = df[df["uf"] == "SC"]
    return df[["codigo_ibge", "municipio", "chave", "populacao_censo2022"]]


def carregar_urbanizacao() -> pd.DataFrame:
    caminho = RAW_DIR / "urbanizacao_brasil.csv"
    df = pd.read_csv(
        caminho, sep=";", skiprows=5, header=None, encoding="utf-8-sig",
        names=["municipio_uf", "total", "urbana", "rural"],
        quotechar='"', engine="python",
    )
    for col in ["total", "urbana", "rural"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["total", "urbana"])

    df["uf"] = df["municipio_uf"].apply(extrair_uf)
    df["municipio"] = df["municipio_uf"].apply(extrair_nome_sem_uf)
    df["chave"] = df["municipio"].apply(normalizar_nome) + "_" + df["uf"].fillna("")

    df = df[df["uf"] == "SC"]
    df["taxa_urbanizacao_pct"] = df["urbana"] / df["total"] * 100
    return df[["chave", "taxa_urbanizacao_pct"]]


def carregar_pib(ano_coluna: str = "pib_2022") -> pd.DataFrame:
    caminho = RAW_DIR / "pib_total_brasil.csv"
    df = pd.read_csv(
        caminho, sep=";", skiprows=4, header=None, encoding="utf-8-sig",
        names=["municipio_uf", "pib_2021", "pib_2022", "pib_2023"],
        quotechar='"', engine="python",
    )
    for col in ["pib_2021", "pib_2022", "pib_2023"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[ano_coluna])

    df["uf"] = df["municipio_uf"].apply(extrair_uf)
    df["municipio"] = df["municipio_uf"].apply(extrair_nome_sem_uf)
    df["chave"] = df["municipio"].apply(normalizar_nome) + "_" + df["uf"].fillna("")

    df = df[df["uf"] == "SC"]
    df = df.rename(columns={ano_coluna: "pib_total_mil_reais"})
    return df[["chave", "pib_total_mil_reais"]]


def main():
    populacao = carregar_populacao()
    urbanizacao = carregar_urbanizacao()
    pib = carregar_pib()

    print(f"[OK] População: {len(populacao)} municípios de SC")
    print(f"[OK] Urbanização: {len(urbanizacao)} municípios de SC")
    print(f"[OK] PIB: {len(pib)} municípios de SC")

    base = populacao.merge(urbanizacao, on="chave", how="left")
    base = base.merge(pib, on="chave", how="left")

    # PIB total vem em Mil Reais -> multiplicar por 1000 para virar Reais antes de dividir
    base["pib_per_capita"] = (base["pib_total_mil_reais"] * 1000) / base["populacao_censo2022"]

    base_final = base[[
        "codigo_ibge", "municipio", "populacao_censo2022",
        "taxa_urbanizacao_pct", "pib_per_capita"
    ]]

    saida = RAW_DIR / "indicadores_socioeconomicos_sc.csv"
    base_final.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Base consolidada salva em: {saida}")
    print(f"[OK] Total de municípios na base final: {len(base_final)}")

    sem_urbanizacao = base_final["taxa_urbanizacao_pct"].isna().sum()
    sem_pib = base_final["pib_per_capita"].isna().sum()
    if sem_urbanizacao or sem_pib:
        print(f"[AVISO] {sem_urbanizacao} municípios sem urbanização, {sem_pib} sem PIB "
              f"(provavelmente diferença de grafia no nome — confira manualmente se for muitos)")

    print("\nAmostra da base final:")
    print(base_final.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
