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

RAW_PAGAMENTO = [
    "identificador_do_processo_de_viagem", "numero_da_proposta_pcdp",
    "nome_do_orgao_pagador", "nome_da_unidade_gestora_pagadora",
    "tipo_de_pagamento", "valor",
]
SILVER_PAGAMENTO = [
    "id_viagem", "num_proposta", "nome_orgao_pagador", "nome_ug_pagadora",
    "tipo_pagamento", "valor",
]

RAW_PASSAGEM = [
    "identificador_do_processo_de_viagem", "meio_de_transporte",
    "pais_origem_ida", "uf_origem_ida", "cidade_origem_ida",
    "pais_destino_ida", "uf_destino_ida", "cidade_destino_ida",
    "valor_da_passagem", "taxa_de_servico", "data_da_emissao_compra",
]
SILVER_PASSAGEM = [
    "id_viagem", "meio_transporte", "pais_origem_ida", "uf_origem_ida",
    "cidade_origem_ida", "pais_destino_ida", "uf_destino_ida",
    "cidade_destino_ida", "valor_passagem", "taxa_servico", "data_emissao",
]

RAW_TRECHO = [
    "identificador_do_processo_de_viagem", "sequencia_trecho", "origem_data",
    "origem_uf", "origem_cidade", "destino_data", "destino_uf",
    "destino_cidade", "meio_de_transporte", "numero_diarias",
]
SILVER_TRECHO = [
    "id_viagem", "sequencia_trecho", "origem_data", "origem_uf",
    "origem_cidade", "destino_data", "destino_uf", "destino_cidade",
    "meio_transporte", "numero_diarias",
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

def converter_inteiro(valor):
    """Converte texto em int. Vazio ou inválido vira None."""
    try:
        return int(str(valor).strip())
    except ValueError:
        return None


def transformar_pagamento(linha):
    id_viagem, num_proposta, orgao, ug, tipo, valor = linha
    id_viagem = limpar_texto(id_viagem, 20)
    tipo = limpar_texto(tipo, 50)
    valor = converter_decimal(valor)

    if id_viagem is None or tipo is None:
        return None
    if valor is not None and valor < 0:
        return None
    return (
        id_viagem, limpar_texto(num_proposta, 20), limpar_texto(orgao, 255),
        limpar_texto(ug, 255), tipo, valor,
    )


def transformar_passagem(linha):
    (id_viagem, meio, pais_o, uf_o, cidade_o, pais_d, uf_d, cidade_d,
     valor, taxa, emissao) = linha
    id_viagem = limpar_texto(id_viagem, 20)
    valor = converter_decimal(valor)
    taxa = converter_decimal(taxa)

    if id_viagem is None:
        return None
    if (valor is not None and valor < 0) or (taxa is not None and taxa < 0):
        return None
    return (
        id_viagem, limpar_texto(meio, 50), limpar_texto(pais_o, 60),
        limpar_texto(uf_o, 40), limpar_texto(cidade_o, 80),
        limpar_texto(pais_d, 60), limpar_texto(uf_d, 40),
        limpar_texto(cidade_d, 80), valor, taxa, converter_data(emissao),
    )


def transformar_trecho(linha):
    (id_viagem, sequencia, data_o, uf_o, cidade_o, data_d, uf_d, cidade_d,
     meio, diarias) = linha
    id_viagem = limpar_texto(id_viagem, 20)
    diarias = converter_decimal(diarias)

    if id_viagem is None:
        return None
    if diarias is not None and diarias < 0:
        return None
    return (
        id_viagem, converter_inteiro(sequencia), converter_data(data_o),
        limpar_texto(uf_o, 40), limpar_texto(cidade_o, 80),
        converter_data(data_d), limpar_texto(uf_d, 40),
        limpar_texto(cidade_d, 80), limpar_texto(meio, 50), diarias,
    )


def carregar_filha(tabela_raw, tabela_silver, colunas_raw, colunas_silver,
                   transformar, ids_viagem, indices_unicos=None):
    """Carrega uma tabela filha, respeitando a FK e a UNIQUE da Silver."""
    consulta = montar_consulta(colunas_raw, tabela_raw)
    vistos = set()
    total = descartadas = 0
    for bloco in ler_em_blocos(consulta):
        linhas = []
        for linha in bloco:
            nova = transformar(linha)
            if nova is None or nova[0] not in ids_viagem:
                descartadas += 1
                continue
            if indices_unicos:
                chave = tuple(nova[i] for i in indices_unicos)
                if None not in chave:
                    if chave in vistos:
                        descartadas += 1
                        continue
                    vistos.add(chave)
            linhas.append(nova)
        banco.inserir_em_lote(tabela_silver, colunas_silver, linhas)
        total += len(linhas)
    print(f"{tabela_silver}: {total} linhas carregadas, {descartadas} descartadas")

def main():
    banco.executar(TRUNCATE_SILVER)
    ids_viagem = carregar_viagem()
    carregar_filha("raw_pagamento", "silver_pagamento", RAW_PAGAMENTO,
                   SILVER_PAGAMENTO, transformar_pagamento, ids_viagem)
    carregar_filha("raw_passagem", "silver_passagem", RAW_PASSAGEM,
                   SILVER_PASSAGEM, transformar_passagem, ids_viagem)
    carregar_filha("raw_trecho", "silver_trecho", RAW_TRECHO,
                   SILVER_TRECHO, transformar_trecho, ids_viagem,
                   indices_unicos=(0, 1))


if __name__ == "__main__":
    main()


