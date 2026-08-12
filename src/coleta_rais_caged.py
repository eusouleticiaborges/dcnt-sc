"""
Coleta dados de mercado de trabalho (RAIS e CAGED) para os municípios de Santa Catarina,
via Base dos Dados (BigQuery) — https://basedosdados.org

Pré-requisito: seguir data/raw/COMO_CONFIGURAR_BASEDOSDADOS.md antes de rodar este script.

IMPORTANTE — leia antes de rodar:
Os nomes de coluna abaixo (ex.: valor_remuneracao_media, quantidade_horas_contratadas,
grau_instrucao_apos_2005, cnae_2_subclasse) são os nomes documentados publicamente pela Base
dos Dados para a tabela br_me_rais.microdados_vinculos, mas esquemas de dados públicos mudam
com o tempo. Rode primeiro a função `listar_colunas_disponiveis()` deste script — ela consulta
o esquema real da tabela e imprime as colunas existentes, para você confirmar (ou ajustar) os
nomes usados nas consultas abaixo antes de rodar a coleta completa.

Uso:
    python src/coleta_rais_caged.py
"""

import basedosdados as bd
import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Troque pelo seu Project ID do Google Cloud (ver COMO_CONFIGURAR_BASEDOSDADOS.md)
BILLING_PROJECT_ID = "SEU_PROJECT_ID_AQUI"

ANO_REFERENCIA = 2023  # ajuste para o ano mais recente disponível na base


def listar_colunas_disponiveis(dataset_id: str, table_id: str):
    """Consulta o esquema real da tabela no BigQuery, para conferir nomes de coluna antes de
    montar a query principal — rode isso primeiro se o script der erro de coluna não encontrada."""
    query = f"""
        SELECT column_name, data_type
        FROM `basedosdados.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{table_id}'
        ORDER BY ordinal_position
    """
    colunas = bd.read_sql(query, billing_project_id=BILLING_PROJECT_ID)
    print(f"\nColunas disponíveis em {dataset_id}.{table_id}:")
    print(colunas.to_string(index=False))
    return colunas


def coletar_rais(ano: int = ANO_REFERENCIA) -> pd.DataFrame:
    """
    Agrega, por município de SC, indicadores derivados da RAIS (microdado de vínculos formais):
    - salário médio (nominal)
    - horas contratadas médias
    - % de vínculos com ensino superior completo (proxy de escolaridade da força de trabalho)
    - número total de vínculos ativos (proxy de tamanho do mercado formal)
    """
    query = f"""
        SELECT
            id_municipio AS codigo_ibge,
            AVG(valor_remuneracao_media) AS salario_medio_rais,
            AVG(quantidade_horas_contratadas) AS horas_contratadas_media,
            AVG(CASE WHEN grau_instrucao_apos_2005 IN ('9', '10', '11')
                     THEN 1.0 ELSE 0.0 END) * 100 AS pct_vinculos_ensino_superior,
            COUNT(*) AS total_vinculos_ativos
        FROM `basedosdados.br_me_rais.microdados_vinculos`
        WHERE sigla_uf = 'SC'
          AND ano = {ano}
          AND vinculo_ativo_3112 = '1'
        GROUP BY id_municipio
    """
    print(f"[INFO] Consultando RAIS para SC, ano {ano}... (pode levar alguns minutos)")
    df = bd.read_sql(query, billing_project_id=BILLING_PROJECT_ID)
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)
    print(f"[OK] RAIS: {len(df)} municípios retornados.")
    return df


def coletar_caged(ano: int = ANO_REFERENCIA) -> pd.DataFrame:
    """
    Agrega, por município de SC, indicadores derivados do CAGED (movimentação mensal):
    - saldo de empregos no ano (admissões - desligamentos)
    - total de admissões e desligamentos
    - salário médio de admissão
    """
    query = f"""
        SELECT
            id_municipio AS codigo_ibge,
            SUM(CASE WHEN saldo_movimentacao = 1 THEN 1 ELSE 0 END) AS admissoes,
            SUM(CASE WHEN saldo_movimentacao = -1 THEN 1 ELSE 0 END) AS desligamentos,
            SUM(saldo_movimentacao) AS saldo_empregos,
            AVG(CASE WHEN saldo_movimentacao = 1 THEN salario END) AS salario_medio_admissao
        FROM `basedosdados.br_me_caged.microdados_movimentacao`
        WHERE sigla_uf = 'SC'
          AND ano = {ano}
        GROUP BY id_municipio
    """
    print(f"[INFO] Consultando CAGED para SC, ano {ano}... (pode levar alguns minutos)")
    df = bd.read_sql(query, billing_project_id=BILLING_PROJECT_ID)
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)
    print(f"[OK] CAGED: {len(df)} municípios retornados.")
    return df


def main():
    print("Se esta é a primeira vez rodando, considere chamar antes:")
    print("  listar_colunas_disponiveis('br_me_rais', 'microdados_vinculos')")
    print("  listar_colunas_disponiveis('br_me_caged', 'microdados_movimentacao')")
    print("para confirmar os nomes de coluna reais.\n")

    rais = coletar_rais()
    caged = coletar_caged()

    base = rais.merge(caged, on="codigo_ibge", how="outer")

    saida = RAW_DIR / "rais_caged_sc.csv"
    base.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Dados de RAIS + CAGED salvos em: {saida}")
    print(base.head())


if __name__ == "__main__":
    main()
