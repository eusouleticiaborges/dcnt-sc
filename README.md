# Doenças Crônicas Não Transmissíveis (DCNT) em Santa Catarina: mortalidade, internações e relação com indicadores socioeconômicos

## 🎯 Objetivo

Identificar **quais** variáveis socioeconômicas — econômicas (PIB, renda), de desigualdade
(Gini, pobreza), educacionais (analfabetismo), estruturais (urbanização) e de mercado de
trabalho (saldo de empregos formais, salário médio) — estão associadas à ocorrência das quatro
principais Doenças Crônicas Não Transmissíveis (DCNT) nos municípios de Santa Catarina, e
**como** (direção e força do efeito) — usando modelagem estatística formal, não apenas
correlação simples. O projeto cobre todo o ciclo: coleta de dados públicos → tratamento →
modelagem estatística → painel interativo no Power BI.

Grupos de DCNT analisados (conforme classificação da OMS/OPAS, os "4 grandes grupos"):

| Grupo | CID-10 |
|---|---|
| Doenças cardiovasculares | I00–I99 |
| Neoplasias malignas (câncer) | C00–C97 |
| Diabetes mellitus | E10–E14 |
| Doenças respiratórias crônicas | J40–J47 |

## 🧑‍🔬 Motivação

DCNT são hoje a principal causa de morte no Brasil e no mundo, e sua distribuição está fortemente
associada a determinantes sociais de saúde (renda, escolaridade, acesso a serviços). Este projeto
conecta minha experiência prévia em epidemiologia (doutorado em saúde pública/segurança de
alimentos) com meu trabalho atual em dados socioeconômicos da administração pública de SC —
usando as mesmas bases de indicadores que utilizo profissionalmente, aplicadas a uma pergunta de
saúde pública.

## 📊 Indicadores calculados (por município, por grupo de DCNT)

1. **Taxa de mortalidade geral** — óbitos (SIM) / população × 100.000 hab.
2. **Taxa de internação hospitalar** — internações (SIH) / população × 100.000 hab.
3. **Taxa de letalidade hospitalar** — óbitos ocorridos durante internação (SIH) / internações (SIH) × 100

> **Nota metodológica**: a letalidade hospitalar usa numerador e denominador da mesma fonte (SIH),
> o que é metodologicamente correto. Não se deve dividir óbitos do SIM por internações do SIH —
> são sistemas de notificação diferentes, com populações de referência distintas.

## 📊 Dados utilizados

| Fonte | Dado | Acesso |
|---|---|---|
| SIM/DATASUS (TabNet) | Óbitos por causa (CID-10), por município de SC | Download manual |
| SIH/DATASUS (TabNet) | Internações e óbitos hospitalares por causa (CID-10), por município de SC | Download manual |
| IBGE (API SIDRA) | População estimada, PIB per capita, taxa de urbanização | API REST automática |
| Atlas Brasil (PNUD/IPEA/FJP) | IDHM (e sub-índices), Gini, renda per capita, pobreza, analfabetismo, esperança de vida | Download manual |
| RAIS (via Base dos Dados/BigQuery) | Salário médio, horas contratadas, % força de trabalho com ensino superior | SQL (Python) |
| CAGED (via Base dos Dados/BigQuery) | Admissões, desligamentos, saldo de empregos, salário médio de admissão | SQL (Python) |

## 🗄️ Banco de dados

O projeto usa **SQLite** como banco de dados central — um banco de dados real (não CSVs
soltos), mas que vive num único arquivo (`data/dcnt_sc.db`), sem exigir instalação de servidor.
Todos os dados coletados e tratados são carregados nele antes de seguir para análise ou
exportação, o que garante uma única fonte de verdade para o projeto, consultável via SQL.

O arquivo do banco não é versionado no Git (por conter dado, mesmo que público) — ele é gerado
localmente a partir dos CSVs coletados, rodando `python src/criar_banco_sqlite.py`.

## 🗂️ Estrutura do repositório

