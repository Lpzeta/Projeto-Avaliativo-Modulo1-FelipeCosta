-- Execute com: psql -U postgres -f 0_criar_banco.sql
CREATE DATABASE viagens;
\c viagens

CREATE TABLE IF NOT EXISTS raw_viagem (
    "identificador_do_processo_de_viagem" VARCHAR(4000),
    "numero_da_proposta_pcdp" VARCHAR(4000),
    "situacao" VARCHAR(4000),
    "viagem_urgente" VARCHAR(4000),
    "justificativa_urgencia_viagem" VARCHAR(4000),
    "codigo_do_orgao_superior" VARCHAR(4000),
    "nome_do_orgao_superior" VARCHAR(4000),
    "codigo_orgao_solicitante" VARCHAR(4000),
    "nome_orgao_solicitante" VARCHAR(4000),
    "cpf_viajante" VARCHAR(4000),
    "nome" VARCHAR(4000),
    "cargo" VARCHAR(4000),
    "funcao" VARCHAR(4000),
    "descricao_funcao" VARCHAR(4000),
    "periodo_data_de_inicio" VARCHAR(4000),
    "periodo_data_de_fim" VARCHAR(4000),
    "destinos" VARCHAR(4000),
    "motivo" VARCHAR(4000),
    "valor_diarias" VARCHAR(4000),
    "valor_passagens" VARCHAR(4000),
    "valor_devolucao" VARCHAR(4000),
    "valor_outros_gastos" VARCHAR(4000)
);

CREATE TABLE IF NOT EXISTS raw_pagamento (
    "identificador_do_processo_de_viagem" VARCHAR(4000),
    "numero_da_proposta_pcdp" VARCHAR(4000),
    "codigo_do_orgao_superior" VARCHAR(4000),
    "nome_do_orgao_superior" VARCHAR(4000),
    "codigo_do_orgao_pagador" VARCHAR(4000),
    "nome_do_orgao_pagador" VARCHAR(4000),
    "codigo_da_unidade_gestora_pagadora" VARCHAR(4000),
    "nome_da_unidade_gestora_pagadora" VARCHAR(4000),
    "tipo_de_pagamento" VARCHAR(4000),
    "valor" VARCHAR(4000)
);

CREATE TABLE IF NOT EXISTS raw_passagem (
    "identificador_do_processo_de_viagem" VARCHAR(4000),
    "numero_da_proposta_pcdp" VARCHAR(4000),
    "meio_de_transporte" VARCHAR(4000),
    "pais_origem_ida" VARCHAR(4000),
    "uf_origem_ida" VARCHAR(4000),
    "cidade_origem_ida" VARCHAR(4000),
    "pais_destino_ida" VARCHAR(4000),
    "uf_destino_ida" VARCHAR(4000),
    "cidade_destino_ida" VARCHAR(4000),
    "pais_origem_volta" VARCHAR(4000),
    "uf_origem_volta" VARCHAR(4000),
    "cidade_origem_volta" VARCHAR(4000),
    "pais_destino_volta" VARCHAR(4000),
    "uf_destino_volta" VARCHAR(4000),
    "cidade_destino_volta" VARCHAR(4000),
    "valor_da_passagem" VARCHAR(4000),
    "taxa_de_servico" VARCHAR(4000),
    "data_da_emissao_compra" VARCHAR(4000),
    "hora_da_emissao_compra" VARCHAR(4000)
);

CREATE TABLE IF NOT EXISTS raw_trecho (
    "identificador_do_processo_de_viagem" VARCHAR(4000),
    "numero_da_proposta_pcdp" VARCHAR(4000),
    "sequencia_trecho" VARCHAR(4000),
    "origem_data" VARCHAR(4000),
    "origem_pais" VARCHAR(4000),
    "origem_uf" VARCHAR(4000),
    "origem_cidade" VARCHAR(4000),
    "destino_data" VARCHAR(4000),
    "destino_pais" VARCHAR(4000),
    "destino_uf" VARCHAR(4000),
    "destino_cidade" VARCHAR(4000),
    "meio_de_transporte" VARCHAR(4000),
    "numero_diarias" VARCHAR(4000),
    "missao" VARCHAR(4000)
);

