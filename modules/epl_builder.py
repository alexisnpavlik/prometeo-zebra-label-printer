# -*- coding: utf-8 -*-
"""Arma la fila de 3 etiquetas en EPL2, para impresoras que no aceptan ZPL.

EPL2 no es un dialecto de ZPL: son comandos de una letra, uno por linea, sin ^.
El buffer se limpia con N y se imprime con P1. La oscuridad es absoluta (D0-D15),
no relativa como el ^MD de ZPL.
"""

from modules import barcodes

TIPOS_EPL = {
    "^BEN": "E30",  # EAN-13
    "^BUN": "UA0",  # UPC-A
    "^B8N": "E80",  # EAN-8
    "^BCN": "1",    # Code 128
}

GAP = 24          # separacion entre filas de etiquetas, en dots
FUENTE = "2"      # fuente EPL de tamano fijo
ALTO_BARRAS = 40


def _escapar(texto):
    """Escapa comillas y barras, que en EPL2 delimitan el texto."""
    return texto.replace("\\", "\\\\").replace('"', '\\"')


def _oscuridad_epl(oscuridad_zpl):
    """Traduce el ^MD relativo de ZPL a la densidad absoluta D0-D15 de EPL."""
    return max(0, min(15, 15 + oscuridad_zpl - 1))


def _columna(x, nombre, precio, codigo, calibracion):
    """Devuelve las lineas EPL de una columna con offset horizontal x."""
    margen = calibracion["margen"]
    comando, modulo = barcodes.elegir_barcode(codigo, calibracion["util"])
    tipo = TIPOS_EPL[comando]

    lineas = ['A{},10,0,{},1,1,N,"{}"'.format(x + margen, FUENTE, _escapar(nombre))]
    if precio:
        lineas.append(
            'A{},48,0,{},2,2,N,"{}"'.format(x + margen, FUENTE, _escapar(precio))
        )
        y_barcode = 84
    else:
        y_barcode = 60

    lineas.append(
        'B{},{},0,"{}",{},{},{},N,"{}"'.format(
            x + margen, y_barcode, tipo, modulo, modulo * 2, ALTO_BARRAS, codigo
        )
    )
    lineas.append(
        'A{},{},0,1,1,1,N,"{}"'.format(x + margen, y_barcode + 44, codigo)
    )
    return lineas


def _encabezado(calibracion):
    """Lineas comunes a toda etiqueta."""
    return [
        "N",
        "q{}".format(calibracion["ancho_total"]),
        "Q{},{}".format(calibracion["alto"], GAP),
        "D{}".format(_oscuridad_epl(calibracion["oscuridad"])),
    ]


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
