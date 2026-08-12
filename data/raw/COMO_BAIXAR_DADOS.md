# Como baixar os dados de mortalidade e internações (TabNet/DATASUS)

Você vai baixar **8 arquivos no total**: 4 de mortalidade (SIM) + 4 de internações (SIH), um
para cada grupo de DCNT.

## ⚠️ Nota metodológica importante

Os dados de internação (SIH) usados aqui são **"por local de internação"** (o município onde
fica o hospital), não "por local de residência" (onde o paciente mora) — o DATASUS não
disponibiliza publicamente a versão por residência com detalhamento de diagnóstico (CID-10) de
forma acessível. Isso significa que municípios com hospital (municípios-polo) tendem a
concentrar números mais altos de internação, enquanto municípios menores, que dependem de
encaminhar pacientes para cidades vizinhas, podem aparecer artificialmente "mais saudáveis"
nesse indicador específico. Já os dados de mortalidade (SIM) usados são por município de
ocorrência do óbito — verifique a mesma ressalva se for comparar diretamente.

## Parte 1 — Mortalidade (SIM)

Acesse: **tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/obt10sc.def**

Para cada um dos 4 grupos, configure:

- **Linha**: Município
- **Coluna**: Ano do óbito
- **Conteúdo**: Óbitos p/ Ocorrência
- **Período**: selecione o intervalo de anos desejado (usamos 2019 a 2023 no projeto)
- **Categoria CID-10**: filtra o(s) código(s) do grupo:

| Grupo | Categoria CID-10 | Nome do arquivo de saída |
|---|---|---|
| Cardiovascular | I00 a I99 | `cardiovascular_obitos.csv` |
| Câncer | C00 a C97 | `neoplasias_obitos.csv` |
| Diabetes | E10 a E14 | `diabetes_obitos.csv` |
| Respiratória crônica | J40 a J47 | `respiratorias_obitos.csv` |

Depois de gerar cada tabela, exporte como CSV e salve em `data/raw/sim/` com o nome exato
indicado acima.

## Parte 2 — Internações e óbitos hospitalares (SIH)

Acesse: **tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nisc.def**

(Se esse endereço não funcionar, tente a versão nacional:
`tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/niuf.def` — nesse caso, baixe todos os
municípios do Brasil; o script de tratamento já filtra automaticamente só SC pelo código
IBGE, mas confira se há uma opção de restringir por UF na tela.)

Para cada um dos 4 grupos, configure:

- **Linha**: Município
- **Coluna**: **"Não ativa"** — importante: ao marcar "Internações" e "Óbitos" juntos no
  Conteúdo, o TabNet exige que a coluna fique inativa (o resultado sai já agregado para o
  período inteiro, sem quebra por ano)
- **Conteúdo**: marque **as duas opções ao mesmo tempo** — "Internações" e "Óbitos"
- **Período**: mesmo intervalo usado na mortalidade (2019-2023)
- **Categoria**: use **"Capítulo CID-10"** quando o capítulo bater certinho com o grupo (ex.:
  Cardiovascular = "IX. Doenças do aparelho circulatório"); para os demais grupos, use a
  caixa de busca dentro de **"Lista Morb CID-10"** (tem um campo "Digite o texto e ache
  fácil") — por exemplo, busque "maligna" para Câncer, "diabetes" para Diabetes, e
  "bronquite"/"asma"/"enfisema"/"DPOC" para Respiratória crônica

| Grupo | Nome do arquivo de saída |
|---|---|
| Cardiovascular | `cardiovascular_internacoes.csv` |
| Câncer | `neoplasias_internacoes.csv` |
| Diabetes | `diabetes_internacoes.csv` |
| Respiratória crônica | `respiratorias_internacoes.csv` |

Salve em `data/raw/sih/`.

## Formato esperado (já testado com dado real)

- **SIM**: colunas `Município;2019;2020;2021;2022;2023;Total` — uma coluna por ano, mais um
  total agregado (o script ignora a coluna Total, calcula a partir dos anos individuais).
- **SIH**: colunas `Município;Internações;Óbitos` — já vem agregado no período inteiro, sem
  quebra por ano (por causa da limitação do TabNet mencionada acima).
- Em ambos, o código do município vem com **6 dígitos** (não 7 — o TabNet omite o dígito
  verificador do código IBGE completo). Os scripts de tratamento já lidam com isso.
- Municípios sem nenhum caso no período **não aparecem no arquivo** (não é erro — o script
  trata isso automaticamente).

## Se o TabNet estiver indisponível ou mudar de layout

O DATASUS ocasionalmente reorganiza essas URLs. Se o link não funcionar, busque por "TabNet
DATASUS Santa Catarina" e procure os links de "Mortalidade Geral" (SIM) e "Morbidade
Hospitalar do SUS" (SIH) na seção de Santa Catarina — e, se o formato do arquivo baixado vier
diferente do descrito acima, cole as primeiras linhas do arquivo na conversa para ajustar o
script.
