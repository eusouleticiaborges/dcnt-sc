# Como baixar os indicadores do Atlas do Desenvolvimento Humano no Brasil

O Atlas Brasil (parceria PNUD/IPEA/Fundação João Pinheiro) é a fonte mais rica de indicadores
socioeconômicos municipais em um único lugar — um único download já traz dezenas de variáveis,
sem precisar caçar uma API para cada uma.

## Passo a passo

1. Acesse http://www.atlasbrasil.org.br/consulta
2. Em "Unidade Geográfica", selecione **Santa Catarina** → **Todos os municípios**
3. Em "Indicadores", marque **todos** os que forem relevantes (veja tabela abaixo — dá pra
   marcar vários de uma vez)
4. Clique em **Consultar** e depois em **Exportar** (formato Excel/CSV)
5. Salve o arquivo como `data/raw/atlas_brasil_sc.csv`

## Indicadores recomendados para marcar

| Indicador no site | Nome sugerido na base | O que mede |
|---|---|---|
| IDHM | `idhm` | Índice de Desenvolvimento Humano Municipal |
| IDHM Renda | `idhm_renda` | Sub-índice de renda do IDHM |
| IDHM Longevidade | `idhm_longevidade` | Sub-índice de expectativa de vida |
| IDHM Educação | `idhm_educacao` | Sub-índice de escolaridade |
| Índice de Gini | `gini` | Desigualdade de renda (0 = igualdade total, 1 = desigualdade máxima) |
| Renda per capita | `renda_per_capita` | Renda domiciliar média por pessoa |
| % de pobres | `taxa_pobreza` | % da população com renda domiciliar per capita abaixo da linha de pobreza |
| Taxa de analfabetismo (18+) | `taxa_analfabetismo` | % da população adulta que não sabe ler/escrever |
| Esperança de vida ao nascer | `esperanca_vida` | Expectativa de vida em anos |

Não precisa usar todos — mas quanto mais você incluir, mais completo fica o modelo depois
(lembrando do cuidado com multicolinearidade, que o script de regressão já verifica
automaticamente).

## Formato esperado

Assim como o download de IDHM isolado, esse arquivo não vem com o código IBGE de 6 dígitos —
só o nome do município. O script `src/juntar_variaveis_socioeconomicas.py` faz esse cruzamento
por nome (normalizado, sem acento, minúsculo) automaticamente. Se os nomes das colunas
exportadas pelo site vierem diferentes da tabela acima, ajuste o dicionário `MAPEAMENTO_COLUNAS`
no topo desse script.
