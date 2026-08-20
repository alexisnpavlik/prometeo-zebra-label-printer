# -*- coding: utf-8 -*-
"""Arma el ZPL de una fila de 3 etiquetas para el rollo 3-across.

La impresora ve las 3 etiquetas de una fila como una sola etiqueta: el sensor
detecta el gap vertical, no los cortes laterales. Por eso es un unico ^XA con
tres columnas dibujadas en sus offsets, y no tres ^XA separados.
"""

from modules import barcodes


def _columna(x, nombre, precio, codigo, calibracion):
    """Devuelve el bloque ZPL de una columna con offset horizontal x."""
    margen = calibracion["margen"]
    util = calibracion["util"]
    comando, modulo = barcodes.elegir_barcode(codigo, util)

    bloque = [
        "^FO{},10^A0N,13,8^FB{},2,0,C,0^FD{}^FS".format(x + margen, util, nombre)
    ]
    if precio:
        bloque.append(
            "^FO{},48^A0N,24,16^FB{},1,0,C,0^FD{}^FS".format(x + margen, util, precio)
        )
        y_barcode = 84
    else:
        y_barcode = 60

    argumentos = ",N,N" if comando in ("^BEN", "^BUN", "^B8N") else ",N,N,N"
    bloque.append(
        "^FO{},{}^BY{}{},40{}^FD{}^FS".format(
            x + margen, y_barcode, modulo, comando, argumentos, codigo
        )
    )
    bloque.append(
        "^FO{},{}^A0N,14,9^FB{},1,0,C,0^FD{}^FS".format(
            x + margen, y_barcode + 44, util, codigo
        )
    )
    return "".join(bloque)


def _encabezado(calibracion):
    """Comandos comunes a toda etiqueta."""
    return "^XA^CI28^PW{}^LL{}^LH0,0^LS0^MD{}".format(
        calibracion["ancho_total"], calibracion["alto"], calibracion["oscuridad"]
    )


def etiqueta(nombre, precio, codigo, calibracion):
    """Arma una fila completa de 3 etiquetas identicas."""
    columnas = "".join(
        _columna(x, nombre, precio, codigo, calibracion)
        for x in calibracion["offsets"]
    )
    return "{}{}^XZ\n".format(_encabezado(calibracion), columnas)


def filas(nombre, precio, codigo, calibracion, cantidad):
    """Concatena `cantidad` filas identicas en un solo trabajo de impresion."""
    if cantidad < 1:
        raise ValueError("la cantidad de filas debe ser 1 o mas")
    return etiqueta(nombre, precio, codigo, calibracion) * cantidad


def regla(calibracion):
    """Fila con marcas numeradas cada 25 dots, para calibrar contra el troquel."""
    partes = [_encabezado(calibracion)]
    for x in range(0, calibracion["ancho_total"], 25):
        partes.append("^FO{},0^GB2,60,2^FS".format(x))
        partes.append("^FO{},64^A0N,18,10^FD{}^FS".format(x + 3, x))
    partes.append("^XZ\n")
    return "".join(partes)
