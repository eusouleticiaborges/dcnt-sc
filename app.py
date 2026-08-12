"""
Painel interativo (Streamlit) para explorar a relação entre indicadores socioeconômicos e
DCNT nos municípios de Santa Catarina.

Uso local:
    streamlit run app.py

Publicação gratuita (Streamlit Community Cloud):
    1. Suba este projeto para o GitHub
    2. Acesse share.streamlit.io, conecte sua conta GitHub
    3. Aponte para este repositório e este arquivo (app.py)
"""

import copy
import json
import sqlite3
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

DB_PATH = Path(__file__).parent / "data" / "dcnt_sc.db"
REGRESSAO_PATH = Path(__file__).parent / "outputs" / "tabela_regressao_dcnt.csv"
GEOJSON_PATH = Path(__file__).parent / "data" / "sc_municipios.geojson"

ICONE_GRUPO = {
    "Cardiovascular": "❤️",
    "Câncer": "🎗️",
    "Diabetes": "🩸",
    "Respiratória crônica": "🫁",
}

NOME_VARIAVEL = {
    "pib_per_capita": "PIB per capita",
    "taxa_urbanizacao_pct": "Taxa de urbanização",
    "renda_per_capita": "Renda per capita",
    "gini": "Índice de Gini",
    "taxa_pobreza": "Taxa de pobreza",
    "taxa_analfabetismo": "Taxa de analfabetismo",
    "idhm": "IDHM",
    "saldo_empregos": "Saldo de empregos",
    "salario_medio_admissao": "Salário médio",
    "taxa_rotatividade": "Rotatividade de emprego",
}

