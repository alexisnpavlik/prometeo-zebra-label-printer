# -*- coding: utf-8 -*-
"""Arma la fila de 3 etiquetas en EPL2, para impresoras que no aceptan ZPL.

EPL2 no es un dialecto de ZPL: son comandos de una letra, uno por linea, sin ^.
El buffer se limpia con N y se imprime con P1. Misma disposicion que el ZPL,
con las fuentes que usaba la app vieja en EPL: 2 para el nombre y 3 para el
precio.
"""

from modules import barcodes, textos, zpl_builder

TIPOS_EPL = {
    "^BEN": "E30",  # EAN-13
    "^BUN": "UA0",  # UPC-A
    "^B8N": "E80",  # EAN-8
    "^BCN": "1",    # Code 128
}

GAP = 24          # separacion entre filas de etiquetas, en dots
ALTO_BARRAS = zpl_builder.ALTO_BARRAS

# Avance por caracter de cada fuente EPL a 203 dpi (glifo + 2 dots de
# separacion), con multiplicador 1. Son de ancho fijo: el ancho real de un
# texto es largo x avance x multiplicador horizontal.
AVANCE_FUENTE = {1: 10, 2: 12, 3: 14, 4: 16, 5: 34}
FUENTE_NOMBRE = 2
FUENTE_PRECIO = 3
# Sin precio el numero y el nombre suben a la fuente 3 y el nombre usa dos lineas.
FUENTE_GRANDE = 3


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


def _texto(x, y, util, texto, fuente, mult_h=1, mult_v=1):
    """Linea A con `texto` centrado en el ancho util; se recorta si no entra."""
    avance = AVANCE_FUENTE[fuente] * mult_h
    texto = textos.recortar(texto, util, lambda caracter: avance)
    sobrante = util - len(texto) * avance
    return 'A{},{},0,{},{},{},N,"{}"'.format(
        x + sobrante // 2, y, fuente, mult_h, mult_v, _escapar(texto)
    )


def _columna(x, nombre, precio, codigo, calibracion):
    """Devuelve las lineas EPL de una columna con offset horizontal x.

    El margen superior se suma a cada Y en vez de mandarse como R: R queda
    grabado en la impresora y correria las etiquetas de las otras apps.
    """
    x = x + calibracion["margen"]
    arriba = calibracion["margen_superior"]
    util = calibracion["util"]
    comando, modulo = barcodes.elegir_barcode(codigo, util)
    fuentes_codigo = (2, 1) if precio else (FUENTE_GRANDE, 2, 1)
    fuente_codigo = next(
        (f for f in fuentes_codigo if len(codigo) * AVANCE_FUENTE[f] <= util), 1
    )

    lineas = [
        'B{},{},0,{},{},{},{},N,"{}"'.format(
            x, arriba + zpl_builder.Y_BARRAS, TIPOS_EPL[comando], modulo, modulo * 2,
            ALTO_BARRAS, _escapar(codigo),
        ),
        _texto(x, arriba + zpl_builder.Y_NUMERO, util, codigo, fuente_codigo),
    ]
    if not precio:
        avance = AVANCE_FUENTE[FUENTE_GRANDE]
        partes = textos.partir_en_lineas(
            nombre, util, lambda caracter: avance, zpl_builder.LINEAS_NOMBRE_GRANDE
        )
        for indice, parte in enumerate(partes):
            y = arriba + zpl_builder.Y_NOMBRE_GRANDE + indice * zpl_builder.ALTO_NOMBRE_GRANDE
            lineas.append(_texto(x, y, util, parte, FUENTE_GRANDE))
        return lineas

    lineas.append(_texto(x, arriba + zpl_builder.Y_NOMBRE, util, nombre, FUENTE_NOMBRE))
    precio = textos.precio_corto(precio)
    doble_ancho = len(precio) * AVANCE_FUENTE[FUENTE_PRECIO] * 2 <= util
    lineas.append(
        _texto(x, arriba + zpl_builder.Y_PRECIO, util, precio, FUENTE_PRECIO,
               2 if doble_ancho else 1, 2)
    )
    return lineas


def _encabezado(calibracion):
    """Lineas comunes a toda etiqueta.

    No emite el comando D, igual que la app vieja: en EPL2 la densidad es
    ABSOLUTA y emitirla pisa la calibracion de cada impresora.
    """
    return [
        "N",
        "q{}".format(calibracion["ancho_total"]),
        "Q{},{}".format(calibracion["alto"], GAP),
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
