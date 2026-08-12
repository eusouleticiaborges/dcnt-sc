"""
Cria/atualiza o banco de dados SQLite central do projeto, carregando os dados disponíveis
em data/raw/ e data/processed/ para dentro de tabelas organizadas.

Por que SQLite: é um banco de dados real (não são "CSVs soltos"), mas vive num único arquivo,
sem precisar instalar nem configurar nenhum servidor. O Python já sabe conversar com ele nativamente.

Este script é seguro de rodar várias vezes — ele recria as tabelas do zero a cada execução,
usando os CSVs mais recentes disponíveis. Ele não falha se algum dado ainda não tiver sido
coletado (por exemplo, antes de você baixar os dados de saúde do TabNet) — nesse caso, a
tabela correspondente simplesmente não é criada ainda, e o script avisa.

Uso:
    python src/criar_banco_sqlite.py
"""

import sqlite3
import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "dcnt_sc.db"


def carregar_tabela(conexao, caminho_csv: Path, nome_tabela: str, descricao: str):
    if not caminho_csv.exists():
        print(f"[PULADO] {nome_tabela}: arquivo {caminho_csv.name} ainda não existe "
              f"({descricao})")
        return False

    df = pd.read_csv(caminho_csv)
    df.to_sql(nome_tabela, conexao, if_exists="replace", index=False)
    print(f"[OK] Tabela '{nome_tabela}' criada com {len(df)} linhas ({descricao})")
    return True


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(DB_PATH)

    print(f"Banco de dados: {DB_PATH}\n")

    carregar_tabela(
        conexao,
        RAW_DIR / "indicadores_socioeconomicos_sc.csv",
        "dim_municipios",
        "população, urbanização, PIB per capita — um registro por município",
    )

    carregar_tabela(
        conexao,
        PROCESSED_DIR / "mortalidade_dcnt_sc_tratado.csv",
        "fato_mortalidade",
        "óbitos por grupo de DCNT e ano — dados do SIM/TabNet",
    )

    carregar_tabela(
        conexao,
        PROCESSED_DIR / "internacoes_dcnt_sc_tratado.csv",
        "fato_internacoes",
        "internações e óbitos hospitalares — dados do SIH/TabNet",
    )

    carregar_tabela(
        conexao,
        RAW_DIR / "rais_caged_sc.csv",
        "fato_mercado_trabalho",
        "salário médio, saldo de empregos — RAIS/CAGED via Base dos Dados",
    )

    # Lista as tabelas que efetivamente existem no banco, para conferência
    tabelas = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table'", conexao
    )
    print(f"\n[OK] Tabelas atualmente no banco: {list(tabelas['name'])}")

    conexao.close()


if __name__ == "__main__":
    main()
