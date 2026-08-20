# -*- coding: utf-8 -*-
"""Lista impresoras y envia ZPL crudo, en Linux y en Windows.

El envio tiene que ser RAW: el ZPL lo interpreta el firmware de la Zebra. Si el
driver lo rasteriza, las barras caen entre pixeles y el codigo deja de leer.
"""

import subprocess
import sys


class ErrorImpresion(Exception):
    """Fallo al enviar el trabajo a la impresora."""


# Motivo de la ultima falla real de listar() en Windows (no se expone en el
# contrato de listar(), que siempre devuelve una lista; sirve para diagnostico
# remoto cuando "no hay impresoras" en realidad era un error del sistema).
ultimo_error_listado = None

# Cache del WinDLL de winspool, para no recargarlo ni redeclarar argtypes en
# cada llamada. Se crea perezosamente porque WinDLL no existe fuera de Windows.
_winspool_dll = None


def _es_windows():
    """True si corre sobre Windows."""
    return sys.platform.startswith("win")


def _winspool():
    """Devuelve el WinDLL de winspool.drv, cacheado, con codigos de error del sistema."""
    global _winspool_dll
    if _winspool_dll is None:
        import ctypes
        from ctypes import wintypes

        dll = ctypes.WinDLL("winspool.drv", use_last_error=True)

        dll.OpenPrinterW.argtypes = [
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.HANDLE),
            wintypes.LPVOID,
        ]
        dll.OpenPrinterW.restype = wintypes.BOOL

        dll.WritePrinter.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        dll.WritePrinter.restype = wintypes.BOOL

        dll.StartDocPrinterW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPVOID,
        ]
        dll.StartDocPrinterW.restype = wintypes.DWORD

        dll.EnumPrintersW.argtypes = [
            wintypes.DWORD,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        dll.EnumPrintersW.restype = wintypes.BOOL

        _winspool_dll = dll
    return _winspool_dll


def _error_sistema_windows():
    """Mensaje de error del sistema (FormatMessage) para la ultima falla de winspool."""
    import ctypes

    return str(ctypes.WinError(ctypes.get_last_error()))


def _listar_linux():
    """Nombres de impresora segun CUPS."""
    try:
        salida = subprocess.check_output(["lpstat", "-e"], universal_newlines=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return [linea.strip() for linea in salida.splitlines() if linea.strip()]


def _listar_windows():
    """Nombres de impresora segun winspool. Lanza ErrorImpresion si algo falla de verdad."""
    import ctypes
    from ctypes import wintypes

    ERROR_INSUFFICIENT_BUFFER = 122

    class PRINTER_INFO_4(ctypes.Structure):
        _fields_ = [
            ("pPrinterName", wintypes.LPWSTR),
            ("pServerName", wintypes.LPWSTR),
            ("Attributes", wintypes.DWORD),
        ]

    winspool = _winspool()
    necesarios = wintypes.DWORD(0)
    devueltos = wintypes.DWORD(0)
    banderas = 2 | 4  # LOCAL | CONNECTIONS

    ctypes.set_last_error(0)
    if not winspool.EnumPrintersW(
        banderas, None, 4, None, 0, ctypes.byref(necesarios), ctypes.byref(devueltos)
    ):
        codigo = ctypes.get_last_error()
        if codigo != ERROR_INSUFFICIENT_BUFFER:
            raise ErrorImpresion(_error_sistema_windows())
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
        raise ErrorImpresion(_error_sistema_windows())

    info = ctypes.cast(buffer, ctypes.POINTER(PRINTER_INFO_4))
    return [info[i].pPrinterName for i in range(devueltos.value)]


def listar():
    """Devuelve los nombres de impresora disponibles en el sistema."""
    global ultimo_error_listado
    if _es_windows():
        try:
            resultado = _listar_windows()
        except Exception as error:
            ultimo_error_listado = str(error)
            print(
                "printers: fallo al listar impresoras: {0}".format(error),
                file=sys.stderr,
            )
            return []
        ultimo_error_listado = None
        return resultado
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

    winspool = _winspool()
    handle = wintypes.HANDLE()
    if not winspool.OpenPrinterW(impresora, ctypes.byref(handle), None):
        raise ErrorImpresion(_error_sistema_windows())

    trabajo_iniciado = False
    try:
        documento = DOC_INFO_1("Etiquetas ZPL", None, "RAW")
        if not winspool.StartDocPrinterW(handle, 1, ctypes.byref(documento)):
            raise ErrorImpresion(_error_sistema_windows())
        trabajo_iniciado = True

        if not winspool.StartPagePrinter(handle):
            raise ErrorImpresion(_error_sistema_windows())

        crudo = datos.encode("utf-8")
        escritos = wintypes.DWORD(0)
        if not winspool.WritePrinter(
            handle, crudo, len(crudo), ctypes.byref(escritos)
        ):
            raise ErrorImpresion(_error_sistema_windows())
        if escritos.value != len(crudo):
            raise ErrorImpresion(
                "escritura incompleta: {0} de {1} bytes enviados".format(
                    escritos.value, len(crudo)
                )
            )

        winspool.EndPagePrinter(handle)
        winspool.EndDocPrinter(handle)
    except Exception:
        if trabajo_iniciado:
            winspool.AbortPrinter(handle)
        raise
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
