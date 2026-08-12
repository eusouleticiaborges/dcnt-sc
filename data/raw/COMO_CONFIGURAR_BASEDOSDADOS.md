# Como configurar o acesso à RAIS e ao CAGED via Base dos Dados (BigQuery)

A Base dos Dados (basedosdados.org) hospeda microdados da RAIS e do CAGED já tratados, num
"data lake" público no Google BigQuery. O acesso é gratuito (1 TB de consulta por mês, sem
precisar de cartão de crédito), mas exige uma configuração inicial.

## Passo a passo

### 1. Criar um projeto no Google Cloud

1. Acesse https://console.cloud.google.com (use sua conta Google normal)
2. Clique em **Criar Projeto**, dê um nome (ex.: `portfolio-dcnt-sc`)
3. Anote o **Project ID** gerado — vai ser usado no código (é diferente do nome que você digitou)
4. Não é necessário adicionar cartão de crédito — o BigQuery abre automaticamente no modo
   Sandbox, que não cobra nada dentro do limite gratuito

### 2. Instalar o pacote Python

```bash
pip install basedosdados
```

(já está incluído no `requirements.txt` deste projeto)

### 3. Autenticar

Na primeira vez que você rodar qualquer função do pacote, ele vai abrir uma janela do navegador
pedindo para você fazer login na sua conta Google e autorizar o acesso. Basta seguir o fluxo —
depois disso fica salvo localmente e você não precisa repetir.

### 4. Testar

```python
import basedosdados as bd

df = bd.read_sql(
    "SELECT COUNT(*) as total FROM `basedosdados.br_me_rais.microdados_vinculos` "
    "WHERE sigla_uf = 'SC' AND ano = 2022 LIMIT 10",
    billing_project_id="SEU_PROJECT_ID_AQUI"
)
print(df)
```

Se retornar um número (não um erro), está tudo configurado.

## Sobre o volume de dados

A tabela de microdados da RAIS tem centenas de GB no total, mas como o script deste projeto
filtra por `sigla_uf = 'SC'` e por ano, o volume processado por consulta fica bem menor — dentro
do limite gratuito mensal tranquilamente, mesmo rodando o script várias vezes durante o
desenvolvimento.

## Se preferir não usar BigQuery

Essa é a via mais rica em variáveis, mas também a mais avançada tecnicamente. Se em algum
momento achar complexo demais, o projeto continua funcional só com IBGE + Atlas Brasil (já
implementados) — a análise perde a camada de mercado de trabalho, mas continua válida e completa
o suficiente para portfólio.
