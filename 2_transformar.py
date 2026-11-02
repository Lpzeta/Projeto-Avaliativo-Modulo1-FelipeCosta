"""Fase 2: copia a camada Raw para a Silver, convertendo os tipos."""
from decimal import Decimal, InvalidOperation

from datetime import datetime


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