CREATE TABLE IF NOT EXISTS silver_viagem (
    id_viagem VARCHAR(20) NOT NULL,
    num_proposta VARCHAR(20),
    situacao VARCHAR(50),
    viagem_urgente VARCHAR(5),
    cod_orgao_superior VARCHAR(20),
    nome_orgao_superior VARCHAR(255) NOT NULL,
    nome_viajante VARCHAR(255),
    cargo VARCHAR(255),
    data_inicio DATE,
    data_fim DATE,
    destinos VARCHAR(4000),
    motivo VARCHAR(4000),
    valor_diarias DECIMAL(10,2),
    valor_passagens DECIMAL(10,2),
    valor_devolucao DECIMAL(10,2),
    valor_outros_gastos DECIMAL(10,2),
    valor_total DECIMAL(12,2),
    duracao_dias INT,
    PRIMARY KEY (id_viagem),
    CONSTRAINT chk_viagem_diarias CHECK (valor_diarias >= 0)
);

CREATE TABLE IF NOT EXISTS silver_passagem (
    id_passagem INT GENERATED ALWAYS AS IDENTITY,
    id_viagem VARCHAR(20) NOT NULL,
    meio_transporte VARCHAR(50),
    pais_origem_ida VARCHAR(60),
    uf_origem_ida VARCHAR(40),
    cidade_origem_ida VARCHAR(80),
    pais_destino_ida VARCHAR(60),
    uf_destino_ida VARCHAR(40),
    cidade_destino_ida VARCHAR(80),
    valor_passagem DECIMAL(10,2),
    taxa_servico DECIMAL(10,2),
    data_emissao DATE,
    PRIMARY KEY (id_passagem),
    CONSTRAINT fk_passagem_viagem FOREIGN KEY (id_viagem)
        REFERENCES silver_viagem (id_viagem),
    CONSTRAINT chk_passagem_valor CHECK (valor_passagem >= 0),
    CONSTRAINT chk_passagem_taxa CHECK (taxa_servico >= 0)
);

CREATE TABLE IF NOT EXISTS silver_pagamento (
    id_pagamento INT GENERATED ALWAYS AS IDENTITY,
    id_viagem VARCHAR(20) NOT NULL,
    num_proposta VARCHAR(20),
    nome_orgao_pagador VARCHAR(255),
    nome_ug_pagadora VARCHAR(255),
    tipo_pagamento VARCHAR(50) NOT NULL,
    valor DECIMAL(10,2),
    PRIMARY KEY (id_pagamento),
    CONSTRAINT fk_pagamento_viagem FOREIGN KEY (id_viagem)
        REFERENCES silver_viagem (id_viagem),
    CONSTRAINT chk_pagamento_valor CHECK (valor >= 0)
);

CREATE TABLE IF NOT EXISTS silver_trecho (
    id_trecho INT GENERATED ALWAYS AS IDENTITY,
    id_viagem VARCHAR(20) NOT NULL,
    sequencia_trecho INT,
    origem_data DATE,
    origem_uf VARCHAR(40),
    origem_cidade VARCHAR(80),
    destino_data DATE,
    destino_uf VARCHAR(40),
    destino_cidade VARCHAR(80),
    meio_transporte VARCHAR(50),
    numero_diarias DECIMAL(10,2),
    PRIMARY KEY (id_trecho),
    CONSTRAINT fk_trecho_viagem FOREIGN KEY (id_viagem)
        REFERENCES silver_viagem (id_viagem),
    CONSTRAINT chk_trecho_diarias CHECK (numero_diarias >= 0),
    CONSTRAINT uq_trecho_viagem_seq UNIQUE (id_viagem, sequencia_trecho)
);
