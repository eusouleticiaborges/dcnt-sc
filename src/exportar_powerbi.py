"""
Exporta um arquivo Excel (.xlsx) com múltiplas abas, organizado para importação direta no
Power BI. A fonte dos dados é o banco de dados SQLite central do projeto (data/dcnt_sc.db) —
não os CSVs soltos diretamente, já que o banco é agora a fonte única de verdade do projeto.

Por que ainda gerar um Excel, se os dados já estão num banco? Porque conectar o Power BI
diretamente a um arquivo SQLite exige instalar um driver ODBC separado — uma complicação a
mais que não vale a pena neste estágio. O Excel funciona como uma "ponte" simples: script lê
do banco, gera a planilha, Power BI importa a planilha normalmente.

Pré-requisitos: rodar antes, nesta ordem:
    python src/criar_banco_sqlite.py
    python src/modelagem_regressao.py   (opcional, se quiser a aba de resultado da regressão)

Uso:
    python src/exportar_powerbi.py
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "dcnt_sc.db"
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Banco de dados não encontrado. Rode primeiro: python src/criar_banco_sqlite.py"
        )

    conexao = sqlite3.connect(DB_PATH)

    dim_municipios = pd.read_sql("SELECT * FROM dim_municipios", conexao)

    tabelas_existentes = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table'", conexao
    )["name"].tolist()

    saida = OUTPUTS_DIR / "dataset_powerbi.xlsx"
    with pd.ExcelWriter(saida, engine="openpyxl") as writer:
        dim_municipios.to_excel(writer, sheet_name="dim_municipios", index=False)
        print(f"[OK] Aba 'dim_municipios': {len(dim_municipios)} linhas")

        if "fato_mortalidade" in tabelas_existentes and "fato_internacoes" in tabelas_existentes:
            mortalidade = pd.read_sql("SELECT * FROM fato_mortalidade", conexao)
            internacoes = pd.read_sql("SELECT * FROM fato_internacoes", conexao)

            # Mortalidade tem detalhamento por ano; internação já vem agregada no período
            # inteiro (limitação do TabNet ao combinar Internações+Óbitos no mesmo conteúdo).
            # Para juntar as duas, soma a mortalidade também pelo período inteiro.
            mortalidade_periodo = (
                mortalidade.groupby(["codigo_ibge", "grupo_dcnt"])["obitos"]
                .sum()
                .reset_index()
            )

            fato = mortalidade_periodo.merge(
                internacoes, on=["codigo_ibge", "grupo_dcnt"], how="outer"
            )
            fato = fato.merge(
                dim_municipios[["codigo_ibge", "populacao_censo2022"]],
                on="codigo_ibge", how="left"
            )
            fato["taxa_mortalidade_100k"] = fato["obitos"] / fato["populacao_censo2022"] * 100_000
            fato["taxa_internacao_100k"] = fato["internacoes"] / fato["populacao_censo2022"] * 100_000
            fato["taxa_letalidade_pct"] = fato.apply(
                lambda r: (r["obitos_hospitalares"] / r["internacoes"] * 100)
                if r.get("internacoes", 0) and r["internacoes"] > 0 else None,
                axis=1,
            )
            fato.to_excel(writer, sheet_name="fato_indicadores", index=False)
            print(f"[OK] Aba 'fato_indicadores': {len(fato)} linhas")
        else:
            print("[AVISO] Tabelas de saúde ainda não existem no banco — aba 'fato_indicadores' "
                  "não gerada. Rode a coleta do TabNet + criar_banco_sqlite.py primeiro.")

        caminho_regressao = OUTPUTS_DIR / "tabela_regressao_dcnt.csv"
        if caminho_regressao.exists():
            regressao = pd.read_csv(caminho_regressao)
            regressao.to_excel(writer, sheet_name="resultado_regressao", index=False)
            print(f"[OK] Aba 'resultado_regressao': {len(regressao)} linhas")

    conexao.close()
    print(f"\n[OK] Arquivo pronto para o Power BI salvo em: {saida}")


if __name__ == "__main__":
    main()

