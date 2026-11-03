# Pipeline de Dados: Viagens a Serviço do Governo Federal

Projeto avaliativo do Módulo 1 (Análise de Dados com Python, turma T6).
Autor: Felipe Costa.

Pipeline de dados de ponta a ponta (ETL) em **Python + PostgreSQL**, seguindo a
**Arquitetura Medallion** (camadas Raw, Silver e Gold). Ele baixa os dados de
Viagens a Serviço do Portal da Transparência, preserva o dado original, limpa e
modela as tabelas e responde perguntas de negócio com SQL, tabelas e gráficos.

## Problema que o projeto resolve

O Portal da Transparência publica os dados de viagens a serviço em forma bruta:
arquivos CSV com vírgula como separador decimal, datas em `DD/MM/AAAA`, valores
como texto e colunas em excesso. Nessa forma, eles não servem para decidir nada.

Este projeto transforma esses arquivos em informação confiável, para responder
perguntas como: quais órgãos mais gastam, quanto custa cada tipo de pagamento,
qual meio de transporte é mais usado e quais destinos custam mais.

A fonte é o recorte de **6 meses de 2025** da base de Viagens a Serviço,
fornecido em um arquivo `.zip` no Google Drive do curso.

## Tecnologias e técnicas

| Tecnologia | Uso |
|---|---|
| Python | scripts de extração e transformação |
| PostgreSQL | banco de dados das três camadas |
| psycopg 3 | conexão com o banco e carga em lote |
| pandas | leitura dos CSVs em blocos e consultas no notebook |
| SQLAlchemy | conexão do notebook com o banco |
| matplotlib | gráficos |
| gdown | download do `.zip` do Google Drive |
| python-dotenv | leitura das credenciais do arquivo `.env` |
| Jupyter | notebook da análise (camada Gold) |

Técnicas: arquitetura Medallion, carga em blocos, carga idempotente
(`TRUNCATE` antes de carregar), tratamento de exceções (`try/except`), integridade
referencial (PK, FK e constraints), conversão de tipos por funções específicas,
agregação com `JOIN` + `GROUP BY` e criação de tabelas e views Gold.

## Arquitetura

```mermaid
flowchart LR
    A[Google Drive: viagens.zip] --> B[1_extrair.py]
    B --> C[Raw: 4 tabelas raw_*]
    C --> D[2_transformar.py]
    D --> E[Silver: 4 tabelas silver_*]
    E --> F[3_analise.ipynb]
    F --> G[Gold: 3 tabelas gold_* e 3 views vw_gold_*]
```

| Camada | O que contém | Onde fica |
|---|---|---|
| Raw | Cópia fiel dos CSVs. Todas as colunas são `VARCHAR`, sem constraints. | `raw_viagem`, `raw_pagamento`, `raw_passagem`, `raw_trecho` |
| Silver | Dados limpos e tipados (`DECIMAL`, `DATE`, `INT`), com PK, FK e constraints. | `silver_viagem`, `silver_pagamento`, `silver_passagem`, `silver_trecho` |
| Gold | Agregações de negócio, criadas com `JOIN` + `GROUP BY`, como tabela e como view. | `gold_orgao_custo`, `gold_pagamento`, `gold_destino` e as views `vw_gold_*` |

## Estrutura do repositório

```
.
├── .env.example          modelo das credenciais (copie para .env)
├── .gitignore            ignora .env, .zip, .csv, data/ e arquivos locais
├── README.md
├── requirements.txt      dependências do projeto
├── config.py             parâmetros do projeto e leitura do .env
├── banco.py              conexão e funções utilitárias (conectar, executar, inserir_em_lote)
├── 0_criar_banco.sql     criação do database e das 8 tabelas (gerado pelo 1_extrair.py)
├── 1_extrair.py          download, leitura dos CSVs e carga na camada Raw
├── 2_transformar.py      limpeza e tipagem (Raw para Silver) e colunas calculadas
└── 3_analise.ipynb       camada Gold, perguntas de negócio e gráficos
```

A pasta `data/` (o `.zip` e os CSVs) e o arquivo `.env` existem só na máquina de
quem executa e não são versionados.

