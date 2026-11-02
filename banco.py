"""Conexão com o PostgreSQL e funções utilitárias."""
import psycopg

import config


def conectar(usar_database=True, autocommit=False):
    """Abre uma conexão com o PostgreSQL.

    Use usar_database=False (com autocommit=True) para rodar o
    CREATE DATABASE, quando o banco do projeto ainda não existe.
    """
    nome_banco = config.DB_NAME if usar_database else config.DB_ADMIN
    return psycopg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        dbname=nome_banco,
        autocommit=autocommit,
    )


def executar(sql, params=None):
    """Executa um comando SQL (CREATE, TRUNCATE, INSERT, etc.)."""
    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            cursor.execute(sql, params)
        conexao.commit()
    finally:
        conexao.close()


def inserir_em_lote(tabela, colunas, linhas):
    """Insere várias linhas de uma vez numa tabela.

    colunas: lista de nomes das colunas.
    linhas: lista de tuplas com os valores.
    """
    if not linhas:
        return
    campos = ", ".join(f'"{c}"' for c in colunas)
    marcadores = ", ".join(["%s"] * len(colunas))
    sql = f"INSERT INTO {tabela} ({campos}) VALUES ({marcadores})"

    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            cursor.executemany(sql, linhas)
        conexao.commit()
    finally:
        conexao.close()