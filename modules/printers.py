# -*- coding: utf-8 -*-
"""Lista impresoras y envia ZPL crudo, en Linux y en Windows.

El envio tiene que ser RAW: el ZPL lo interpreta el firmware de la Zebra. Si el
driver lo rasteriza, las barras caen entre pixeles y el codigo deja de leer.
"""

import subprocess
import sys


class ErrorImpresion(Exception):
    """Fallo al enviar el trabajo a la impresora."""


def _es_windows():
    """True si corre sobre Windows."""
    return sys.platform.startswith("win")


def _listar_linux():
    """Nombres de impresora segun CUPS."""
    try:
        salida = subprocess.check_output(["lpstat", "-a"], universal_newlines=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    nombres = []
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) >= 2 and partes[0] == "printer":
            nombres.append(partes[1])
        elif partes:
            nombres.append(partes[0])
    return nombres


def _listar_windows():
    """Nombres de impresora segun winspool."""
    import ctypes
    from ctypes import wintypes

    class PRINTER_INFO_4(ctypes.Structure):
        _fields_ = [
            ("pPrinterName", wintypes.LPWSTR),
            ("pServerName", wintypes.LPWSTR),
            ("Attributes", wintypes.DWORD),
        ]

    winspool = ctypes.WinDLL("winspool.drv")
    necesarios = wintypes.DWORD(0)
    devueltos = wintypes.DWORD(0)
    banderas = 2 | 4  # LOCAL | CONNECTIONS

    winspool.EnumPrintersW(
        banderas, None, 4, None, 0, ctypes.byref(necesarios), ctypes.byref(devueltos)
    )
    if necesarios.value == 0:
        return []

    buffer = ctypes.create_string_buffer(necesarios.value)
    if not winspool.EnumPrintersW(
        banderas,
        None,
        4,
        buffer,
        necesarios.value,
        ctypes.byref(necesarios),
        ctypes.byref(devueltos),
    ):
        return []

    info = ctypes.cast(buffer, ctypes.POINTER(PRINTER_INFO_4))
    return [info[i].pPrinterName for i in range(devueltos.value)]


def listar():
    """Devuelve los nombres de impresora disponibles en el sistema."""
    if _es_windows():
        try:
            return _listar_windows()
        except Exception:
            return []
    return _listar_linux()


def _imprimir_linux(impresora, datos):
    """Envia por CUPS con -o raw."""
    resultado = subprocess.run(
        ["lp", "-d", impresora, "-o", "raw"],
        input=datos.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if resultado.returncode != 0:
        raise ErrorImpresion(resultado.stderr.decode("utf-8", "replace").strip())


def _imprimir_windows(impresora, datos):
    """Envia por winspool con datatype RAW."""
    import ctypes
    from ctypes import wintypes

    class DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]

    winspool = ctypes.WinDLL("winspool.drv")
    handle = wintypes.HANDLE()
    if not winspool.OpenPrinterW(impresora, ctypes.byref(handle), None):
        raise ErrorImpresion("no se pudo abrir la impresora {!r}".format(impresora))

    try:
        documento = DOC_INFO_1("Etiquetas ZPL", None, "RAW")
        if not winspool.StartDocPrinterW(handle, 1, ctypes.byref(documento)):
            raise ErrorImpresion("no se pudo iniciar el trabajo de impresion")
        try:
            if not winspool.StartPagePrinter(handle):
                raise ErrorImpresion("no se pudo iniciar la pagina")
            crudo = datos.encode("utf-8")
            escritos = wintypes.DWORD(0)
            if not winspool.WritePrinter(
                handle, crudo, len(crudo), ctypes.byref(escritos)
            ):
                raise ErrorImpresion("fallo el envio de datos a la impresora")
            winspool.EndPagePrinter(handle)
        finally:
            winspool.EndDocPrinter(handle)
    finally:
        winspool.ClosePrinter(handle)


def imprimir_raw(impresora, datos):
    """Envia ZPL crudo a la impresora indicada."""
    if not datos:
        raise ValueError("no hay nada para imprimir")
    if not impresora:
        raise ValueError("no se selecciono impresora")
    if _es_windows():
        _imprimir_windows(impresora, datos)
    else:
        _imprimir_linux(impresora, datos)