## Como executar

**Pré-requisitos:** Python 3.9 ou superior e PostgreSQL 10 ou superior em
execução, com um usuário que tenha permissão para criar databases.

1. Clone o repositório e entre na pasta do projeto.

2. Crie o ambiente virtual e instale as dependências:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Crie o arquivo de credenciais a partir do modelo e preencha com os dados do
   seu PostgreSQL:

   ```bash
   cp .env.example .env
   ```

   O `DRIVE_FILE_ID` do arquivo de dados já está configurado em `config.py`.

4. Execute o pipeline, nesta ordem:

   ```bash
   python 1_extrair.py        # baixa o zip (cerca de 68 MB), cria o banco e carrega a Raw
   python 2_transformar.py    # Raw -> Silver
   jupyter notebook 3_analise.ipynb   # Gold, perguntas e gráficos
   ```

O `1_extrair.py` cria o database e as 8 tabelas, e também grava esse mesmo script
em `0_criar_banco.sql`. Para recriar a estrutura manualmente, use
`psql -U <usuario> -f 0_criar_banco.sql`.

Os scripts podem ser executados várias vezes sem duplicar dados: as tabelas Raw e
Silver são esvaziadas (`TRUNCATE`) antes de cada carga, e as tabelas Gold são
recriadas pelo notebook.

## Modelo da camada Silver

`silver_viagem` é a tabela principal. As outras três se ligam a ela pela chave
estrangeira `id_viagem` (uma viagem tem vários pagamentos, passagens e trechos).

| Tabela | Constraint 1 | Constraint 2 |
|---|---|---|
| `silver_viagem` | `NOT NULL` em `nome_orgao_superior` | `CHECK` em `valor_diarias >= 0` |
| `silver_pagamento` | `CHECK` em `valor >= 0` | `NOT NULL` em `tipo_pagamento` |
| `silver_passagem` | `CHECK` em `valor_passagem >= 0` | `CHECK` em `taxa_servico >= 0` |
| `silver_trecho` | `CHECK` em `numero_diarias >= 0` | `UNIQUE` em `(id_viagem, sequencia_trecho)` |

Todas as tabelas têm chave primária e as constraints são declaradas dentro do
`CREATE TABLE`. As colunas da Raw vêm do cabeçalho de cada CSV, com os nomes sem
acento e em minúsculas, e a Raw guarda o arquivo inteiro, inclusive colunas que a
Silver não usa (como o CPF do viajante e os dados de volta da passagem).

## Regras de tratamento de dados (Raw para Silver)

- **Valores em reais:** texto com vírgula decimal (`1272,97`) vira `DECIMAL`. Vazio ou
  inválido vira `NULL`.
- **Datas:** `DD/MM/AAAA` vira `DATE`. Vazio ou inválido vira `NULL`.
- **Textos:** espaços das pontas são removidos, texto vazio vira `NULL` e o conteúdo é
  cortado no tamanho da coluna definido no dicionário de dados.
- **Colunas calculadas:**
  - `valor_total = valor_diarias + valor_passagens + valor_outros_gastos - valor_devolucao`
  - `duracao_dias = data_fim - data_inicio`, em dias (sem somar 1).
- **Linhas descartadas**, porque a Silver não as aceitaria: `id_viagem` vazio;
  `nome_orgao_superior` ou `tipo_pagamento` vazios; valores negativos nos campos com
  `CHECK`; viagens com `id_viagem` repetido (fica a primeira); linhas filhas cujo
  `id_viagem` não existe na viagem (a FK recusaria); trechos com o par
  `(id_viagem, sequencia_trecho)` repetido.

Ao final de cada tabela, o `2_transformar.py` imprime quantas linhas foram
carregadas e quantas foram descartadas.

## Camada Gold

Criada no `3_analise.ipynb`. Cada agregação existe como **tabela** (`gold_*`) e como
**view** (`vw_gold_*`) com a mesma consulta.

