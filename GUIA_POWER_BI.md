# Guia: construindo o painel no Power BI Desktop

Pré-requisito: já ter rodado `python src/exportar_powerbi.py`, que gera
`outputs/dataset_powerbi.xlsx` com 3 abas (`fato_indicadores`, `dim_municipios`,
`resultado_regressao`).

Se ainda não tem o Power BI Desktop instalado: é gratuito, baixe em
https://powerbi.microsoft.com/pt-br/desktop/ (só funciona em Windows).

---

## 1. Importar os dados

1. Abra o Power BI Desktop
2. Página inicial → **Obter dados** → **Excel**
3. Selecione `outputs/dataset_powerbi.xlsx`
4. Marque as 3 abas (`fato_indicadores`, `dim_municipios`, `resultado_regressao`) → **Carregar**

## 2. Criar o relacionamento entre as tabelas

1. Vá na aba **Modelo** (ícone de relacionamento, painel esquerdo)
2. Arraste `codigo_ibge` de `dim_municipios` até `codigo_ibge` em `fato_indicadores`
3. Confirme que o relacionamento ficou "1 para muitos" (um município aparece uma vez em
   `dim_municipios`, mas várias vezes em `fato_indicadores` — uma por grupo de DCNT)

Isso cria a estrutura de "esquema estrela", que é a forma correta de modelar dados no Power BI
— evita duplicação e deixa os filtros mais rápidos e consistentes.

## 3. Criar medidas (DAX) — o "vocabulário" do seu painel

Na aba **Relatório**, clique com o botão direito em `fato_indicadores` → **Nova medida**, e crie
estas (uma de cada vez):

```dax
Mortalidade Média (100k) = AVERAGE(fato_indicadores[taxa_mortalidade_100k])
```

```dax
Internação Média (100k) = AVERAGE(fato_indicadores[taxa_internacao_100k])
```

```dax
Letalidade Média (%) = AVERAGE(fato_indicadores[taxa_letalidade_pct])
```

```dax
Total de Óbitos = SUM(fato_indicadores[obitos])
```

## 4. Montar as páginas do painel

Sugestão de 3 páginas:

### Página 1 — Visão geral
- **Cartões** (visual "Cartão"): `Total de Óbitos`, `Mortalidade Média (100k)`
- **Gráfico de barras**: eixo = `grupo_dcnt`, valor = `Mortalidade Média (100k)`
  (mostra qual DCNT mata mais, no agregado de SC)
- **Segmentação de dados** (slicer): por `grupo_dcnt`, para filtrar o resto da página

### Página 2 — Distribuição geográfica
- **Mapa de formas** ou **Mapa** (visual nativo do Power BI): campo de local = município
  (do jeito que o Power BI reconhece nomes de município brasileiro, pode ser necessário
  ativar "Mapas Preenchidos" ou usar um mapa de formas customizado do SC — pesquise
  "shape map Santa Catarina Power BI" se o reconhecimento automático falhar)
- Valor = `Mortalidade Média (100k)`, com segmentação por `grupo_dcnt`
- **Tabela/matriz**: município x grupo_dcnt x taxa de mortalidade, ordenável — permite ver
  ranking de municípios mais afetados

### Página 3 — O que explica as diferenças (a pergunta central do projeto)
- **Gráfico de dispersão**: eixo X = `pib_per_capita` (de `dim_municipios`), eixo Y =
  `taxa_mortalidade_100k` (de `fato_indicadores`), com detalhe = `municipio`
- **Tabela da aba `resultado_regressao`**: mostre `variavel`, `irr`, `p_valor`,
  `significativo_5pct` — essa é a tabela que responde literalmente "quais variáveis
  influenciam e quanto"
- Adicione um **texto explicativo** ao lado: "IRR (Razão de Taxa de Incidência) acima de 1
  indica que a variável aumenta o risco; abaixo de 1, indica proteção. Só considere
  confiável quando 'significativo_5pct' = Sim."

## 5. Formatação e identidade visual

- Escolha uma paleta de cores consistente (evite usar as cores padrão do Power BI sem
  ajuste — passa impressão de protótipo não finalizado)
- Adicione um título geral no topo de cada página
- Use tooltips (dica de ferramenta) explicando cada indicador, para quem não é da área de
  saúde entender rapidamente

## 6. Como mostrar isso no portfólio

O Power BI Desktop gera um arquivo `.pbix`, que **não abre direto no GitHub** (não é um
formato que o GitHub sabe exibir). Três formas de resolver:

**Opção A — Publicar no Power BI Service (mais impressionante, mas fica público de verdade)**
1. No Power BI Desktop: **Página Inicial → Publicar**
2. Crie uma conta gratuita no Power BI Service se ainda não tiver
3. Depois de publicado, no site do Power BI: **Arquivo → Inserir relatório → Publicar na Web**
4. Isso gera um link/iframe público — cole esse link no seu README do GitHub
5. ⚠️ **Atenção**: "Publicar na Web" torna o relatório visível para qualquer pessoa com o
   link, sem exigir login. Como você já decidiu manter esse projeto com dados 100% públicos,
   não tem problema — mas nunca faça isso com um relatório que tenha dado de cliente.

**Opção B — Exportar como PDF ou imagens**
1. No Power BI Desktop: **Arquivo → Exportar → Exportar para PDF**
2. Tire prints de cada página, ou converta o PDF em imagens
3. Suba essas imagens na pasta `outputs/` do repositório e referencie no README:
   ```markdown
   ![Painel geral](outputs/powerbi_pagina1.png)
   ```
   Isso é mais simples e mais seguro (não expõe nada ao vivo), mas perde a interatividade.

**Opção C — Gravar um GIF curto navegando pelo painel**
Ferramentas gratuitas como ScreenToGif (Windows) gravam a tela; um GIF de 10-15 segundos
mostrando os filtros funcionando no README costuma impressionar mais do que print estático.

Recomendo **B ou C** para portfólio (mais seguro e você mantém controle total), e deixar a
**Opção A** como algo a considerar mais adiante, se quiser.
