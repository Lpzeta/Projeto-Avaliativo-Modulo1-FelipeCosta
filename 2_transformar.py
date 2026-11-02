"""Fase 2: copia a camada Raw para a Silver, convertendo os tipos."""
from decimal import Decimal, InvalidOperation

from datetime import datetime

import banco
import config

TRUNCATE_SILVER = (
    "TRUNCATE TABLE silver_trecho, silver_passagem, "
    "silver_pagamento, silver_viagem RESTART IDENTITY"
)

RAW_VIAGEM = [
    "identificador_do_processo_de_viagem", "numero_da_proposta_pcdp",
    "situacao", "viagem_urgente", "codigo_do_orgao_superior",
    "nome_do_orgao_superior", "nome", "cargo", "periodo_data_de_inicio",
    "periodo_data_de_fim", "destinos", "motivo", "valor_diarias",
    "valor_passagens", "valor_devolucao", "valor_outros_gastos",
]

SILVER_VIAGEM = [
    "id_viagem", "num_proposta", "situacao", "viagem_urgente",
    "cod_orgao_superior", "nome_orgao_superior", "nome_viajante", "cargo",
    "data_inicio", "data_fim", "destinos", "motivo", "valor_diarias",
    "valor_passagens", "valor_devolucao", "valor_outros_gastos",
    "valor_total", "duracao_dias",
]


def converter_decimal(valor):
    """Converte texto com vírgula decimal ('1272,97') em Decimal.

    Texto vazio ou inválido vira None.
    """
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor == "":
        return None
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    try:
        return Decimal(valor)
    except InvalidOperation:
        return None


def converter_data(valor):
    """Converte texto 'DD/MM/AAAA' em date. Vazio ou inválido vira None."""
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor == "":
        return None
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except ValueError:
        return None

def limpar_texto(valor, tamanho=None):
    """Tira espaços das pontas. Vazio vira None e corta no tamanho da coluna."""
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor == "":
        return None
    return valor[:tamanho] if tamanho else valor


def montar_consulta(colunas, tabela):
    return f"SELECT {', '.join(colunas)} FROM {tabela}"


def ler_em_blocos(consulta):
    """Lê uma consulta em blocos, sem carregar a tabela inteira na memória."""
    conexao = banco.conectar()
    try:
        with conexao.cursor(name="leitura_raw") as cursor:
            cursor.execute(consulta)
            while True:
                bloco = cursor.fetchmany(config.CHUNK_SIZE)
                if not bloco:
                    break
                yield bloco
    finally:
        conexao.close()

def transformar_viagem(linha):
    """Converte uma linha da raw_viagem. Devolve None se for inválida."""
    (id_viagem, num_proposta, situacao, urgente, cod_orgao, nome_orgao, nome,
     cargo, inicio, fim, destinos, motivo, diarias, passagens, devolucao,
     outros) = linha

    id_viagem = limpar_texto(id_viagem, 20)
    nome_orgao = limpar_texto(nome_orgao, 255)
    diarias = converter_decimal(diarias)
    passagens = converter_decimal(passagens)
    devolucao = converter_decimal(devolucao)
    outros = converter_decimal(outros)
    inicio = converter_data(inicio)
    fim = converter_data(fim)

    # Linhas que violariam NOT NULL ou CHECK da Silver são descartadas
    if id_viagem is None or nome_orgao is None:
        return None
    if diarias is not None and diarias < 0:
        return None

    valor_total = (diarias or 0) + (passagens or 0) + (outros or 0) - (devolucao or 0)
    duracao_dias = (fim - inicio).days if inicio and fim else None

    return (
        id_viagem, limpar_texto(num_proposta, 20), limpar_texto(situacao, 50),
        limpar_texto(urgente, 5), limpar_texto(cod_orgao, 20), nome_orgao,
        limpar_texto(nome, 255), limpar_texto(cargo, 255), inicio, fim,
        limpar_texto(destinos, 4000), limpar_texto(motivo, 4000),
        diarias, passagens, devolucao, outros, valor_total, duracao_dias,
    )


def carregar_viagem():
    """Carrega silver_viagem e devolve o conjunto de ids carregados."""
    consulta = montar_consulta(RAW_VIAGEM, "raw_viagem")
    ids_vistos = set()
    total = descartadas = 0
    for bloco in ler_em_blocos(consulta):
        linhas = []
        for linha in bloco:
            nova = transformar_viagem(linha)
            if nova is None or nova[0] in ids_vistos:
                descartadas += 1
                continue
            ids_vistos.add(nova[0])
            linhas.append(nova)
        banco.inserir_em_lote("silver_viagem", SILVER_VIAGEM, linhas)
        total += len(linhas)
    print(f"silver_viagem: {total} linhas carregadas, {descartadas} descartadas")
    return ids_vistos


def main():
    banco.executar(TRUNCATE_SILVER)
    carregar_viagem()


if __name__ == "__main__":
    main()


