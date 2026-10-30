# -*- coding: utf-8 -*-
"""Arma el ZPL de una fila de 3 etiquetas para el rollo 3-across.

La impresora ve las 3 etiquetas de una fila como una sola etiqueta: el sensor
detecta el gap vertical, no los cortes laterales. Por eso es un unico ^XA con
tres columnas dibujadas en sus offsets, y no tres ^XA separados.
"""

from modules import barcodes, textos

# Disposicion y fuentes de zebra_label_printer_odoo, la app vieja, que imprime
# nitido en todas las Zebra: barras arriba, numero, nombre en una linea y el
# precio grande abajo. Con letras mas chicas los trazos quedan de 1 dot y salen
# borrosos. Coordenadas en dots, relativas al borde superior de la etiqueta.
Y_BARRAS = 4
ALTO_BARRAS = 40
BAJADA_GUARDAS = 12  # las guardas del EAN/UPC bajan 12 dots mas (medido en Labelary)
Y_NUMERO = 60
ALTO_NUMERO = 18
Y_NOMBRE = 80
Y_PRECIO = 102
PRECIO_GRANDE_MAX = 8  # hasta 8 caracteres va en 48x24; si no, en 40x16

# Sin precio queda libre la parte de abajo: numero y nombre van mas grandes y
# el nombre ocupa dos lineas en vez de recortarse en una.
ALTO_NUMERO_GRANDE = 28
ANCHO_NUMERO_GRANDE = 16
Y_NOMBRE_GRANDE = 92
ALTO_NOMBRE_GRANDE = 28
ANCHO_NOMBRE_GRANDE = 13
LINEAS_NOMBRE_GRANDE = 2


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
    """Devuelve el bloque ZPL de una columna con offset horizontal x.

    El margen superior se suma a cada ^FO en vez de mandarse como ^LH: ^LH
    queda grabado en la impresora y correria tambien las etiquetas que
    imprimen Odoo o la app vieja, que no lo resetean.
    """
    x = x + calibracion["margen"]
    arriba = calibracion["margen_superior"]
    util = calibracion["util"]
    comando, modulo = barcodes.elegir_barcode(codigo, util)
    argumentos = ",N,N" if comando in ("^BEN", "^BUN", "^B8N") else ",N,N,N"

    bloque = [
        "^FO{},{}^BY{}{},{}{}^FH\\^FD{}^FS".format(
            x, arriba + Y_BARRAS, modulo, comando, ALTO_BARRAS, argumentos, _escapar(codigo)
        ),
    ]
    if not precio:
        return "".join(bloque + _numero_y_nombre_grandes(x, arriba, nombre, codigo, util))

    bloque += [
        _texto(x, arriba + Y_NUMERO, ALTO_NUMERO, 10, util, codigo),
        _texto(x, arriba + Y_NOMBRE, 20, 10, util,
               textos.recortar(nombre, util, textos.ancho_a0_nombre)),
    ]
    precio = textos.precio_corto(precio)
    alto, ancho = (48, 24) if len(precio) <= PRECIO_GRANDE_MAX else (40, 16)
    bloque.append(_texto(x, arriba + Y_PRECIO, alto, ancho, util, precio))
    return "".join(bloque)


def _texto(x, y, alto, ancho, util, texto):
    """Campo ^A0 de una linea centrado en el ancho util."""
    return "^FO{},{}^A0N,{},{}^FB{},1,0,C,0^FH\\^FD{}^FS".format(
        x, y, alto, ancho, util, _escapar(texto)
    )


def _numero_y_nombre_grandes(x, arriba, nombre, codigo, util):
    """Numero y nombre en la fuente grande, para etiquetas sin precio.

    Un codigo que no entra en la fuente grande (Code 128 largo) vuelve a la
    chica: ^FB lo partiria en dos lineas y la segunda pisaria el nombre.
    """
    if textos.ancho(codigo, textos.ancho_a0(ANCHO_NUMERO_GRANDE)) <= util:
        campos = [_texto(x, arriba + Y_NUMERO, ALTO_NUMERO_GRANDE, ANCHO_NUMERO_GRANDE, util, codigo)]
    else:
        campos = [_texto(x, arriba + Y_NUMERO, ALTO_NUMERO, 10, util, codigo)]
    lineas = textos.partir_en_lineas(
        nombre, util, textos.ancho_a0(ANCHO_NOMBRE_GRANDE), LINEAS_NOMBRE_GRANDE
    )
    for indice, linea in enumerate(lineas):
        y = arriba + Y_NOMBRE_GRANDE + indice * ALTO_NOMBRE_GRANDE
        campos.append(_texto(x, y, ALTO_NOMBRE_GRANDE, ANCHO_NOMBRE_GRANDE, util, linea))
    return campos


def _encabezado(calibracion):
    """Comandos comunes a toda etiqueta.

    No emite ^MD ni ningun otro comando de densidad, igual que la app vieja:
    cada impresora usa la que tiene configurada. ^MD es relativo a esa
    densidad, asi que un ajuste que queda bien en una deja la otra borrosa.
    """
    return "^XA^CI28^PW{}^LL{}^LH0,0^LS0".format(
        calibracion["ancho_total"], calibracion["alto"]
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
