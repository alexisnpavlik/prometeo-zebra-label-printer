# -*- coding: utf-8 -*-
"""Calibracion del rollo, persistida en config.json junto al ejecutable."""

import copy
import json
import os
import sys

CALIBRACION_DEFECTO = {
    "ancho_total": 736,   # ^PW, ancho del cabezal en dots
    "alto": 166,          # ^LL, largo de la etiqueta
    "offsets": [0, 256, 508],  # x de cada columna; el paso NO es uniforme
    "margen": 11,         # margen interno de cada columna
    "util": 190,          # ancho disponible para el contenido
    "oscuridad": 0,       # ajuste de densidad; 0 = respetar la de la impresora
    "lenguaje": "zpl",    # "zpl" o "epl"; se elige a mano, no se autodetecta
    "impresora": "",     # nombre de cola recordado; vacio si nunca se imprimio
    "tema": "claro",     # apariencia de la GUI: "claro" u "oscuro"
}


def directorio_base():
    """Directorio del ejecutable, o del fuente si corre sin congelar."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ruta_config():
    """Ruta del config.json."""
    return os.path.join(directorio_base(), "config.json")


# Motivo de la ultima falla al persistir la calibracion (crear o escribir el
# archivo). None si la ultima operacion de escritura salio bien o todavia no
# se intento ninguna. Sirve de diagnostico, en la misma linea que
# printers.ultimo_error_listado.
ultimo_error_config = None


def cargar(ruta=None):
    """Carga la calibracion, creando el archivo con los defectos si falta.

    Un JSON corrupto o incompleto no rompe la app: se completa con los defectos.
    Si el directorio no es escribible (ejecutable en Program Files, por
    ejemplo) tampoco rompe: la app sigue con los valores por defecto solo en
    memoria y el motivo queda en `ultimo_error_config`.
    """
    ruta = ruta or ruta_config()
    calibracion = copy.deepcopy(CALIBRACION_DEFECTO)
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                guardado = json.load(archivo)
            if isinstance(guardado, dict):
                calibracion.update(
                    {k: v for k, v in guardado.items() if k in CALIBRACION_DEFECTO}
                )
        except (ValueError, OSError):
            pass
    else:
        try:
            guardar(calibracion, ruta)
        except OSError:
            pass
    return calibracion


def guardar(calibracion, ruta=None):
    """Escribe la calibracion en el JSON.

    Propaga OSError si no se puede escribir (permisos, disco lleno, etc);
    quien llama decide como avisar. Registra el motivo en
    `ultimo_error_config` para diagnostico.
    """
    global ultimo_error_config
    ruta = ruta or ruta_config()
    try:
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(calibracion, archivo, indent=2, ensure_ascii=False)
    except OSError as error:
        ultimo_error_config = str(error)
        raise
    ultimo_error_config = None


def config_escribible(ruta=None):
    """True si la calibracion se puede persistir en `ruta` (o la de defecto)."""
    ruta = ruta or ruta_config()
    directorio = os.path.dirname(ruta) or "."
    if not os.access(directorio, os.W_OK):
        return False
    if os.path.exists(ruta) and not os.access(ruta, os.W_OK):
        return False
    return True
