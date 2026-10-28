"""Utilidades para números de identificación."""
import re


def normalize_id_number(value):
    """id_number sin guiones ni espacios, para comparar valores equivalentes."""
    return re.sub(r'[-\s]', '', value or '')
