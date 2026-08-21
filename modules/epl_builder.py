# -*- coding: utf-8 -*-
"""Arma la fila de 3 etiquetas en EPL2, para impresoras que no aceptan ZPL.

EPL2 no es un dialecto de ZPL: son comandos de una letra, uno por linea, sin ^.
El buffer se limpia con N y se imprime con P1. La oscuridad es absoluta (D0-D15),
no relativa como el ^MD de ZPL.
"""

import textwrap

from modules import barcodes

TIPOS_EPL = {
    "^BEN": "E30",  # EAN-13
    "^BUN": "UA0",  # UPC-A
    "^B8N": "E80",  # EAN-8
    "^BCN": "1",    # Code 128
}

GAP = 24          # separacion entre filas de etiquetas, en dots
FUENTE = "2"      # fuente EPL de tamano fijo
ANCHO_CARACTER_FUENTE_2 = 10  # dots por caracter, fuente 2 con multiplicador 1
ALTO_BARRAS = 40


def _escapar(texto):
    """Escapa comillas dobles dentro de campos de texto EPL2.

    Solo se escapa la comilla doble con \", que es el escape documentado por EPL2.
    La barra invertida no se toca: EPL2 no define \\ como escape. Pero una barra
    invertida al final del texto quedaria pegada a la comilla de cierre del
    campo, "escapandola" sin querer y dejando el string sin cerrar; se descarta.
    """
    texto = texto.replace('"', '\\"')
    if texto.endswith("\\"):
        texto = texto.rstrip("\\")
    return texto


def _oscuridad_epl(oscuridad_zpl):
    """Traduce el ^MD relativo de ZPL a la densidad absoluta D0-D15 de EPL.

    La fórmula 15 + oscuridad_zpl - 1 mapea el -6 de ZPL a D8, que es el valor
    calibrado para que las barras no engordan en esta impresora. El clamp
    mantiene el resultado en 0-15 para cualquier entrada.
    """
    return max(0, min(15, 15 + oscuridad_zpl - 1))


def _partir_nombre(nombre, ancho_util):
    """Envuelve el nombre en hasta 2 lineas que entren en ancho_util.

    EPL2 no tiene equivalente al ^FB de ZPL (envolvimiento automatico dentro
    de un bloque), asi que hay que partirlo a mano. La fuente 2 mide
    ANCHO_CARACTER_FUENTE_2 dots por caracter con multiplicador 1. Corta por
    palabras cuando se puede; lo que no entra en 2 lineas se descarta.
    """
    max_caracteres = max(1, ancho_util // ANCHO_CARACTER_FUENTE_2)
    lineas = textwrap.wrap(nombre, width=max_caracteres, break_long_words=True)
    return lineas[:2]


def _columna(x, nombre, precio, codigo, calibracion):
    """Devuelve las lineas EPL de una columna con offset horizontal x."""
    margen = calibracion["margen"]
    comando, modulo = barcodes.elegir_barcode(codigo, calibracion["util"])
    tipo = TIPOS_EPL[comando]

    lineas = [
        'A{},{},0,{},1,1,N,"{}"'.format(x + margen, y, FUENTE, _escapar(linea_nombre))
        for y, linea_nombre in zip((6, 24), _partir_nombre(nombre, calibracion["util"]))
    ]
    if precio:
        lineas.append(
            'A{},48,0,{},2,2,N,"{}"'.format(x + margen, FUENTE, _escapar(precio))
        )
        y_barcode = 84
    else:
        y_barcode = 60

    lineas.append(
        'B{},{},0,{},{},{},{},N,"{}"'.format(
            x + margen, y_barcode, tipo, modulo, modulo * 2, ALTO_BARRAS, _escapar(codigo)
        )
    )
    lineas.append(
        'A{},{},0,1,1,1,N,"{}"'.format(x + margen, y_barcode + 44, _escapar(codigo))
    )
    return lineas


def _encabezado(calibracion):
    """Lineas comunes a toda etiqueta.

    Con oscuridad 0 no se emite el comando D y la impresora usa la densidad que
    tiene configurada. En EPL2 la densidad es ABSOLUTA, asi que emitirla pisa la
    calibracion de la impresora y puede dejarla demasiado clara.
    """
    lineas = [
        "N",
        "q{}".format(calibracion["ancho_total"]),
        "Q{},{}".format(calibracion["alto"], GAP),
    ]
    if calibracion["oscuridad"]:
        lineas.append("D{}".format(_oscuridad_epl(calibracion["oscuridad"])))
    return lineas


def etiqueta(nombre, precio, codigo, calibracion):
    """Arma una fila completa de 3 etiquetas identicas en EPL2."""
    lineas = _encabezado(calibracion)
    for x in calibracion["offsets"]:
        lineas.extend(_columna(x, nombre, precio, codigo, calibracion))
    lineas.append("P1")
    return "\n".join(lineas) + "\n"


def filas(nombre, precio, codigo, calibracion, cantidad):
    """Concatena `cantidad` filas identicas en un solo trabajo de impresion."""
    if cantidad < 1:
        raise ValueError("la cantidad de filas debe ser 1 o mas")
    return etiqueta(nombre, precio, codigo, calibracion) * cantidad


def regla(calibracion):
    """Fila con marcas numeradas cada 25 dots, para calibrar contra el troquel."""
    lineas = _encabezado(calibracion)
    for x in range(0, calibracion["ancho_total"], 25):
        lineas.append("LO{},0,2,60".format(x))
        lineas.append('A{},64,0,1,1,1,N,"{}"'.format(x + 3, x))
    lineas.append("P1")
    return "\n".join(lineas) + "\n"
