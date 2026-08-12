"""
Coleta de dados socioeconômicos dos municípios de Santa Catarina via API do IBGE.

⚠️ AVISO: este script foi a primeira tentativa do projeto (via API automática), mas parte
dela (PIB, taxa de urbanização) se mostrou pouco confiável durante o desenvolvimento — os
dados realmente usados no projeto vêm de `consolidar_ibge_manual.py`, que lê arquivos
baixados manualmente do site do SIDRA. Este arquivo permanece como referência/rota
alternativa, não como parte do fluxo principal. A função `obter_municipios_sc()` (lista de
municípios com código IBGE) continua funcionando bem e é reaproveitável.

Fontes:
- API de Localidades: lista de municípios de SC com código IBGE
- API SIDRA (agregados): população estimada e PIB per capita por município

Uso:
    python src/coleta_ibge.py
"""

import requests
import pandas as pd
import time
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

UF_SIGLA = "SC"


def obter_municipios_sc() -> pd.DataFrame:
    """Retorna a lista de municípios de SC com seus códigos IBGE."""
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF_SIGLA}/municipios"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dados = resp.json()

    municipios = [
        {"codigo_ibge": m["id"], "municipio": m["nome"]}
        for m in dados
    ]
    df = pd.DataFrame(municipios)
    print(f"[OK] {len(df)} municípios de SC encontrados.")
    return df


def obter_populacao_censo2022(ano: int = 2023) -> pd.DataFrame:
    """
    Retorna a população por município de SC, via API do IBGE.

    ATENÇÃO — rota alternativa não utilizada no projeto atual: esta função tenta buscar o
    dado via API automática (tabela SIDRA 6579), mas isso se mostrou pouco confiável durante
    o desenvolvimento (a tabela de "estimativas" não cobre anos de Censo, entre outros
    problemas). Por isso os dados de população realmente usados no projeto vêm de
    `consolidar_ibge_manual.py`, que lê arquivos baixados manualmente do SIDRA (Censo 2022).
    Esta função permanece aqui como referência, caso queira automatizar no futuro.
    """
    url = (
        f"https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/{ano}"
        f"/c1/all"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dados = resp.json()

    df = pd.DataFrame(dados[1:])  # primeira linha é o cabeçalho descritivo
    df = df.rename(columns={"D1C": "codigo_ibge", "V": "populacao_censo2022"})
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)
    df["populacao_censo2022"] = pd.to_numeric(df["populacao_censo2022"], errors="coerce")

    # Filtrar apenas municípios de SC (códigos IBGE de SC começam com 42)
    df = df[df["codigo_ibge"].astype(str).str.startswith("42")]
    df = df[["codigo_ibge", "populacao_censo2022"]]
    print(f"[OK] População obtida via API para {len(df)} municípios (ano {ano}) — "
          f"rota alternativa, não é a fonte usada no projeto atual.")
    return df


def obter_pib_per_capita(ano: int = 2021) -> pd.DataFrame:
    """
    Retorna o PIB per capita por município de SC.
    Tabela SIDRA 5938 = PIB dos Municípios.
    Variável 593 = PIB per capita.
    """
    url = (
        f"https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/593/p/{ano}"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dados = resp.json()

    df = pd.DataFrame(dados[1:])
    df = df.rename(columns={"D1C": "codigo_ibge", "V": "pib_per_capita"})
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)
    df["pib_per_capita"] = pd.to_numeric(df["pib_per_capita"], errors="coerce")

    df = df[df["codigo_ibge"].astype(str).str.startswith("42")]
    df = df[["codigo_ibge", "pib_per_capita"]]
    print(f"[OK] PIB per capita obtido para {len(df)} municípios (ano {ano}).")
    return df


def obter_taxa_urbanizacao(ano_censo: int = 2022) -> pd.DataFrame:
    """
    Retorna a taxa de urbanização (% da população em área urbana) por município de SC.
    Tabela SIDRA 9514 = População residente, por situação do domicílio (Censo 2022).
    Variável 93 = % população urbana (ajustar código se a tabela mudar).

    ATENÇÃO: código de tabela/variável não testado em ambiente com acesso à internet —
    confira em https://sidra.ibge.gov.br se der erro, e ajuste aqui.
    """
    url = f"https://apisidra.ibge.gov.br/values/t/9514/n6/all/v/93/p/{ano_censo}/c1/all"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dados = resp.json()

    df = pd.DataFrame(dados[1:])
    df = df.rename(columns={"D1C": "codigo_ibge", "V": "taxa_urbanizacao_pct"})
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)
    df["taxa_urbanizacao_pct"] = pd.to_numeric(df["taxa_urbanizacao_pct"], errors="coerce")

    df = df[df["codigo_ibge"].astype(str).str.startswith("42")]
    df = df[["codigo_ibge", "taxa_urbanizacao_pct"]]
    print(f"[OK] Taxa de urbanização obtida para {len(df)} municípios.")
    return df


def main():
    municipios = obter_municipios_sc()
    time.sleep(1)  # gentileza com a API pública

    populacao = obter_populacao_censo2022()
    time.sleep(1)

    pib = obter_pib_per_capita()
    time.sleep(1)

    try:
        urbanizacao = obter_taxa_urbanizacao()
    except Exception as e:
        print(f"[AVISO] Não foi possível obter taxa de urbanização automaticamente: {e}")
        print("Você pode preencher essa coluna manualmente depois, ou ajustar o código da tabela SIDRA.")
        urbanizacao = pd.DataFrame(columns=["codigo_ibge", "taxa_urbanizacao_pct"])

    # Junta tudo em uma única base
    base = municipios.merge(populacao, on="codigo_ibge", how="left")
    base = base.merge(pib, on="codigo_ibge", how="left")
    base = base.merge(urbanizacao, on="codigo_ibge", how="left")

    saida = RAW_DIR / "indicadores_socioeconomicos_sc.csv"
    base.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Base salva em: {saida}")
    print(base.head())
    print(
        "\n[LEMBRETE] O IDHM (Índice de Desenvolvimento Humano Municipal) não tem API pública — "
        "veja data/raw/COMO_ADICIONAR_IDHM.md para baixá-lo manualmente e enriquecer esta base."
    )


if __name__ == "__main__":
    main()