| Gold | Agregação |
|---|---|
| `gold_orgao_custo` | por órgão superior: quantidade de viagens, custo total, custo médio e total pago. Junta `silver_viagem` com os pagamentos já somados por viagem, para o custo não se multiplicar. |
| `gold_pagamento` | por órgão pagador, tipo de pagamento e mês: quantidade e valor total. Junta `silver_pagamento` com `silver_viagem`. |
| `gold_destino` | por destino (cidade e UF): quantidade de viagens e custo médio. Junta `silver_trecho` com `silver_viagem`, contando cada viagem uma vez por destino. |

## Perguntas de negócio e resultados

Os gráficos de cada pergunta estão no `3_analise.ipynb`, que já está salvo com os
resultados e pode ser lido direto no GitHub.

As perguntas 3, 5 e 6 foram respondidas com consultas na Silver. As perguntas 1, 2,
4 e 7 usam a Gold.

### 1. Os 5 órgãos com maior custo total

| Órgão superior | Viagens | Custo total (R$) |
|---|---:|---:|
| Ministério da Justiça e Segurança Pública | 75.742 | 486.933.121,65 |
| Ministério da Defesa | 61.912 | 156.070.304,49 |
| Ministério da Educação | 65.295 | 111.291.349,34 |
| Ministério do Meio Ambiente e Mudança do Clima | 19.413 | 49.697.710,16 |
| Ministério da Previdência Social | 8.190 | 40.417.309,06 |

O Ministério da Justiça e Segurança Pública tem o maior custo: 3,1 vezes o da Defesa
e 57,7% do total dos cinco órgãos juntos (R$ 844,4 milhões). O custo médio por
viagem nesse ministério é de R$ 6.428,84.

### 2. Os 3 destinos com maior custo médio por viagem

Considerados só destinos com pelo menos 5 viagens.

| Destino | Viagens | Custo médio (R$) |
|---|---:|---:|
| Monte Negro / Rondônia | 98 | 84.926,03 |
| Novo Santo Antônio / Mato Grosso | 24 | 79.266,08 |
| Sananduva / Rio Grande do Sul | 103 | 78.792,23 |

Esses valores são muito maiores que a média por viagem do órgão que mais gasta. Veja
a seção de limitações: o método atribui o custo total de uma viagem a cada um dos seus
destinos, e viagens longas e caras podem inflar a média de destinos pequenos.

### 3. A viagem de maior duração e seu custo total

A viagem de maior duração (id `0000000000020699856`, Ministério da Previdência
Social) vai de 13/01/2025 a 31/01/2026: **383 dias**, com custo total de **R$ 0,00**.

Entre as 10 viagens mais longas, todas duram de 364 a 383 dias; 6 são do Ministério
da Justiça e Segurança Pública, 3 do Ministério da Educação e 1 da Previdência, e
4 delas têm custo registrado de R$ 0,00. A mais longa com custo é do Ministério da
Justiça: 378 dias e R$ 120.650,00. A de maior custo entre as 10 tem 364 dias e
R$ 216.729,36.

### 4. O tipo de pagamento com maior valor médio

| Tipo de pagamento | Pagamentos | Valor médio (R$) |
|---|---:|---:|
| DIÁRIAS | 401.463 | 2.078,28 |
| PASSAGEM | 188.985 | 1.878,34 |
| Serviço correlato: seguro | 4.894 | 447,51 |
| RESTITUIÇÃO | 11.574 | 245,70 |

Diárias têm o maior valor médio, 1,11 vez o da passagem, e também o maior volume de
pagamentos.

### 5. O meio de transporte mais usado nos trechos

| Meio de transporte | Trechos | Participação |
|---|---:|---:|
| Veículo Oficial | 386.424 | 50,62% |
| Aéreo | 232.666 | 30,48% |
| Rodoviário | 64.970 | 8,51% |
| Veículo Próprio | 42.846 | 5,61% |
| Inválido | 26.659 | 3,49% |
| Fluvial | 8.429 | 1,10% |
| Ferroviário | 874 | 0,11% |
| Marítimo | 481 | 0,06% |

O veículo oficial é o mais usado (mais da metade dos 763.349 trechos com meio de
transporte informado). Junto com o transporte aéreo, ele responde por 81,1% do total.

