# -*- coding: utf-8 -*-
"""Arma el ZPL de una fila de 3 etiquetas para el rollo 3-across.

La impresora ve las 3 etiquetas de una fila como una sola etiqueta: el sensor
detecta el gap vertical, no los cortes laterales. Por eso es un unico ^XA con
tres columnas dibujadas en sus offsets, y no tres ^XA separados.
"""

from modules import barcodes


def _escapar(texto):
    """Escapa los prefijos de comando ZPL dentro de un campo ^FD.

    El firmware corta el campo ^FD en cuanto ve ^ o ~, sean parte del texto o
    no: con un nombre como "PINTURA 3^4" el campo termina en "PINTURA 3" y
    "^4" se interpreta como comando desconocido, arrastrando el resto de la
    columna. ^FH\\ antes del campo habilita las secuencias _XX (hex de 2
    digitos); reemplazando ^ por _5E y ~ por _7E el dato sale literal.

    El guion bajo tambien hay que escaparlo, y antes que nada: con ^FH activo
    el firmware trata cualquier _XX como escape hexadecimal, asi que un
    guion bajo literal seguido de dos hex validos (un SKU como "SKU_5E123")
    se reinterpretaria como el caracter que codifica. Escapar _ primero
    evita re-escapar los guiones bajos que generan los reemplazos de ^ y ~.
    """
    return texto.replace("_", "_5F").replace("^", "_5E").replace("~", "_7E")


def _columna(x, nombre, precio, codigo, calibracion):
    """Devuelve el bloque ZPL de una columna con offset horizontal x."""
    margen = calibracion["margen"]
    util = calibracion["util"]
    comando, modulo = barcodes.elegir_barcode(codigo, util)

    bloque = [
        "^FO{},10^A0N,13,8^FB{},2,0,C,0^FH\\^FD{}^FS".format(
            x + margen, util, _escapar(nombre)
        )
    ]
    if precio:
        bloque.append(
            "^FO{},48^A0N,24,16^FB{},1,0,C,0^FH\\^FD{}^FS".format(
                x + margen, util, _escapar(precio)
            )
        )
        y_barcode = 84
    else:
        y_barcode = 60

    argumentos = ",N,N" if comando in ("^BEN", "^BUN", "^B8N") else ",N,N,N"
    bloque.append(
        "^FO{},{}^BY{}{},40{}^FH\\^FD{}^FS".format(
            x + margen, y_barcode, modulo, comando, argumentos, _escapar(codigo)
        )
    )
    bloque.append(
        "^FO{},{}^A0N,14,9^FB{},1,0,C,0^FH\\^FD{}^FS".format(
            x + margen, y_barcode + 44, util, _escapar(codigo)
        )
    )
    return "".join(bloque)


def _encabezado(calibracion):
    """Comandos comunes a toda etiqueta.

    Con oscuridad 0 no se emite ^MD y la impresora usa la densidad que tiene
    configurada. ^MD es RELATIVO: el mismo valor da resultados distintos en cada
    impresora, y en una configurada baja deja la etiqueta ilegible.
    """
    encabezado = "^XA^CI28^PW{}^LL{}^LH0,0^LS0".format(
        calibracion["ancho_total"], calibracion["alto"]
    )
    if calibracion["oscuridad"]:
        encabezado += "^MD{}".format(calibracion["oscuridad"])
    return encabezado


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
