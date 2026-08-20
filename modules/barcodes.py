# -*- coding: utf-8 -*-
"""Elige la simbologia de codigo de barras y el ancho de modulo.

En ZPL ^BC es Code 128, NO EAN-13. Usar ^BC para un EAN de 13 digitos da un
codigo de ~246 dots que no entra en una etiqueta de 212 y ademas no lee como
codigo de producto. Este modulo elige el comando correcto segun el codigo.
"""

import math

ANCHO_MAX_DEFECTO = 190


def verificador(datos):
    """Calcula el digito verificador EAN/UPC con pesos 1-3 desde la derecha."""
    digitos = [int(c) for c in datos][::-1]
    suma = sum(v * (3 if i % 2 == 0 else 1) for i, v in enumerate(digitos))
    return str((10 - suma % 10) % 10)


def modulos_code128(codigo):
    """Devuelve cuantos modulos ocupa el codigo en Code 128.

    Subset C si es todo digitos y de largo par (dos digitos por simbolo).
    """
    if codigo.isdigit() and len(codigo) % 2 == 0:
        simbolos = len(codigo) / 2
    else:
        simbolos = len(codigo)
    return 11 * (1 + math.ceil(simbolos) + 1) + 13


def elegir_barcode(codigo, ancho_max=ANCHO_MAX_DEFECTO):
    """Devuelve (comando_zpl, modulo) para que el codigo entre en ancho_max.

    Usa EAN/UPC solo si el largo y el verificador son validos; si no, Code 128,
    que acepta cualquier largo y contenido alfanumerico.
    """
    codigo = str(codigo).strip()
    if not codigo:
        raise ValueError("el codigo esta vacio")

    if codigo.isdigit():
        if len(codigo) == 13 and codigo[12] == verificador(codigo[:12]):
            return "^BEN", 2
        if len(codigo) == 12 and codigo[11] == verificador(codigo[:11]):
            return "^BUN", 2
        if len(codigo) == 8 and codigo[7] == verificador(codigo[:7]):
            return "^B8N", 2

    modulos = modulos_code128(codigo)
    for modulo in (3, 2, 1):
        if modulos * modulo <= ancho_max:
            return "^BCN", modulo
    raise ValueError(
        "{!r} necesita {} modulos y no entra en {} dots ni con modulo 1. "
        "Usa un codigo mas corto o un rollo mas ancho.".format(
            codigo, modulos, ancho_max
        )
    )
