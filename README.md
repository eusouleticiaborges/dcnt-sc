# Doenças Crônicas Não Transmissíveis (DCNT) em Santa Catarina

Análise da relação entre indicadores socioeconômicos e a ocorrência de Doenças Crônicas Não
Transmissíveis (DCNT) nos 295 municípios de Santa Catarina, com painel interativo publicado.

**🔗 Painel ao vivo: [dcnt-santa-catarina.streamlit.app](https://dcnt-santa-catarina.streamlit.app/)**

## 🎯 Objetivo

Identificar se — e como — indicadores socioeconômicos municipais (PIB per capita e taxa de
urbanização) se associam à mortalidade, internação hospitalar e letalidade hospitalar das
quatro principais DCNT (cardiovascular, câncer, diabetes e doenças respiratórias crônicas) em
Santa Catarina, usando modelagem estatística formal — não apenas correlação simples.

## 📈 Principais resultados

A regressão (Binomial Negativa, ver metodologia abaixo) encontrou:

- **Taxa de urbanização** está associada a **aumento estatisticamente significativo** na
  mortalidade nos **4 grupos de DCNT**, mesmo controlando pelo PIB per capita:
  - Câncer: +23,6% de mortalidade a cada desvio-padrão de aumento na urbanização
  - Cardiovascular: +16,3%
  - Diabetes: +12,4%
  - Respiratória crônica: +11,0%
- **PIB per capita** não apresentou efeito estatisticamente significativo em nenhum dos 4
  grupos neste recorte de variáveis — um resultado tão válido de reportar quanto um efeito
  significativo, já que contraria a intuição de que "cidade mais rica é mais saudável" de
  forma simplista.

O painel permite explorar isso interativamente por grupo de DCNT, incluindo mapa por
município, ranking, e a tabela completa de coeficientes da regressão.

## 📊 Dados utilizados

| Fonte | Dado | Acesso |
|---|---|---|
| SIM/DATASUS (TabNet) | Óbitos por causa (CID-10), por município, 2019-2023 | Download manual |
| SIH/DATASUS (TabNet) | Internações e óbitos hospitalares por causa (CID-10), 2019-2023 | Download manual |
| IBGE (SIDRA) | População (Censo 2022), PIB per capita, taxa de urbanização | Download manual (ver nota abaixo) |
| [geodata-br](https://github.com/tbrugz/geodata-br) / malha municipal do IBGE | Contornos geográficos dos municípios de SC, para o mapa | Incluído no repositório |

**Nota sobre o IBGE**: a coleta automática via API foi tentada primeiro, mas se mostrou pouco
confiável durante o desenvolvimento (tabelas com nomes de coluna inconsistentes, períodos
indisponíveis). O caminho que efetivamente funciona é baixar manualmente do SIDRA e consolidar
com `src/consolidar_ibge_manual.py` — ver instruções em `data/raw/COMO_BAIXAR_DADOS.md` para a
parte de saúde, e o próprio script para a parte do IBGE.

### Indicadores calculados

- **Taxa de mortalidade** (óbitos ÷ população × 100.000)
- **Taxa de internação** (internações ÷ população × 100.000)
- **Letalidade hospitalar** (óbitos ocorridos durante internação ÷ total de internações) —
  indica gravidade/desfecho dos casos que chegam a ser internados, diferente da taxa de
  mortalidade geral (que inclui óbitos fora do ambiente hospitalar)
- **Taxa de urbanização** (população urbana ÷ população total × 100, Censo 2022) — percentual
  da população do município vivendo em área classificada como urbana (em vez de rural). Essa é
  uma classificação administrativa (definida pelo perímetro urbano oficial de cada município,
  não por características territoriais reais), que é o padrão usado pelo IBGE em todo o Brasil.

## 🗂️ Estrutura do repositório

```
dcnt-sc/
├── app.py                          # painel interativo (Streamlit) — o entregável principal
├── data/
│   ├── dcnt_sc.db                  # banco de dados SQLite (dados públicos, versionado)
│   ├── sc_municipios.geojson       # contornos geográficos dos municípios (para o mapa)
│   ├── raw/
│   │   ├── sim/                    # 4 arquivos de óbitos (um por grupo de DCNT)
│   │   ├── sih/                    # 4 arquivos de internações/óbitos hospitalares
│   │   └── COMO_BAIXAR_DADOS.md    # passo a passo do download manual (TabNet)
│   └── processed/
├── src/
│   ├── consolidar_ibge_manual.py   # consolida população/urbanização/PIB (IBGE, SIDRA)
│   ├── tratamento_mortalidade.py   # trata os 4 arquivos do SIM
│   ├── tratamento_internacoes.py   # trata os 4 arquivos do SIH
│   ├── criar_banco_sqlite.py       # monta o banco de dados central
│   ├── analise_exploratoria.py     # correlações e gráficos exploratórios
│   └── modelagem_regressao.py      # regressão binomial negativa + checagem de VIF
├── outputs/
│   └── tabela_regressao_dcnt.csv   # resultado final da regressão (lido pelo painel)
├── requirements.txt
└── README.md
```

## 🚀 Como reproduzir

```bash
pip install -r requirements.txt

# 1. Dados socioeconômicos do IBGE
#    (baixe manualmente do SIDRA seguindo as instruções em consolidar_ibge_manual.py,
#    salve os 3 arquivos em data/raw/, depois rode:)
python src/consolidar_ibge_manual.py

# 2. Baixe manualmente os 8 arquivos de saúde do TabNet — ver data/raw/COMO_BAIXAR_DADOS.md

# 3. Trate os dados de saúde baixados
python src/tratamento_mortalidade.py
python src/tratamento_internacoes.py

# 4. Monte o banco de dados central
python src/criar_banco_sqlite.py

# 5. Análise exploratória (correlações e gráficos)
python src/analise_exploratoria.py

# 6. Modelagem estatística (regressão)
python src/modelagem_regressao.py

# 7. Rode o painel
streamlit run app.py
```

## 🧮 Metodologia estatística

A pergunta "quais variáveis influenciam e quanto" exige mais do que correlação simples — uma
regressão múltipla controla o efeito de cada variável isoladamente, considerando as demais.
Como a variável de desfecho é uma contagem de óbitos (não uma medida contínua normal), o
projeto usa **regressão Binomial Negativa com offset de população** — o padrão em epidemiologia
para dados de contagem por área geográfica com populações de tamanhos diferentes. Os resultados
são reportados como **Razão de Taxa de Incidência (IRR)**: valores acima de 1 indicam aumento
de risco, abaixo de 1 indicam proteção, sempre por desvio-padrão de aumento na variável
(as variáveis são padronizadas para permitir comparação direta de magnitude entre elas).

O script `modelagem_regressao.py` também calcula automaticamente o **VIF (Variance Inflation
Factor)** de cada variável, alertando sobre multicolinearidade — relevante caso o projeto seja
estendido com mais variáveis no futuro (ver "Próximos passos" abaixo).

## 📝 Limitações

- **Apenas 2 variáveis socioeconômicas foram efetivamente coletadas e modeladas**: PIB per
  capita e taxa de urbanização. Outras variáveis relevantes (Índice de Gini, IDHM, renda per
  capita, indicadores de mercado de trabalho via RAIS/CAGED) foram cogitadas durante o
  desenvolvimento do projeto, mas não chegaram a ser coletadas — ver "Próximos passos".
- Dados de mortalidade/internação estão sujeitos a subnotificação e à qualidade do
  preenchimento da causa básica, que varia entre municípios.
- **Municípios pequenos podem ter taxas instáveis** por conta do denominador populacional
  baixo. Isso é tratado corretamente na regressão (que pondera pelo tamanho da população via
  offset), mas **não** na tabela de correlação simples exploratória — trate essa parte como
  panorama inicial, não como evidência robusta.
- Análise é ecológica (nível municipal) — correlações/associações não implicam causalidade
  individual.
- **Internações são "por local de internação"**, não "por local de residência" — o DATASUS não
  disponibiliza publicamente a versão por residência com detalhamento de diagnóstico (CID-10)
  de forma acessível. Municípios-polo (com hospital) tendem a concentrar números mais altos de
  internação; municípios menores que encaminham pacientes podem parecer artificialmente "mais
  saudáveis" nesse indicador específico. Mortalidade (SIM) já é por local de ocorrência do óbito.
- Por uma limitação do TabNet (a combinação "Internações + Óbitos" no mesmo conteúdo exige
  coluna inativa), os dados de internação não têm quebra por ano — são um total agregado do
  período inteiro (2019-2023), diferente da mortalidade, que mantém detalhamento anual.
- Letalidade hospitalar reflete apenas óbitos ocorridos dentro do sistema hospitalar do SUS;
  não captura óbitos domiciliares ou em rede privada sem AIH.

## 🔮 Próximos passos (não implementados neste repositório)

- **Mais variáveis socioeconômicas**: Índice de Gini, IDHM e renda per capita (via Atlas
  Brasil/PNUD) e indicadores de mercado de trabalho (via RAIS/CAGED, usando a plataforma Base
  dos Dados) foram cogitados durante o desenvolvimento, mas não foram efetivamente coletados.
- **Índice de Moran (autocorrelação espacial)**: municípios vizinhos tendem a compartilhar
  determinantes socioeconômicos e ambientais — ignorar essa dependência espacial pode inflar
  artificialmente a significância estatística da regressão.
- **Random Forest** como checagem complementar não-paramétrica da regressão.
- **PCA e análise de cluster** para segmentar municípios por perfil socioeconômico — desenhado
  mas não testado com o conjunto final de variáveis (que hoje tem só 2 candidatas).

## 🔧 Tecnologias

Python · pandas · SQLite · statsmodels (regressão Binomial Negativa) · Streamlit · Plotly ·
Folium (mapa)

## 👤 Autoria

Análise, coleta de dados e desenvolvimento: **Letícia Borges**

## 📄 Licença

MIT — ver `LICENSE`