### 6. A UF de destino que aparece em mais trechos

| UF de destino | Trechos |
|---|---:|
| São Paulo | 82.722 |
| Distrito Federal | 79.962 |
| Minas Gerais | 50.965 |
| Rio de Janeiro | 44.197 |
| Paraná | 42.603 |
| Pará | 40.044 |
| Rio Grande do Sul | 38.684 |
| Mato Grosso do Sul | 30.516 |
| Bahia | 28.375 |
| Pernambuco | 28.372 |

São Paulo é o destino mais frequente, seguido de perto pelo Distrito Federal. Como
os trechos incluem os deslocamentos de volta, parte desses números pode refletir
retornos a Brasília.

### 7. O órgão que pagou mais no total

| Órgão pagador | Total pago (R$) |
|---|---:|
| Fundo Nacional de Segurança Pública | 278.481.047,89 |
| Sigiloso | 200.484.801,68 |
| Comando da Aeronáutica | 81.769.144,77 |
| Instituto Nacional do Seguro Social | 37.427.601,45 |
| Comando do Exército | 36.872.643,95 |

O Fundo Nacional de Segurança Pública é o órgão que mais pagou.

## Conclusões e insights

- **O gasto é concentrado.** Um único ministério (Justiça e Segurança Pública) responde
  por mais da metade do custo dos cinco maiores órgãos.
- **O pagador mais relevante não é identificável.** Os pagamentos classificados como
  "Sigiloso" somam R$ 200,5 milhões e ficam em segundo lugar. Junto com o Fundo
  Nacional de Segurança Pública, somam R$ 479,0 milhões, ou 75,4% do total dos cinco
  maiores pagadores. Essa soma tem a mesma ordem de grandeza do custo do Ministério da
  Justiça (R$ 486,9 milhões), o que sugere, mas não comprova, que boa parte das viagens
  desse ministério é paga por essas duas fontes. O projeto não cruza órgão superior
  com órgão pagador, então isso é só uma hipótese para investigar.
- **Diárias e passagens dominam os pagamentos**, e a diária tem o maior valor médio.
- **O deslocamento é majoritariamente terrestre e oficial**, com o transporte aéreo em
  segundo lugar.
- **Há viagens de quase um ano com custo zero registrado.** Quatro das dez viagens mais
  longas têm `valor_total` igual a R$ 0,00, incluindo a mais longa. O projeto não
  investiga o motivo, mas é um ponto a verificar na fonte.

## Limitações

- **Período:** os dados cobrem seis meses de 2025, conforme o arquivo fornecido. Algumas
  viagens terminam em 2026.
- **Fórmulas:** o dicionário de dados não define o `valor_total` nem o `duracao_dias`.
  Foram adotadas as fórmulas descritas acima.
- **Destinos (pergunta 2):** o custo total de uma viagem é atribuído a cada destino dos
  seus trechos, inclusive o de volta, e só entram destinos com pelo menos 5 viagens.
- **Categoria "Inválido":** aparece como meio de transporte em 26.659 trechos (3,5%) e
  foi mantida, sem filtro. Ela não muda a resposta da pergunta 5.
- **UF de destino:** na base, a coluna traz o nome do estado por extenso, e não a sigla.
- **Linhas descartadas na Silver** não são guardadas em nenhuma tabela, só contadas.
- **Textos** são cortados no tamanho definido no dicionário de dados.

## Melhorias possíveis

- Guardar as linhas rejeitadas numa tabela de quarentena, com o motivo da rejeição.
- Investigar e tratar as viagens longas com custo zero e a categoria "Inválido".
- Calcular o destino de uma viagem de forma mais precisa (por exemplo, desconsiderando o
  trecho de volta) e ratear o custo entre os destinos.
- Cruzar órgão superior e órgão pagador na Gold.
- Criar índices nas colunas de junção para acelerar as consultas.
- Carregar a Raw com `COPY`, que é bem mais rápido que inserções em lote.
- Receber o período como parâmetro e permitir cargas incrementais.
- Subir o PostgreSQL com Docker Compose, para a execução ficar reproduzível.
- Adicionar testes automatizados das funções de conversão.