```
dcnt-sc/
├── data/
│   ├── raw/
│   │   ├── sim/          # 4 arquivos de óbitos (um por grupo de DCNT)
│   │   ├── sih/          # 4 arquivos de internações/óbitos hospitalares
│   │   ├── COMO_BAIXAR_DADOS.md
│   │   ├── COMO_ADICIONAR_ATLAS_BRASIL.md
│   │   └── COMO_CONFIGURAR_BASEDOSDADOS.md
│   └── processed/
├── src/
│   ├── coleta_ibge.py                     # dados socioeconômicos via API IBGE
│   ├── consolidar_ibge_manual.py          # consolida população/urbanização/PIB baixados manualmente
│   ├── coleta_rais_caged.py               # RAIS + CAGED via Base dos Dados (BigQuery)
│   ├── tratamento_mortalidade.py          # trata os 4 arquivos do SIM
│   ├── tratamento_internacoes.py          # trata os 4 arquivos do SIH
│   ├── juntar_variaveis_socioeconomicas.py# consolida IBGE + Atlas Brasil + RAIS/CAGED
│   ├── criar_banco_sqlite.py              # monta o banco de dados central (SQLite)
│   ├── analise_exploratoria.py            # correlações e gráficos
│   ├── pca_e_cluster.py                   # redução de dimensionalidade e segmentação
│   ├── modelagem_regressao.py             # regressão binomial negativa + checagem de VIF
│   └── exportar_powerbi.py                # lê do banco e gera o Excel para o Power BI
├── outputs/
├── GUIA_POWER_BI.md
├── requirements.txt
└── README.md
```

## 🚀 Como reproduzir

```bash
pip install -r requirements.txt

# 1. Dados socioeconômicos básicos do IBGE (automático)
python src/coleta_ibge.py

# 2. Dados de mercado de trabalho (RAIS + CAGED via BigQuery)
#    ver data/raw/COMO_CONFIGURAR_BASEDOSDADOS.md antes de rodar
python src/coleta_rais_caged.py

# 3. Baixe manualmente:
#    - os 8 arquivos do TabNet — ver data/raw/COMO_BAIXAR_DADOS.md
#    - o Atlas Brasil — ver data/raw/COMO_ADICIONAR_ATLAS_BRASIL.md

# 4. Trate os dados de saúde baixados
python src/tratamento_mortalidade.py
python src/tratamento_internacoes.py

# 5. Consolide todas as fontes socioeconômicas em uma única base
python src/juntar_variaveis_socioeconomicas.py

# 6. Análise exploratória (correlações e gráficos)
python src/analise_exploratoria.py

# 7. Redução de dimensionalidade e segmentação de municípios
python src/pca_e_cluster.py

# 8. Modelagem estatística (quais variáveis importam e quanto, com checagem de multicolinearidade)
python src/modelagem_regressao.py

# 9. Exportar dataset pronto para o Power BI
python src/exportar_powerbi.py

# 10. Construir o painel — ver GUIA_POWER_BI.md
```

## 🧮 Metodologia estatística

A pergunta "quais e como variáveis influenciam" exige mais do que correlação — uma regressão
múltipla controla o efeito de cada variável isoladamente, considerando as demais. Como a
variável de desfecho é uma contagem de óbitos (não uma medida contínua normal), o projeto usa
**regressão Binomial Negativa com offset de população**, o padrão em epidemiologia para dados de
contagem por área geográfica com populações de tamanhos diferentes. Os resultados são reportados
como **Razão de Taxa de Incidência (IRR)**: valores acima de 1 indicam aumento de risco, abaixo
de 1 indicam proteção, sempre por desvio-padrão de aumento na variável (as variáveis são
padronizadas para permitir comparação direta de magnitude entre elas).

Com muitas variáveis socioeconômicas candidatas (PIB, renda per capita, Gini, IDHM etc.), várias
delas medem dimensões parecidas e tendem a ser altamente correlacionadas entre si — isso é
**multicolinearidade**, e infla a incerteza dos coeficientes estimados. O script
`modelagem_regressao.py` calcula automaticamente o **VIF (Variance Inflation Factor)** de cada
variável antes de reportar os resultados, alertando quando duas ou mais variáveis do modelo
estão competindo pelo mesmo "crédito" estatístico — nesse caso, a recomendação é manter apenas
uma variável por dimensão conceitual (ex.: escolher entre PIB *ou* renda per capita, não os
dois), em vez de confiar cegamente nos coeficientes de um modelo com colinearidade alta.

