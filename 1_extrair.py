"""Fases 0 e 1: cria o banco e carrega a camada Raw."""
import re
import unicodedata
import zipfile

import gdown
import pandas as pd

import banco
import config

ARQUIVO_SQL = config.BASE_DIR / "0_criar_banco.sql"

DDL_SILVER = [
    """CREATE TABLE IF NOT EXISTS silver_viagem (
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
)""",
    """CREATE TABLE IF NOT EXISTS silver_passagem (
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
)""",
    """CREATE TABLE IF NOT EXISTS silver_pagamento (
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
)""",
    """CREATE TABLE IF NOT EXISTS silver_trecho (
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
)""",
]


def limpar_nome(nome):
    """Transforma o cabeçalho do CSV em nome de coluna: sem acento, minúsculo."""
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    nome = re.sub(r"[^a-zA-Z0-9]+", "_", nome).strip("_").lower()
    return nome[:60]


def baixar_zip():
    config.DATA_DIR.mkdir(exist_ok=True)
    gdown.download(id=config.DRIVE_FILE_ID, output=str(config.ZIP_PATH))


def extrair_zip():
    with zipfile.ZipFile(config.ZIP_PATH) as zip_file:
        zip_file.extractall(config.DATA_DIR)


def ler_colunas(arquivo):
    """Lê só o cabeçalho do CSV e devolve os nomes das colunas já limpos."""
    cabecalho = pd.read_csv(
        config.DATA_DIR / arquivo,
        sep=config.CSV_SEP,
        encoding=config.CSV_ENCODING,
        nrows=0,
    )
    return [limpar_nome(coluna) for coluna in cabecalho.columns]


TAMANHO_RAW = 4000


def ddl_raw(tabela, colunas):
    """Tabela Raw: todas as colunas VARCHAR, sem constraints."""
    campos = ",\n    ".join(f'"{c}" VARCHAR({TAMANHO_RAW})' for c in colunas)
    return f"CREATE TABLE IF NOT EXISTS {tabela} (\n    {campos}\n)"


def salvar_sql(comandos):
    """Grava os comandos no arquivo 0_criar_banco.sql (para rodar no psql)."""
    cabecalho = (
        f"-- Execute com: psql -U {config.DB_USER} -f 0_criar_banco.sql\n"
        f"CREATE DATABASE {config.DB_NAME};\n"
        f"\\c {config.DB_NAME}\n\n"
    )
    corpo = ";\n\n".join(comandos) + ";\n"
    ARQUIVO_SQL.write_text(cabecalho + corpo, encoding="utf-8")


def criar_database():
    """Cria o database se ainda não existir (PostgreSQL não tem IF NOT EXISTS)."""
    conexao = banco.conectar(usar_database=False, autocommit=True)
    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (config.DB_NAME,)
            )
            if cursor.fetchone() is None:
                cursor.execute(f"CREATE DATABASE {config.DB_NAME}")
    finally:
        conexao.close()


def criar_tabelas(comandos):
    for comando in comandos:
        banco.executar(comando)


def carregar_raw(arquivo, tabela, colunas):
    """Carrega o CSV em blocos, sem alterar o conteúdo."""
    banco.executar(f"TRUNCATE TABLE {tabela}")
    blocos = pd.read_csv(
        config.DATA_DIR / arquivo,
        sep=config.CSV_SEP,
        encoding=config.CSV_ENCODING,
        dtype=str,
        keep_default_na=False,
        chunksize=config.CHUNK_SIZE,
    )
    total = 0
    for bloco in blocos:
        linhas = list(bloco.itertuples(index=False, name=None))
        banco.inserir_em_lote(tabela, colunas, linhas)
        total += len(linhas)
    print(f"{tabela}: {total} linhas carregadas")


def main():
    try:
        baixar_zip()
        extrair_zip()

        colunas_raw = {
            tabela: ler_colunas(arquivo)
            for arquivo, tabela in config.ARQUIVOS_RAW.items()
        }
        comandos = [ddl_raw(t, cols) for t, cols in colunas_raw.items()]
        comandos += DDL_SILVER

        salvar_sql(comandos)
        criar_database()
        criar_tabelas(comandos)

        for arquivo, tabela in config.ARQUIVOS_RAW.items():
            carregar_raw(arquivo, tabela, colunas_raw[tabela])
    except Exception as erro:
        print(f"Erro na extração: {erro}")
        raise


if __name__ == "__main__":
    main()