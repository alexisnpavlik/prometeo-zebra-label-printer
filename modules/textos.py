# -*- coding: utf-8 -*-
"""Ajusta nombre y precio al ancho de la columna, como hacia la app vieja.

zebra_label_printer_odoo imprime el nombre en una sola linea recortada y el
precio sin centavos en cero, para que entre grande. Aca se hace lo mismo, pero
midiendo el ancho real del texto en vez de cortar siempre en 20 caracteres.
"""

import math

# Avance por caracter de ^A0N,20,10 en dots, medido renderizando el texto en
# Labelary y redondeado hacia arriba: sobreestimar solo acorta el nombre, pero
# subestimar hace que ^FB lo parta y la segunda linea se imprima encima.
_ANGOSTOS_A0 = set(" .,;:!'|()/Iil")
_ANCHOS_A0 = set("WMmw-%+@=")
_ANCHO_ANGOSTO_A0 = 3
_ANCHO_ANCHO_A0 = 9
_ANCHO_COMUN_A0 = 6.5


def ancho_a0_nombre(caracter):
    """Dots que ocupa un caracter en ^A0N,20,10, la fuente del nombre en ZPL."""
    if caracter in _ANGOSTOS_A0:
        return _ANCHO_ANGOSTO_A0
    if caracter in _ANCHOS_A0:
        return _ANCHO_ANCHO_A0
    return _ANCHO_COMUN_A0


def ancho_a0(ancho_fuente):
    """Ancho por caracter de ^A0N con ancho `ancho_fuente`, escalado desde 10.

    Se redondea hacia arriba por caracter: el firmware dibuja cada glifo en
    dots enteros y sobreestimar solo acorta el texto, mientras que subestimar
    hace que ^FB lo parta y la segunda linea se imprima encima.
    """
    escala = ancho_fuente / 10
    return lambda caracter: math.ceil(ancho_a0_nombre(caracter) * escala)


def ancho(texto, ancho_de):
    """Ancho total de `texto`, con `ancho_de(caracter)` dando el de cada uno."""
    return sum(ancho_de(caracter) for caracter in texto)


def recortar(texto, ancho_max, ancho_de):
    """Corta `texto` y le agrega un punto hasta que entre en `ancho_max` dots."""
    if ancho(texto, ancho_de) <= ancho_max:
        return texto
    for largo in range(len(texto) - 1, 0, -1):
        recortado = texto[:largo].rstrip() + "."
        if ancho(recortado, ancho_de) <= ancho_max:
            return recortado
    return ""


def partir_en_lineas(texto, ancho_max, ancho_de, cantidad):
    """Reparte `texto` en hasta `cantidad` lineas cortando entre palabras.

    Una palabra que no entra sola en una linea se corta donde caiga. Lo que
    sobra despues de la ultima linea se recorta con punto, igual que `recortar`.
    """
    lineas = []
    resto = texto.strip()
    while resto and len(lineas) < cantidad - 1:
        if ancho(resto, ancho_de) <= ancho_max:
            break
        largo = len(resto)
        while largo > 0 and ancho(resto[:largo], ancho_de) > ancho_max:
            largo -= 1
        corte = resto.rfind(" ", 0, largo + 1)
        if corte <= 0:
            corte = largo
        lineas.append(resto[:corte].rstrip())
        resto = resto[corte:].strip()
    if resto:
        lineas.append(recortar(resto, ancho_max, ancho_de))
    return lineas


def precio_corto(precio):
    """Quita los centavos en cero para que el precio entre en la fuente grande."""
    precio = precio.strip()
    for centavos in (",00", ".00"):
        if precio.endswith(centavos):
            return precio[: -len(centavos)]
    return precio