### Redução de dimensionalidade e segmentação (PCA e cluster)

Com o número de variáveis socioeconômicas ampliado (IBGE + Atlas Brasil + RAIS/CAGED), duas
técnicas complementares ajudam além da checagem de VIF:

- **Análise de Componentes Principais (PCA)**: resume as variáveis originais em poucos "eixos"
  compostos que capturam a maior parte da variação entre municípios, sem a redundância das
  variáveis originais. Pode substituir as variáveis originais na regressão quando o VIF estiver
  persistentemente alto.
- **Cluster (k-means)**: agrupa municípios com perfil socioeconômico parecido, escolhendo o
  número de grupos automaticamente via coeficiente de silhueta. Permite perguntas mais diretas
  como "o cluster de municípios menos desenvolvidos tem mortalidade por DCNT
  significativamente maior?" — e gera uma variável categórica útil como filtro no painel do
  Power BI.

### Próximos passos metodológicos (não implementados neste repositório, mas recomendados)

- **Índice de Moran (autocorrelação espacial)**: municípios vizinhos tendem a compartilhar
  determinantes socioeconômicos e ambientais — ignorar essa dependência espacial pode inflar
  artificialmente a significância estatística da regressão. Bibliotecas como `esda`/`libpysal`
  (Python) implementam isso.
- **Random Forest (importância de variáveis)**: como checagem complementar não-paramétrica da
  regressão — se as mesmas variáveis aparecem como relevantes nos dois métodos, a evidência
  fica mais robusta.

## 📈 Principais resultados

*(a preencher conforme a análise avança)*

## 📝 Limitações

- Dados de mortalidade/internação estão sujeitos a subnotificação e a qualidade do preenchimento
  da causa básica de óbito, que varia entre municípios.
- **Municípios pequenos podem ter taxas instáveis por conta do denominador populacional baixo**
  (poucos casos geram taxas muito altas ou muito baixas por acaso). Essa limitação é tratada de
  forma desigual entre as duas análises deste projeto:
  - Na **modelagem por regressão** (`modelagem_regressao.py`), isso já é levado em conta
    corretamente: o método (Binomial Negativa com offset de população) pondera explicitamente
    pelo tamanho de cada município, em vez de tratar a taxa como um número plano — é o resultado
    estatisticamente mais confiável do projeto.
  - Na **tabela de correlação simples**, exploratória (`analise_exploratoria.py`), esse cuidado
    **não é aplicado** — cada município entra com o mesmo peso, independente do tamanho da
    população ou do número absoluto de casos. Um município pequeno com poucos casos pode gerar
    uma taxa por 100 mil habitantes tão ou mais "extrema" quanto uma cidade grande com muito
    mais casos, distorcendo a correlação. Trate essa parte como panorama descritivo inicial, não
    como evidência robusta — a conclusão de peso do projeto vem da regressão.
- Análise é ecológica (nível municipal) — correlações não implicam causalidade individual.
- Letalidade hospitalar reflete apenas óbitos ocorridos dentro do sistema hospitalar SUS; não
  captura óbitos domiciliares ou em rede privada sem AIH.
- **Internações são "por local de internação", não "por local de residência"** — o DATASUS não
  disponibiliza publicamente a versão por residência com detalhamento de diagnóstico (CID-10)
  de forma acessível. Isso significa que municípios-polo (com hospital) tendem a concentrar
  números mais altos de internação, enquanto municípios menores que encaminham pacientes para
  cidades vizinhas podem parecer artificialmente "mais saudáveis" nesse indicador específico.
  Mortalidade (SIM) já é por local de ocorrência do óbito.
- Por uma limitação do TabNet (a combinação "Internações + Óbitos" no mesmo conteúdo exige
  coluna inativa), os dados de internação não têm quebra por ano — são um total agregado do
  período inteiro (2019-2023), diferente da mortalidade, que mantém detalhamento anual.

## 🔧 Tecnologias

Python 3.11 · pandas · requests · matplotlib/seaborn · scipy

## 👤 Autor

*(seu nome, LinkedIn, contato)*
