"""
Tratamento dos arquivos de internação/óbito hospitalar (SIH) por grupo de DCNT.

Formato real do TabNet (confirmado com arquivo baixado): quando se marca "Internações" e
"Óbitos" juntos no Conteúdo, o TabNet exige Coluna = "Não ativa" — ou seja, o resultado já
vem agregado para o período inteiro selecionado (não quebrado por ano). Por isso este script
não faz "melt" por ano, diferente do tratamento_mortalidade.py.

Nota metodológica: os dados são "por local de internação" (município onde fica o hospital),
não "por local de residência" (município onde a pessoa mora) — o DATASUS não disponibiliza a
versão por residência com detalhamento de diagnóstico (CID-10) de forma acessível. Isso é uma
limitação conhecida: municípios-polo (com hospital) tendem a concentrar números mais altos.
Documentado também no README do projeto.

Pré-requisito: seguir data/raw/COMO_BAIXAR_DADOS.md e salvar os 4 arquivos em data/raw/sih/

Uso:
    python src/tratamento_internacoes.py
"""

import pandas as pd
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "sih"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

ARQUIVOS_POR_GRUPO = {
    "cardiovascular_internacoes.csv": "Cardiovascular",
    "neoplasias_internacoes.csv": "Câncer",
    "diabetes_internacoes.csv": "Diabetes",
    "respiratorias_internacoes.csv": "Respiratória crônica",
}


def converter_para_codigo7(codigo6: str) -> int:
    """Ver explicação detalhada em tratamento_mortalidade.py — mesma lógica, aplicada aqui
    para o código de município extraído dos arquivos do SIH."""
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
    """
    Em vez de assumir um número fixo de linhas de metadado (que varia conforme o que foi
    selecionado no TabNet — às vezes tem 'Capítulo CID-10', às vezes não), procura a linha
    real do cabeçalho (a que começa com "Município") e retorna quantas linhas pular até ela.
    """
    with open(caminho, "r", encoding="latin1") as f:
        for i, linha in enumerate(f):
            if linha.strip().startswith('"Município"'):
                return i
    raise ValueError(f"Não encontrei a linha de cabeçalho em {caminho.name}")


def tratar_arquivo(caminho: Path, grupo: str) -> pd.DataFrame:
    linhas_para_pular = encontrar_linha_cabecalho(caminho)
    df = pd.read_csv(
        caminho, sep=";", encoding="latin1", skiprows=linhas_para_pular, quotechar='"'
    )
    col_municipio = df.columns[0]

    # Remove a linha de rodapé "Total" (soma de todos os municípios)
    df = df[df[col_municipio] != "Total"]

    df = df.rename(columns={
        col_municipio: "municipio_bruto",
        "Internações": "internacoes",
        "Óbitos": "obitos_hospitalares",
    })

    df["codigo_ibge"] = df["municipio_bruto"].apply(extrair_codigo_ibge)
    df = df.dropna(subset=["codigo_ibge"])
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)

    df["internacoes"] = pd.to_numeric(df["internacoes"], errors="coerce").fillna(0)
    df["obitos_hospitalares"] = pd.to_numeric(df["obitos_hospitalares"], errors="coerce").fillna(0)
    df["grupo_dcnt"] = grupo

    return df[["codigo_ibge", "grupo_dcnt", "internacoes", "obitos_hospitalares"]]


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
        raise FileNotFoundError("Nenhum arquivo de internação encontrado em data/raw/sih/")

    completo = pd.concat(partes, ignore_index=True)
    saida = PROCESSED_DIR / "internacoes_dcnt_sc_tratado.csv"
    completo.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Dados de internação tratados salvos em: {saida}")
    print(completo.groupby("grupo_dcnt")[["internacoes", "obitos_hospitalares"]].sum())


if __name__ == "__main__":
    main()
