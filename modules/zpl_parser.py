# -*- coding: utf-8 -*-
"""Extrae nombre, precio y codigo de una etiqueta en ZPL o EPL2.

El reporte de Odoo asume una etiqueta mucho mas ancha que el rollo real, asi
que no se imprime tal cual: se extraen los datos y se reconstruye la etiqueta
con la calibracion propia. El lenguaje del archivo de entrada es independiente
del que se use para imprimir.
"""

import re

COMANDOS_BARCODE = ("^BC", "^BE", "^BU", "^B8", "^B3")


class ParseError(Exception):
    """El texto no tiene la forma esperada de un ZPL de Odoo."""


def limpiar_nombre(nombre):
    """Saca el prefijo [CODIGO] y el sufijo (NNNNNN) que agrega Odoo.

    Conserva los parentesis con texto, como (CV), que son parte del nombre.
    """
    nombre = re.sub(r"^\s*\[[^\]]*\]\s*", "", nombre)
    nombre = re.sub(r"\s*\([\d/A-Z]*\d[\d/A-Z]*\)\s*$", "", nombre)
    return nombre.strip()


def _campos(texto):
    """Devuelve la lista de (posicion, contenido) de cada ^FD...^FS."""
    return [(m.start(), m.group(1)) for m in re.finditer(r"\^FD(.*?)\^FS", texto, re.S)]


def detectar_lenguaje(texto):
    """Devuelve "zpl" o "epl" segun los comandos que aparezcan."""
    if "^XA" in texto or "^FD" in texto:
        return "zpl"
    return "epl"


def _parsear_epl(texto):
    """Extrae los datos de una etiqueta EPL2."""
    codigo = None
    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.startswith("B"):
            comillas = re.findall(r'"([^"]*)"', limpia)
            if comillas:
                codigo = comillas[-1].strip()
                break
    if not codigo:
        raise ParseError("el archivo EPL no tiene ningun comando de codigo de barras")

    textos = []
    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.startswith("A"):
            comillas = re.findall(r'"([^"]*)"', limpia)
            if comillas:
                textos.append(comillas[-1].strip())

    precio = next((t for t in textos if t.startswith("$")), None)
    nombre = next(
        (limpiar_nombre(t) for t in textos if t and t != codigo and not t.startswith("$")),
        "",
    )
    return {"nombre": nombre, "precio": precio, "codigo": codigo}


def parsear(texto):
    """Devuelve {"nombre", "precio", "codigo"} a partir de un ZPL o un EPL."""
    if detectar_lenguaje(texto) == "epl":
        return _parsear_epl(texto)

    campos = _campos(texto)
    if not campos:
        raise ParseError("el archivo no tiene campos ^FD...^FS")

    posicion_barcode = -1
    for comando in COMANDOS_BARCODE:
        indice = texto.find(comando)
        if indice != -1 and (posicion_barcode == -1 or indice < posicion_barcode):
            posicion_barcode = indice
    if posicion_barcode == -1:
        raise ParseError("el archivo no tiene ningun comando de codigo de barras")

    codigo = None
    for posicion, contenido in campos:
        if posicion > posicion_barcode:
            codigo = contenido.strip()
            break
    if not codigo:
        raise ParseError("no se encontro el codigo despues del comando de barras")

    precio = None
    for _, contenido in campos:
        if contenido.strip().startswith("$"):
            precio = contenido.strip()
            break

    nombre = ""
    for posicion, contenido in campos:
        texto_campo = contenido.strip()
        if texto_campo and texto_campo != codigo and not texto_campo.startswith("$"):
            nombre = limpiar_nombre(texto_campo)
            break

    return {"nombre": nombre, "precio": precio, "codigo": codigo}
