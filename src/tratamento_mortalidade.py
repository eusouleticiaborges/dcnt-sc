"""
Tratamento dos arquivos de mortalidade (SIM) por grupo de DCNT, baixados manualmente do TabNet.

Pré-requisito: seguir data/raw/COMO_BAIXAR_DADOS.md e salvar os 4 arquivos em data/raw/sim/

Uso:
    python src/tratamento_mortalidade.py
"""

import pandas as pd
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "sim"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Mapeia nome do arquivo -> rótulo do grupo de DCNT
ARQUIVOS_POR_GRUPO = {
    "cardiovascular_obitos.csv": "Cardiovascular",
    "neoplasias_obitos.csv": "Câncer",
    "diabetes_obitos.csv": "Diabetes",
    "respiratorias_obitos.csv": "Respiratória crônica",
}


def converter_para_codigo7(codigo6: str) -> int:
    """
    O TabNet exporta o código do município com 6 dígitos (sem o dígito verificador),
    mas o IBGE (e por consequência, a tabela dim_municipios) usa o código completo de
    7 dígitos. Sem essa conversão, o cruzamento entre as duas fontes falha silenciosamente
    (zero correspondências, sem erro nenhum) — por isso essa conversão é essencial.
    """
    pesos = [1, 2, 1, 2, 1, 2]
    soma = 0
    for digito, peso in zip(codigo6, pesos):
        produto = int(digito) * peso
        soma += produto if produto < 10 else (produto // 10 + produto % 10)
    digito_verificador = (10 - (soma % 10)) % 10
    return int(codigo6 + str(digito_verificador))


def extrair_codigo_ibge(texto_municipio: str) -> int | None:
    match = re.match(r"^\s*(\d{6})", str(texto_municipio))
    return converter_para_codigo7(match.group(1)) if match else None


def encontrar_linha_cabecalho(caminho: Path) -> int:
    """Procura a linha real do cabeçalho (a que começa com "Município"), em vez de assumir
    um número fixo de linhas de metadado — o número varia conforme o que foi selecionado no
    TabNet (ex.: usar só "Categoria CID-10" ou também "Capítulo CID-10")."""
    with open(caminho, "r", encoding="latin1") as f:
        for i, linha in enumerate(f):
            if linha.strip().startswith('"Município"'):
                return i
    raise ValueError(f"Não encontrei a linha de cabeçalho em {caminho.name}")


def tratar_arquivo(caminho: Path, grupo: str) -> pd.DataFrame:
    linhas_para_pular = encontrar_linha_cabecalho(caminho)
    df = pd.read_csv(caminho, sep=";", encoding="latin1", skiprows=linhas_para_pular, quotechar='"')
    col_municipio = df.columns[0]

    # A coluna "Total" é um agregado dos anos, não um ano em si — remove antes de "derreter"
    if "Total" in df.columns:
        df = df.drop(columns=["Total"])

    # Remove a linha de rodapé "Total" (soma de todos os municípios) e linhas de nota/fonte
    df = df[df[col_municipio] != "Total"]

    df_longo = df.melt(id_vars=[col_municipio], var_name="ano", value_name="obitos")
    df_longo["codigo_ibge"] = df_longo[col_municipio].apply(extrair_codigo_ibge)
    df_longo = df_longo.dropna(subset=["codigo_ibge"])
    df_longo["codigo_ibge"] = df_longo["codigo_ibge"].astype(int)
    df_longo["obitos"] = pd.to_numeric(df_longo["obitos"], errors="coerce").fillna(0)
    df_longo["grupo_dcnt"] = grupo

    return df_longo[["codigo_ibge", "ano", "grupo_dcnt", "obitos"]]


def main():
    partes = []
    faltando = []

    for nome_arquivo, grupo in ARQUIVOS_POR_GRUPO.items():
        caminho = RAW_DIR / nome_arquivo
        if not caminho.exists():
            faltando.append(nome_arquivo)
            continue
        partes.append(tratar_arquivo(caminho, grupo))
        print(f"[OK] Processado: {nome_arquivo} ({grupo})")

    if faltando:
        print(f"\n[AVISO] Arquivos não encontrados (pulados): {faltando}")
        print("Veja data/raw/COMO_BAIXAR_DADOS.md para instruções de download.")

    if not partes:
        raise FileNotFoundError("Nenhum arquivo de mortalidade encontrado em data/raw/sim/")

    completo = pd.concat(partes, ignore_index=True)
    saida = PROCESSED_DIR / "mortalidade_dcnt_sc_tratado.csv"
    completo.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Dados de mortalidade tratados salvos em: {saida}")
    print(completo.groupby("grupo_dcnt")["obitos"].sum())


if __name__ == "__main__":
    main()