st.set_page_config(
    page_title="DCNT em Santa Catarina",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stMetric {
        background-color: #f8f9fb;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 14px 10px;
    }
    .stMetric label {
        color: #6b7280 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
        color: #1f2937;
    }
    h1 {
        color: #1f2937;
    }
    .interpretacao-card {
        background-color: #f8f9fb;
        border-left: 4px solid #d1d5db;
        border-radius: 6px;
        padding: 10px 16px;
        margin-bottom: 8px;
    }
    .interpretacao-card.significativo {
        border-left: 4px solid #dc2626;
        background-color: #fef2f2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def formatar_reais(valor: float) -> str:
    """Formata número no padrão de moeda brasileiro: R$ 42.463,05"""
    if pd.isna(valor):
        return "—"
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_numero(valor: float, decimais: int = 0) -> str:
    """Formata número no padrão brasileiro (ponto como separador de milhar): 2.598"""
    if pd.isna(valor):
        return "—"
    texto = f"{valor:,.{decimais}f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


def carregar_dados():
    if not DB_PATH.exists():
        return None, None, None
    conexao = sqlite3.connect(DB_PATH)
    dim = pd.read_sql("SELECT * FROM dim_municipios", conexao)
    mortalidade = pd.read_sql("SELECT * FROM fato_mortalidade", conexao)
    internacoes = pd.read_sql("SELECT * FROM fato_internacoes", conexao)
    conexao.close()
    return dim, mortalidade, internacoes


@st.cache_data
def carregar_regressao():
    if not REGRESSAO_PATH.exists():
        return None
    return pd.read_csv(REGRESSAO_PATH)


@st.cache_data
def carregar_geojson():
    if not GEOJSON_PATH.exists():
        return None
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def montar_base(dim, mortalidade, internacoes, grupo):
    mort_grupo = (
        mortalidade[mortalidade["grupo_dcnt"] == grupo]
        .groupby("codigo_ibge")["obitos"]
        .sum()
        .reset_index()
    )
    intern_grupo = internacoes[internacoes["grupo_dcnt"] == grupo][
        ["codigo_ibge", "internacoes", "obitos_hospitalares"]
    ]

    base = dim.merge(mort_grupo, on="codigo_ibge", how="left")
    base = base.merge(intern_grupo, on="codigo_ibge", how="left")
    base[["obitos", "internacoes", "obitos_hospitalares"]] = base[
        ["obitos", "internacoes", "obitos_hospitalares"]
    ].fillna(0)

    base["taxa_mortalidade_100k"] = base["obitos"] / base["populacao_censo2022"] * 100_000
    base["taxa_internacao_100k"] = base["internacoes"] / base["populacao_censo2022"] * 100_000
    base["taxa_letalidade_pct"] = base.apply(
        lambda r: (r["obitos_hospitalares"] / r["internacoes"] * 100) if r["internacoes"] > 0 else None,
        axis=1,
    )
    base["codigo_ibge_str"] = base["codigo_ibge"].astype(str)
    return base


def preparar_geojson_com_dados(geojson_sc, base_filtrada):
    """
    Injeta os valores de mortalidade, óbitos e internações direto dentro das propriedades
    de cada município no GeoJSON — necessário para o Folium conseguir mostrar esses valores
    no tooltip (ao contrário do Plotly, o Folium lê o tooltip das próprias propriedades do
    GeoJSON, não separadamente dos dados).
    """
    geo = copy.deepcopy(geojson_sc)
    dados_por_codigo = base_filtrada.set_index("codigo_ibge_str").to_dict("index")

    for feature in geo["features"]:
        codigo = feature["properties"].get("CD_MUN")
        dado = dados_por_codigo.get(codigo)
        if dado:
            feature["properties"]["taxa_fmt"] = f"{dado['taxa_mortalidade_100k']:.1f}"
            feature["properties"]["obitos_fmt"] = f"{int(dado['obitos'])}"
            feature["properties"]["internacoes_fmt"] = f"{int(dado['internacoes'])}"
        else:
            feature["properties"]["taxa_fmt"] = "sem dado"
            feature["properties"]["obitos_fmt"] = "sem dado"
            feature["properties"]["internacoes_fmt"] = "sem dado"

    return geo


def montar_mapa_folium(geojson_com_dados, base_filtrada, grupo_selecionado):
    mapa = folium.Map(
        location=[-27.4, -50.8], zoom_start=7,
        tiles="cartodbpositron", control_scale=False,
    )

    folium.Choropleth(
        geo_data=geojson_com_dados,
        data=base_filtrada,
        columns=["codigo_ibge_str", "taxa_mortalidade_100k"],
        key_on="feature.properties.CD_MUN",
        fill_color="Reds",
        fill_opacity=0.8,
        line_opacity=0.4,
        line_color="white",
        legend_name=f"Taxa de mortalidade (por 100 mil hab.) — {grupo_selecionado}",
        nan_fill_color="white",
        highlight=True,
    ).add_to(mapa)

    folium.GeoJson(
        geojson_com_dados,
        style_function=lambda x: {"fillOpacity": 0, "color": "transparent", "weight": 0},
        tooltip=folium.GeoJsonTooltip(
            fields=["NM_MUN", "taxa_fmt", "obitos_fmt", "internacoes_fmt"],
            aliases=[
                "Município:",
                "Taxa de mortalidade (por 100 mil hab.):",
                f"Óbitos — {grupo_selecionado}:",
                f"Internações — {grupo_selecionado}:",
            ],
            sticky=True,
        ),
    ).add_to(mapa)

    return mapa


def main():
    dim, mortalidade, internacoes = carregar_dados()

    if dim is None:
        st.error(
            "Banco de dados não encontrado. Rode `python src/criar_banco_sqlite.py` "
            "antes de abrir este painel."
        )
        st.stop()

    grupos_disponiveis = sorted(mortalidade["grupo_dcnt"].unique())

    st.sidebar.header("🔎 Filtros")
    opcoes_com_icone = [f"{ICONE_GRUPO.get(g, '•')} {g}" for g in grupos_disponiveis]
    escolha = st.sidebar.selectbox("Grupo de DCNT", opcoes_com_icone)
    grupo_selecionado = grupos_disponiveis[opcoes_com_icone.index(escolha)]

    populacao_minima = st.sidebar.slider(
        "População mínima do município",
        min_value=0, max_value=50_000, value=0, step=1_000,
        help="Municípios pequenos podem ter poucos casos no período, o que faz a taxa por "
             "100 mil habitantes variar muito só por acaso (1 óbito numa cidade de 2 mil "
             "habitantes já parece uma taxa alta). Aumente esse filtro para deixar a "
             "comparação entre municípios mais confiável.",
    )
    st.sidebar.caption(
        "💡 Cidades pequenas têm poucos casos no período, o que deixa a taxa por 100 mil "
        "habitantes instável. Suba o filtro acima para comparar só municípios maiores, "
        "com números mais confiáveis."
    )

    base = montar_base(dim, mortalidade, internacoes, grupo_selecionado)
    base_filtrada = base[base["populacao_censo2022"] >= populacao_minima]

    municipios_disponiveis = sorted(base_filtrada["municipio"].unique())
    municipios_selecionados = st.sidebar.multiselect(
        "Destacar município(s) específico(s)",
        municipios_disponiveis,
        help="Os municípios escolhidos aparecem destacados nos gráficos de dispersão e na tabela.",
    )

    icone = ICONE_GRUPO.get(grupo_selecionado, "🏥")
    st.title(f"{icone} DCNT em Santa Catarina — {grupo_selecionado}")
    st.caption(
        "Relação entre indicadores socioeconômicos e mortalidade/internação por Doenças "
        "Crônicas Não Transmissíveis nos municípios de SC (2019-2023)."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de óbitos", f"{int(base_filtrada['obitos'].sum()):,}".replace(",", "."))
    col2.metric("Total de internações", f"{int(base_filtrada['internacoes'].sum()):,}".replace(",", "."))
    taxa_geral_ponderada = (
        base_filtrada["obitos"].sum() / base_filtrada["populacao_censo2022"].sum() * 100_000
        if base_filtrada["populacao_censo2022"].sum() > 0 else 0
    )
    col3.metric(
        "Taxa de mortalidade (por 100 mil hab.)", f"{taxa_geral_ponderada:.1f}",
        help="Número de óbitos a cada 100 mil habitantes no período — permite comparar "
             "municípios de tamanhos diferentes de forma justa. Calculada como: "
             "(total de óbitos ÷ população total) × 100.000. Quanto maior, pior.",
    )
    col4.metric("Municípios no filtro", len(base_filtrada))

    st.divider()

    geojson_sc = carregar_geojson()
    col_mapa, col_barras = st.columns([1.3, 1])

    with col_mapa:
        st.subheader(f"{icone} Mortalidade por município")
        if geojson_sc is not None:
            geojson_com_dados = preparar_geojson_com_dados(geojson_sc, base_filtrada)
            mapa = montar_mapa_folium(geojson_com_dados, base_filtrada, grupo_selecionado)
            st_folium(mapa, height=480, use_container_width=True, returned_objects=[])
            st.caption("Passe o mouse sobre um município para ver a taxa de mortalidade, óbitos e internações.")
        else:
            st.info("Arquivo de mapa (GeoJSON) não encontrado em data/sc_municipios.geojson.")

    with col_barras:
        st.subheader("Comparativo entre grupos")
        taxas_por_grupo = []
        for grupo in grupos_disponiveis:
            base_grupo = montar_base(dim, mortalidade, internacoes, grupo)
            base_grupo_filtrada = base_grupo[base_grupo["populacao_censo2022"] >= populacao_minima]
            taxa_geral_grupo = (
                base_grupo_filtrada["obitos"].sum() / base_grupo_filtrada["populacao_censo2022"].sum() * 100_000
                if base_grupo_filtrada["populacao_censo2022"].sum() > 0 else 0
            )
            taxas_por_grupo.append({
                "grupo": f"{ICONE_GRUPO.get(grupo, '')} {grupo}",
                "taxa_mortalidade": taxa_geral_grupo,
                "destaque": grupo == grupo_selecionado,
            })
        df_taxas = pd.DataFrame(taxas_por_grupo).sort_values("taxa_mortalidade")
        st.caption(
            "💡 Taxa de mortalidade = óbitos a cada 100 mil habitantes no período, "
            "permitindo comparar municípios/grupos de tamanhos diferentes."
        )
        fig_barras = px.bar(
            df_taxas, x="taxa_mortalidade", y="grupo", orientation="h",
            color="destaque", color_discrete_map={True: "#dc2626", False: "#cbd5e1"},
            labels={"taxa_mortalidade": "Taxa de mortalidade (por 100 mil hab.)", "grupo": ""},
            text_auto=".1f",
        )
        maior_valor = df_taxas["taxa_mortalidade"].max()
        fig_barras.update_layout(
            showlegend=False, height=480, margin={"t": 10, "r": 60},
            font=dict(size=16),
            xaxis=dict(
                title_font=dict(size=16), tickfont=dict(size=14),
                range=[0, maior_valor * 1.18],  # espaço extra à direita para o rótulo não cortar
            ),
            yaxis=dict(tickfont=dict(size=16)),
        )
        fig_barras.update_traces(textfont_size=16, textposition="outside")
        st.plotly_chart(fig_barras, width="stretch")

    st.divider()

    st.subheader("O que se relaciona com a mortalidade")

    base_filtrada = base_filtrada.copy()
    base_filtrada["destaque"] = base_filtrada["municipio"].isin(municipios_selecionados)

    col_esq, col_dir = st.columns(2)

    with col_esq:
        fig_pib = px.scatter(
            base_filtrada, x="pib_per_capita", y="taxa_mortalidade_100k",
            hover_name="municipio", size="populacao_censo2022",
            color="destaque", color_discrete_map={True: "#dc2626", False: "#93c5fd"},
            title="PIB per capita e mortalidade",
            labels={
                "pib_per_capita": "PIB per capita (R$)",
                "taxa_mortalidade_100k": "Mortalidade (por 100 mil hab.)",
                "populacao_censo2022": "População (Censo 2022)",
            },
            trendline="ols", trendline_scope="overall", trendline_color_override="#6b7280",
        )
        fig_pib.update_layout(
            showlegend=False,
            font=dict(size=14),
            title_font=dict(size=18),
            xaxis=dict(title_font=dict(size=15), tickfont=dict(size=13)),
            yaxis=dict(title_font=dict(size=15), tickfont=dict(size=13)),
        )
        st.plotly_chart(fig_pib, width="stretch")

    with col_dir:
        fig_urb = px.scatter(
            base_filtrada, x="taxa_urbanizacao_pct", y="taxa_mortalidade_100k",
            hover_name="municipio", size="populacao_censo2022",
            color="destaque", color_discrete_map={True: "#dc2626", False: "#93c5fd"},
            title="Taxa de urbanização e mortalidade",
            labels={
                "taxa_urbanizacao_pct": "Taxa de urbanização (%)",
                "taxa_mortalidade_100k": "Mortalidade (por 100 mil hab.)",
                "populacao_censo2022": "População (Censo 2022)",
            },
            trendline="ols", trendline_scope="overall", trendline_color_override="#6b7280",
        )
        fig_urb.update_layout(
            showlegend=False,
            font=dict(size=14),
            title_font=dict(size=18),
            xaxis=dict(title_font=dict(size=15), tickfont=dict(size=13)),
            yaxis=dict(title_font=dict(size=15), tickfont=dict(size=13)),
        )
        st.plotly_chart(fig_urb, width="stretch")
        st.caption(
            "💡 Taxa de urbanização = % da população vivendo em área classificada como urbana "
            "(perímetro urbano oficial do município), em vez de área rural — dado do Censo 2022."
        )

    st.divider()

    st.subheader(f"Top 15 municípios por mortalidade — {grupo_selecionado}")
    top15 = base_filtrada.sort_values("taxa_mortalidade_100k", ascending=False).head(15).copy()
    top15["População (Censo 2022)"] = top15["populacao_censo2022"].apply(lambda v: formatar_numero(v, 0))
    top15["PIB per capita"] = top15["pib_per_capita"].apply(formatar_reais)
    top15["Taxa (por 100 mil hab.)"] = top15["taxa_mortalidade_100k"].apply(lambda v: formatar_numero(v, 1))
    top15["Óbitos (período)"] = top15["obitos"].apply(lambda v: formatar_numero(v, 0))
    top15["Letalidade hospitalar (%)"] = top15["taxa_letalidade_pct"].apply(
        lambda v: formatar_numero(v, 1) if pd.notna(v) else "—"
    )
    st.dataframe(
        top15[[
            "municipio", "População (Censo 2022)", "Óbitos (período)",
            "Taxa (por 100 mil hab.)", "Letalidade hospitalar (%)", "PIB per capita",
        ]].rename(columns={"municipio": "Município"}),
        width="stretch", hide_index=True,
    )
    st.caption(
        "💡 Letalidade hospitalar = óbitos ocorridos durante internação ÷ total de internações "
        "(no sistema hospitalar do SUS) — indica gravidade/desfecho dos casos internados, "
        "diferente da taxa de mortalidade geral (que inclui óbitos fora do hospital também)."
    )

    st.divider()

    st.subheader("📐 O que a regressão estatística diz")
    st.caption("Efeito de cada variável controlando pelas demais — mais confiável que a correlação simples.")

    regressao = carregar_regressao()
    if regressao is not None:
        regressao_grupo = regressao[regressao["grupo_dcnt"] == grupo_selecionado]

        col_tabela, col_texto = st.columns([1, 1.4])

        with col_tabela:
            tabela_exibicao = regressao_grupo[["variavel", "irr", "p_valor", "significativo_5pct"]].copy()
            tabela_exibicao["variavel"] = tabela_exibicao["variavel"].map(
                lambda v: NOME_VARIAVEL.get(v, v)
            )
            st.dataframe(
                tabela_exibicao.rename(columns={
                    "variavel": "Variável", "irr": "IRR", "p_valor": "p-valor",
                    "significativo_5pct": "Signif. (5%)",
                }),
                width="stretch", hide_index=True,
            )
            st.caption("IRR > 1 = aumenta risco · IRR < 1 = protege · só confie se Signif. = True")

        with col_texto:
            for _, linha in regressao_grupo.iterrows():
                classe = "interpretacao-card significativo" if linha["significativo_5pct"] else "interpretacao-card"
                texto_interpretacao = linha["interpretacao"]
                for chave, nome_legivel in NOME_VARIAVEL.items():
                    texto_interpretacao = texto_interpretacao.replace(chave, nome_legivel)
                st.markdown(
                    f'<div class="{classe}">{texto_interpretacao}</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Rode `python src/modelagem_regressao.py` para ver os resultados da regressão aqui.")

    st.divider()
    st.caption(
        "📊 Análise, coleta de dados e desenvolvimento: **Letícia Borges** · "
        "Dados públicos: DATASUS (SIM/SIH), IBGE"
    )


if __name__ == "__main__":
    main()
