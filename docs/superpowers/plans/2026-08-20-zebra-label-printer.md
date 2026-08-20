# Zebra Label Printer — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicación de escritorio sin instalación, para Linux y Windows, que traduce el TXT de etiquetas de Odoo al ZPL calibrado del rollo 3-across y lo imprime en la Zebra.

**Architecture:** Cuatro módulos de funciones puras (`barcodes`, `zpl_parser`, `zpl_builder`, `config`) más un módulo de sistema (`printers`) que aísla las diferencias entre Linux y Windows. `main.py` es solo GUI: no contiene lógica de ZPL ni de impresión.

**Tech Stack:** Python 3.9+, biblioteca estándar únicamente (tkinter, ctypes, subprocess, json, unittest). PyInstaller solo en CI.

**Spec:** `docs/superpowers/specs/2026-08-20-zebra-label-printer-design.md`

## Global Constraints

- **Cero dependencias externas.** Solo stdlib. Nada de pywin32, customtkinter, pillow ni requests.
- **Python 3.9+** como piso (evitar sintaxis 3.10+ como `match` o `X | Y` en anotaciones).
- **snake_case** en todo el código; docstring en cada función.
- **Sin clases**, salvo la ventana de tkinter en `main.py`.
- **Envío RAW obligatorio:** el ZPL lo interpreta el firmware, nunca un driver.
- Calibración por defecto, medida contra el troquel real el 2026-08-20:
  `ancho_total=736`, `alto=166`, `offsets=[0, 256, 508]`, `margen=11`, `util=190`, `oscuridad=-6`.
- Los tests corren con `python3 -m unittest discover -s tests -v` y no requieren impresora.

---

### Task 1: Simbología y verificadores de código de barras

**Files:**
- Create: `modules/barcodes.py`
- Test: `tests/test_barcodes.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `verificador(datos: str) -> str` — dígito verificador EAN/UPC.
  - `modulos_code128(codigo: str) -> int` — módulos que ocupa un Code 128.
  - `elegir_barcode(codigo: str, ancho_max: int = 190) -> tuple` — devuelve `(comando, modulo)` donde `comando` es uno de `"^BEN"`, `"^BUN"`, `"^B8N"`, `"^BCN"` y `modulo` es un int de 1 a 3. Lanza `ValueError` si no entra.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_barcodes.py
import unittest

from modules import barcodes


class TestVerificador(unittest.TestCase):
    def test_ean13_del_anafe(self):
        self.assertEqual(barcodes.verificador("779482465848"), "8")

    def test_upca_del_scunci(self):
        self.assertEqual(barcodes.verificador("67787056807"), "9")


class TestElegirBarcode(unittest.TestCase):
    def test_ean13_valido_usa_be(self):
        self.assertEqual(barcodes.elegir_barcode("7794824658488"), ("^BEN", 2))

    def test_upca_valido_usa_bu(self):
        self.assertEqual(barcodes.elegir_barcode("677870568079"), ("^BUN", 2))

    def test_ean13_con_verificador_invalido_cae_a_code128(self):
        comando, _ = barcodes.elegir_barcode("7794824658487")
        self.assertEqual(comando, "^BCN")

    def test_codigo_interno_corto_usa_code128_que_entra(self):
        comando, modulo = barcodes.elegir_barcode("123456")
        self.assertEqual(comando, "^BCN")
        self.assertLessEqual(barcodes.modulos_code128("123456") * modulo, 190)

    def test_codigo_alfanumerico_baja_el_modulo(self):
        comando, modulo = barcodes.elegir_barcode("ABC-123")
        self.assertEqual(comando, "^BCN")
        self.assertEqual(modulo, 1)

    def test_codigo_demasiado_largo_falla(self):
        with self.assertRaises(ValueError):
            barcodes.elegir_barcode("A" * 60)

    def test_codigo_vacio_falla(self):
        with self.assertRaises(ValueError):
            barcodes.elegir_barcode("   ")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_barcodes -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'modules'`

- [ ] **Step 3: Write minimal implementation**

Crear `modules/__init__.py` vacío y `tests/__init__.py` vacío, y después:

```python
# modules/barcodes.py
# -*- coding: utf-8 -*-
"""Elige la simbologia de codigo de barras y el ancho de modulo.

En ZPL ^BC es Code 128, NO EAN-13. Usar ^BC para un EAN de 13 digitos da un
codigo de ~246 dots que no entra en una etiqueta de 212 y ademas no lee como
codigo de producto. Este modulo elige el comando correcto segun el codigo.
"""

import math

ANCHO_MAX_DEFECTO = 190


def verificador(datos):
    """Calcula el digito verificador EAN/UPC con pesos 1-3 desde la derecha."""
    digitos = [int(c) for c in datos][::-1]
    suma = sum(v * (3 if i % 2 == 0 else 1) for i, v in enumerate(digitos))
    return str((10 - suma % 10) % 10)


def modulos_code128(codigo):
    """Devuelve cuantos modulos ocupa el codigo en Code 128.

    Subset C si es todo digitos y de largo par (dos digitos por simbolo).
    """
    if codigo.isdigit() and len(codigo) % 2 == 0:
        simbolos = len(codigo) / 2
    else:
        simbolos = len(codigo)
    return 11 * (1 + math.ceil(simbolos) + 1) + 13


def elegir_barcode(codigo, ancho_max=ANCHO_MAX_DEFECTO):
    """Devuelve (comando_zpl, modulo) para que el codigo entre en ancho_max.

    Usa EAN/UPC solo si el largo y el verificador son validos; si no, Code 128,
    que acepta cualquier largo y contenido alfanumerico.
    """
    codigo = str(codigo).strip()
    if not codigo:
        raise ValueError("el codigo esta vacio")

    if codigo.isdigit():
        if len(codigo) == 13 and codigo[12] == verificador(codigo[:12]):
            return "^BEN", 2
        if len(codigo) == 12 and codigo[11] == verificador(codigo[:11]):
            return "^BUN", 2
        if len(codigo) == 8 and codigo[7] == verificador(codigo[:7]):
            return "^B8N", 2

    modulos = modulos_code128(codigo)
    for modulo in (3, 2, 1):
        if modulos * modulo <= ancho_max:
            return "^BCN", modulo
    raise ValueError(
        "{!r} necesita {} modulos y no entra en {} dots ni con modulo 1. "
        "Usa un codigo mas corto o un rollo mas ancho.".format(
            codigo, modulos, ancho_max
        )
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_barcodes -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add modules/__init__.py modules/barcodes.py tests/__init__.py tests/test_barcodes.py
git commit -m "feat: eleccion de simbologia de codigo de barras

^BC es Code 128, no EAN-13: usarlo para un EAN de 13 digitos produce un
codigo mas ancho que la etiqueta y que no lee como codigo de producto."
```

---

### Task 2: Parser del TXT de Odoo

**Files:**
- Create: `modules/zpl_parser.py`
- Test: `tests/test_zpl_parser.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `ParseError` — excepción, subclase de `Exception`.
  - `parsear(texto: str) -> dict` — devuelve `{"nombre": str, "precio": str or None, "codigo": str}`. Lanza `ParseError` si no encuentra el código.
  - `limpiar_nombre(nombre: str) -> str` — saca el prefijo `[CODIGO]` y el sufijo `(NNNNNN)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_zpl_parser.py
import unittest

from modules import zpl_parser

ODOO_CON_PRECIO = """
^XA^CI28
^FT100,80^A0N,40,30^FD[(658488/202039E/2020] "O.F" ANAFE 1 HORNALLA ESMALTADO REDUCCION BRONCE CONOMETAL (658488/202039E/202040E)^FS
^FT100,115^A0N,30,24^FD(658488/202039E^FS
^FO600,100,1
^A0N,66,48^FH^FD$41.000,00^FS
^FO100,160^BY3
^BCN,100,Y,N,N
^FD7794824658488^FS
^XZ
"""

ODOO_SIN_PRECIO = """
^XA^CI28
^FT100,80^A0N,40,30^FD[C-842B-17-7] SCUNCI DE TELA ESTAMPA LETRAS (CV) (568079)^FS
^FT100,150^A0N,30,24^FDC-842B-17-7^FS
^FO100,160^BY3
^BCN,100,Y,N,N
^FD677870568079^FS
^XZ
"""


class TestParsear(unittest.TestCase):
    def test_extrae_codigo_del_barcode(self):
        self.assertEqual(zpl_parser.parsear(ODOO_CON_PRECIO)["codigo"], "7794824658488")

    def test_extrae_precio(self):
        self.assertEqual(zpl_parser.parsear(ODOO_CON_PRECIO)["precio"], "$41.000,00")

    def test_sin_precio_devuelve_none(self):
        self.assertIsNone(zpl_parser.parsear(ODOO_SIN_PRECIO)["precio"])

    def test_nombre_sin_prefijo_ni_sufijo(self):
        nombre = zpl_parser.parsear(ODOO_SIN_PRECIO)["nombre"]
        self.assertEqual(nombre, 'SCUNCI DE TELA ESTAMPA LETRAS (CV)')

    def test_nombre_del_anafe_conserva_el_texto_util(self):
        nombre = zpl_parser.parsear(ODOO_CON_PRECIO)["nombre"]
        self.assertIn("ANAFE 1 HORNALLA", nombre)
        self.assertFalse(nombre.startswith("["))

    def test_texto_sin_barcode_lanza_parse_error(self):
        with self.assertRaises(zpl_parser.ParseError):
            zpl_parser.parsear("^XA^FT10,10^FDhola^FS^XZ")


class TestLimpiarNombre(unittest.TestCase):
    def test_saca_prefijo_entre_corchetes(self):
        self.assertEqual(zpl_parser.limpiar_nombre("[C-842B] SCUNCI"), "SCUNCI")

    def test_saca_sufijo_numerico_entre_parentesis(self):
        self.assertEqual(zpl_parser.limpiar_nombre("SCUNCI (568079)"), "SCUNCI")

    def test_conserva_parentesis_no_numericos(self):
        self.assertEqual(zpl_parser.limpiar_nombre("SCUNCI (CV)"), "SCUNCI (CV)")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_zpl_parser -v`
Expected: FAIL con `ImportError: cannot import name 'zpl_parser'`

- [ ] **Step 3: Write minimal implementation**

```python
# modules/zpl_parser.py
# -*- coding: utf-8 -*-
"""Extrae nombre, precio y codigo del ZPL que exporta Odoo.

El reporte de Odoo asume una etiqueta mucho mas ancha que el rollo real, asi
que no se imprime tal cual: se extraen los datos y se reconstruye la etiqueta
con la calibracion propia.
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


def parsear(texto):
    """Devuelve {"nombre", "precio", "codigo"} a partir del ZPL de Odoo."""
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_zpl_parser -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add modules/zpl_parser.py tests/test_zpl_parser.py
git commit -m "feat: parser del TXT de etiquetas de Odoo"
```

---

### Task 3: Configuración de calibración

**Files:**
- Create: `config/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `CALIBRACION_DEFECTO` — dict con las claves `ancho_total`, `alto`, `offsets`, `margen`, `util`, `oscuridad`.
  - `cargar(ruta: str = None) -> dict` — lee el JSON; si no existe lo crea con los valores por defecto. Si está corrupto o le faltan claves, completa con los defectos.
  - `guardar(calibracion: dict, ruta: str = None) -> None`
  - `ruta_config() -> str` — ruta del `config.json` junto al ejecutable.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import json
import os
import tempfile
import unittest

from config import config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ruta = os.path.join(self.dir, "config.json")

    def test_crea_el_archivo_si_no_existe(self):
        cal = config.cargar(self.ruta)
        self.assertTrue(os.path.exists(self.ruta))
        self.assertEqual(cal["offsets"], [0, 256, 508])

    def test_devuelve_los_valores_calibrados_por_defecto(self):
        cal = config.cargar(self.ruta)
        self.assertEqual(cal["ancho_total"], 736)
        self.assertEqual(cal["alto"], 166)
        self.assertEqual(cal["oscuridad"], -6)

    def test_guardar_y_volver_a_cargar(self):
        cal = config.cargar(self.ruta)
        cal["offsets"] = [0, 250, 500]
        config.guardar(cal, self.ruta)
        self.assertEqual(config.cargar(self.ruta)["offsets"], [0, 250, 500])

    def test_json_corrupto_vuelve_a_los_defectos(self):
        with open(self.ruta, "w") as f:
            f.write("{ esto no es json")
        self.assertEqual(config.cargar(self.ruta)["offsets"], [0, 256, 508])

    def test_completa_claves_faltantes(self):
        with open(self.ruta, "w") as f:
            json.dump({"offsets": [0, 1, 2]}, f)
        cal = config.cargar(self.ruta)
        self.assertEqual(cal["offsets"], [0, 1, 2])
        self.assertEqual(cal["margen"], 11)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_config -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write minimal implementation**

Crear `config/__init__.py` vacío y después:

```python
# config/config.py
# -*- coding: utf-8 -*-
"""Calibracion del rollo, persistida en config.json junto al ejecutable."""

import json
import os
import sys

CALIBRACION_DEFECTO = {
    "ancho_total": 736,   # ^PW, ancho del cabezal en dots
    "alto": 166,          # ^LL, largo de la etiqueta
    "offsets": [0, 256, 508],  # x de cada columna; el paso NO es uniforme
    "margen": 11,         # margen interno de cada columna
    "util": 190,          # ancho disponible para el contenido
    "oscuridad": -6,      # ^MD; sin esto las barras engordan y el EAN no lee
}


def directorio_base():
    """Directorio del ejecutable, o del fuente si corre sin congelar."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ruta_config():
    """Ruta del config.json."""
    return os.path.join(directorio_base(), "config.json")


def cargar(ruta=None):
    """Carga la calibracion, creando el archivo con los defectos si falta.

    Un JSON corrupto o incompleto no rompe la app: se completa con los defectos.
    """
    ruta = ruta or ruta_config()
    calibracion = dict(CALIBRACION_DEFECTO)
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
        guardar(calibracion, ruta)
    return calibracion


def guardar(calibracion, ruta=None):
    """Escribe la calibracion en el JSON."""
    ruta = ruta or ruta_config()
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(calibracion, archivo, indent=2, ensure_ascii=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_config -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
git add config/__init__.py config/config.py tests/test_config.py
git commit -m "feat: calibracion persistida en config.json"
```

---

### Task 4: Generador de ZPL 3-across

**Files:**
- Create: `modules/zpl_builder.py`
- Test: `tests/test_zpl_builder.py`

**Interfaces:**
- Consumes: `modules.barcodes.elegir_barcode`, `config.config.CALIBRACION_DEFECTO`.
- Produces:
  - `etiqueta(nombre: str, precio: str or None, codigo: str, calibracion: dict) -> str` — una fila `^XA…^XZ` de 3 columnas.
  - `filas(nombre, precio, codigo, calibracion, cantidad: int) -> str` — `cantidad` filas concatenadas.
  - `regla(calibracion: dict) -> str` — fila de calibración con marcas cada 25 dots.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_zpl_builder.py
import unittest

from config import config
from modules import zpl_builder

CAL = dict(config.CALIBRACION_DEFECTO)


class TestEtiqueta(unittest.TestCase):
    def test_empieza_y_termina_con_los_delimitadores(self):
        zpl = zpl_builder.etiqueta("ANAFE", "$41.000,00", "7794824658488", CAL)
        self.assertTrue(zpl.startswith("^XA"))
        self.assertTrue(zpl.strip().endswith("^XZ"))

    def test_usa_ean13_para_un_ean_valido(self):
        zpl = zpl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertIn("^BEN", zpl)
        self.assertNotIn("^BCN", zpl)

    def test_usa_upca_para_el_scunci(self):
        zpl = zpl_builder.etiqueta("SCUNCI", None, "677870568079", CAL)
        self.assertIn("^BUN", zpl)

    def test_dibuja_las_tres_columnas_en_sus_offsets(self):
        zpl = zpl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        for offset in CAL["offsets"]:
            self.assertIn("^FO{},".format(offset + CAL["margen"]), zpl)

    def test_incluye_ancho_alto_y_oscuridad(self):
        zpl = zpl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertIn("^PW736", zpl)
        self.assertIn("^LL166", zpl)
        self.assertIn("^MD-6", zpl)

    def test_con_precio_lo_incluye(self):
        zpl = zpl_builder.etiqueta("ANAFE", "$41.000,00", "7794824658488", CAL)
        self.assertEqual(zpl.count("$41.000,00"), 3)

    def test_sin_precio_no_lo_incluye(self):
        zpl = zpl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertNotIn("$", zpl)

    def test_codigo_invalido_propaga_el_error(self):
        with self.assertRaises(ValueError):
            zpl_builder.etiqueta("X", None, "A" * 60, CAL)


class TestFilas(unittest.TestCase):
    def test_tres_filas_son_tres_bloques(self):
        zpl = zpl_builder.filas("ANAFE", None, "7794824658488", CAL, 3)
        self.assertEqual(zpl.count("^XA"), 3)

    def test_cantidad_menor_a_uno_falla(self):
        with self.assertRaises(ValueError):
            zpl_builder.filas("ANAFE", None, "7794824658488", CAL, 0)


class TestRegla(unittest.TestCase):
    def test_tiene_marcas_numeradas(self):
        zpl = zpl_builder.regla(CAL)
        self.assertIn("^GB", zpl)
        self.assertIn("^FD25^FS", zpl)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_zpl_builder -v`
Expected: FAIL con `ImportError: cannot import name 'zpl_builder'`

- [ ] **Step 3: Write minimal implementation**

```python
# modules/zpl_builder.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_zpl_builder -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Commit**

```bash
git add modules/zpl_builder.py tests/test_zpl_builder.py
git commit -m "feat: generador de ZPL 3-across con calibracion"
```

---

### Task 5: Impresión multiplataforma

**Files:**
- Create: `modules/printers.py`
- Test: `tests/test_printers.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `ErrorImpresion` — excepción, subclase de `Exception`.
  - `listar() -> list` — nombres de impresora del sistema; lista vacía si no hay.
  - `imprimir_raw(impresora: str, datos: str) -> None` — envía ZPL crudo. Lanza `ErrorImpresion` con el mensaje del sistema si falla.

Nota para quien lo implemente: en Windows hay que usar `ctypes` contra
`winspool.drv`, no pywin32, porque el proyecto no admite dependencias. El
`datatype` DEBE ser `"RAW"`: cualquier otro hace que el driver rasterice el ZPL
en vez de pasarlo al firmware.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_printers.py
import unittest
from unittest import mock

from modules import printers


class TestListarLinux(unittest.TestCase):
    def test_parsea_la_salida_de_lpstat(self):
        salida = "printer QL-800 disabled since ayer\nprinter ZTC-GC420t idle\n"
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "check_output", return_value=salida):
                self.assertEqual(printers.listar(), ["QL-800", "ZTC-GC420t"])

    def test_sin_cups_devuelve_lista_vacia(self):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "check_output", side_effect=OSError):
                self.assertEqual(printers.listar(), [])


class TestImprimirLinux(unittest.TestCase):
    def test_manda_lp_con_raw(self):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "run") as correr:
                correr.return_value = mock.Mock(returncode=0, stderr=b"")
                printers.imprimir_raw("ZTC-GC420t", "^XA^XZ")
        argumentos = correr.call_args[0][0]
        self.assertIn("-o", argumentos)
        self.assertIn("raw", argumentos)
        self.assertIn("ZTC-GC420t", argumentos)

    def test_error_de_lp_lanza_error_impresion(self):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "run") as correr:
                correr.return_value = mock.Mock(returncode=1, stderr=b"no such printer")
                with self.assertRaises(printers.ErrorImpresion):
                    printers.imprimir_raw("inexistente", "^XA^XZ")

    def test_datos_vacios_falla(self):
        with self.assertRaises(ValueError):
            printers.imprimir_raw("ZTC-GC420t", "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_printers -v`
Expected: FAIL con `ImportError: cannot import name 'printers'`

- [ ] **Step 3: Write minimal implementation**

```python
# modules/printers.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_printers -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Verificar contra la impresora real**

Run:
```bash
python3 -c "
from modules import printers
print(printers.listar())
"
```
Expected: aparece `ZTC-GC420t--EPL--2` en la lista.

- [ ] **Step 6: Commit**

```bash
git add modules/printers.py tests/test_printers.py
git commit -m "feat: impresion RAW en Linux y Windows sin dependencias"
```

---

### Task 6: GUI

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: `config.config.cargar/guardar/CALIBRACION_DEFECTO`, `modules.printers.listar/imprimir_raw/ErrorImpresion`, `modules.zpl_parser.parsear/ParseError`, `modules.zpl_builder.filas/regla`, `modules.barcodes.elegir_barcode`.
- Produces: ejecutable `python3 main.py`.

- [ ] **Step 1: Escribir la ventana principal**

```python
# main.py
# -*- coding: utf-8 -*-
"""GUI para imprimir etiquetas de producto en la Zebra con rollo 3-across."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from config import config
from modules import barcodes, printers, zpl_builder, zpl_parser

NOMBRES_SIMBOLOGIA = {
    "^BEN": "EAN-13",
    "^BUN": "UPC-A",
    "^B8N": "EAN-8",
    "^BCN": "Code 128",
}


class Aplicacion(tk.Tk):
    """Ventana principal: cargar TXT, editar, imprimir."""

    def __init__(self):
        super().__init__()
        self.title("Etiquetas Zebra")
        self.resizable(False, False)
        self.calibracion = config.cargar()
        self._construir_menu()
        self._construir_widgets()
        self._refrescar_impresoras()

    def _construir_menu(self):
        """Menu con la calibracion, fuera del uso diario."""
        barra = tk.Menu(self)
        configuracion = tk.Menu(barra, tearoff=0)
        configuracion.add_command(label="Calibracion...", command=self._abrir_calibracion)
        configuracion.add_separator()
        configuracion.add_command(label="Imprimir regla", command=self._imprimir_regla)
        barra.add_cascade(label="Configuracion", menu=configuracion)
        self.config(menu=barra)

    def _construir_widgets(self):
        """Arma los controles de la pantalla principal."""
        marco = ttk.Frame(self, padding=12)
        marco.grid(row=0, column=0)

        ttk.Label(marco, text="Impresora:").grid(row=0, column=0, sticky="w", pady=3)
        self.impresora = ttk.Combobox(marco, width=38, state="readonly")
        self.impresora.grid(row=0, column=1, columnspan=2, sticky="w", pady=3)
        ttk.Button(marco, text="Refrescar", command=self._refrescar_impresoras).grid(
            row=0, column=3, padx=4
        )

        ttk.Button(marco, text="Cargar TXT...", command=self._cargar_txt).grid(
            row=1, column=0, sticky="w", pady=8
        )
        self.archivo = ttk.Label(marco, text="ningun archivo cargado", foreground="gray")
        self.archivo.grid(row=1, column=1, columnspan=3, sticky="w")

        ttk.Label(marco, text="Nombre:").grid(row=2, column=0, sticky="w", pady=3)
        self.nombre = ttk.Entry(marco, width=46)
        self.nombre.grid(row=2, column=1, columnspan=3, sticky="w", pady=3)

        ttk.Label(marco, text="Codigo:").grid(row=3, column=0, sticky="w", pady=3)
        self.codigo = ttk.Entry(marco, width=22)
        self.codigo.grid(row=3, column=1, sticky="w", pady=3)
        self.codigo.bind("<KeyRelease>", lambda _evento: self._actualizar_simbologia())
        self.simbologia = ttk.Label(marco, text="", foreground="gray")
        self.simbologia.grid(row=3, column=2, columnspan=2, sticky="w")

        ttk.Label(marco, text="Precio:").grid(row=4, column=0, sticky="w", pady=3)
        self.precio = ttk.Entry(marco, width=22)
        self.precio.grid(row=4, column=1, sticky="w", pady=3)
        self.con_precio = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            marco, text="Imprimir con precio", variable=self.con_precio
        ).grid(row=4, column=2, columnspan=2, sticky="w")

        ttk.Label(marco, text="Filas:").grid(row=5, column=0, sticky="w", pady=3)
        self.filas = tk.IntVar(value=1)
        ttk.Spinbox(marco, from_=1, to=99, width=5, textvariable=self.filas).grid(
            row=5, column=1, sticky="w", pady=3
        )
        ttk.Label(marco, text="(cada fila = 3 etiquetas)", foreground="gray").grid(
            row=5, column=2, columnspan=2, sticky="w"
        )

        self.boton_imprimir = ttk.Button(marco, text="Imprimir", command=self._imprimir)
        self.boton_imprimir.grid(row=6, column=3, sticky="e", pady=10)

    def _refrescar_impresoras(self):
        """Recarga la lista de impresoras del sistema."""
        disponibles = printers.listar()
        self.impresora["values"] = disponibles
        if disponibles:
            preferida = [n for n in disponibles if "GC420" in n or "ZTC" in n]
            self.impresora.set(preferida[0] if preferida else disponibles[0])
            self.boton_imprimir.state(["!disabled"])
        else:
            self.impresora.set("")
            self.boton_imprimir.state(["disabled"])

    def _cargar_txt(self):
        """Abre un TXT de Odoo y completa los campos."""
        ruta = filedialog.askopenfilename(
            title="Elegir el TXT de Odoo",
            filetypes=[("Etiquetas ZPL", "*.txt *.zpl"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        with open(ruta, "r", encoding="utf-8", errors="replace") as archivo:
            texto = archivo.read()
        self.archivo.config(text=ruta.split("/")[-1], foreground="black")
        try:
            datos = zpl_parser.parsear(texto)
        except zpl_parser.ParseError as error:
            messagebox.showwarning(
                "No se pudo leer el archivo",
                "{}\n\nCargá los campos a mano.".format(error),
            )
            return
        self._completar(datos)

    def _completar(self, datos):
        """Vuelca los datos parseados en los campos."""
        self.nombre.delete(0, tk.END)
        self.nombre.insert(0, datos["nombre"])
        self.codigo.delete(0, tk.END)
        self.codigo.insert(0, datos["codigo"])
        self.precio.delete(0, tk.END)
        self.precio.insert(0, datos["precio"] or "")
        self.con_precio.set(bool(datos["precio"]))
        self._actualizar_simbologia()

    def _actualizar_simbologia(self):
        """Muestra que simbologia se va a usar para el codigo cargado."""
        codigo = self.codigo.get().strip()
        if not codigo:
            self.simbologia.config(text="", foreground="gray")
            return
        try:
            comando, modulo = barcodes.elegir_barcode(codigo, self.calibracion["util"])
        except ValueError as error:
            self.simbologia.config(text=str(error)[:60], foreground="red")
            return
        nombre = NOMBRES_SIMBOLOGIA.get(comando, comando)
        if comando == "^BCN" and codigo.isdigit() and len(codigo) in (8, 12, 13):
            self.simbologia.config(
                text="{} — verificador invalido, no leera como EAN".format(nombre),
                foreground="red",
            )
        else:
            self.simbologia.config(
                text="{} (modulo {})".format(nombre, modulo), foreground="gray"
            )

    def _imprimir(self):
        """Arma el ZPL con los campos actuales y lo manda a la impresora."""
        nombre = self.nombre.get().strip()
        codigo = self.codigo.get().strip()
        precio = self.precio.get().strip() if self.con_precio.get() else None
        if not codigo:
            messagebox.showerror("Falta el codigo", "Cargá el codigo del producto.")
            return
        try:
            zpl = zpl_builder.filas(
                nombre, precio, codigo, self.calibracion, self.filas.get()
            )
        except ValueError as error:
            messagebox.showerror("No se puede imprimir", str(error))
            return
        self._enviar(zpl)

    def _imprimir_regla(self):
        """Imprime la regla de calibracion."""
        self._enviar(zpl_builder.regla(self.calibracion))

    def _enviar(self, zpl):
        """Envia el ZPL, mostrando el error del sistema si falla."""
        try:
            printers.imprimir_raw(self.impresora.get(), zpl)
        except (printers.ErrorImpresion, ValueError) as error:
            messagebox.showerror("Error al imprimir", str(error))

    def _abrir_calibracion(self):
        """Ventana de calibracion, con los valores del config.json."""
        ventana = tk.Toplevel(self)
        ventana.title("Calibracion")
        ventana.resizable(False, False)
        marco = ttk.Frame(ventana, padding=12)
        marco.grid(row=0, column=0)

        campos = {}
        etiquetas = [
            ("ancho_total", "Ancho total (^PW)"),
            ("alto", "Alto (^LL)"),
            ("margen", "Margen interno"),
            ("util", "Ancho util"),
            ("oscuridad", "Oscuridad (^MD)"),
        ]
        for fila, (clave, texto) in enumerate(etiquetas):
            ttk.Label(marco, text=texto).grid(row=fila, column=0, sticky="w", pady=2)
            entrada = ttk.Entry(marco, width=10)
            entrada.insert(0, str(self.calibracion[clave]))
            entrada.grid(row=fila, column=1, sticky="w", pady=2)
            campos[clave] = entrada

        ttk.Label(marco, text="Offsets de columna").grid(
            row=len(etiquetas), column=0, sticky="w", pady=2
        )
        offsets = ttk.Entry(marco, width=18)
        offsets.insert(0, ", ".join(str(x) for x in self.calibracion["offsets"]))
        offsets.grid(row=len(etiquetas), column=1, sticky="w", pady=2)

        def guardar():
            """Valida y persiste la calibracion."""
            try:
                nueva = {c: int(e.get()) for c, e in campos.items()}
                nueva["offsets"] = [int(x) for x in offsets.get().split(",")]
            except ValueError:
                messagebox.showerror(
                    "Valores invalidos", "Todos los campos deben ser numeros enteros."
                )
                return
            if len(nueva["offsets"]) < 1:
                messagebox.showerror("Offsets invalidos", "Poné al menos un offset.")
                return
            self.calibracion.update(nueva)
            config.guardar(self.calibracion)
            self._actualizar_simbologia()
            ventana.destroy()

        ttk.Button(marco, text="Imprimir regla", command=self._imprimir_regla).grid(
            row=len(etiquetas) + 1, column=0, pady=10, sticky="w"
        )
        ttk.Button(marco, text="Guardar", command=guardar).grid(
            row=len(etiquetas) + 1, column=1, pady=10, sticky="e"
        )


def main():
    """Punto de entrada."""
    Aplicacion().mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar que abre y que los módulos enganchan**

Run: `python3 main.py`
Expected: abre la ventana, el combo lista las impresoras del sistema, y al escribir `7794824658488` en Codigo aparece "EAN-13 (modulo 2)".

- [ ] **Step 3: Verificar el flujo completo contra la impresora**

Run: cargar `~/Downloads/Etiqueta del producto (ZPL) (3).txt`, confirmar que el nombre sale sin el prefijo `[C-842B-17-7]`, que la simbología dice UPC-A, y darle Imprimir con 1 fila.
Expected: sale una fila de 3 etiquetas bien alineadas.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: GUI para cargar, editar e imprimir etiquetas"
```

---

### Task 7: Build automático y documentación

**Files:**
- Create: `.github/workflows/build.yml`
- Create: `README.md`
- Create: `.gitignore`

**Interfaces:**
- Consumes: `main.py` y los módulos de las tareas anteriores.
- Produces: artefactos `etiquetas-zebra.exe` y `etiquetas-zebra` (Linux).

- [ ] **Step 1: Escribir el workflow**

```yaml
# .github/workflows/build.yml
name: build

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m unittest discover -s tests -v

  build:
    needs: test
    strategy:
      matrix:
        include:
          - os: windows-latest
            nombre: etiquetas-zebra-windows
          - os: ubuntu-latest
            nombre: etiquetas-zebra-linux
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install pyinstaller
      - run: pyinstaller --onefile --windowed --name etiquetas-zebra main.py
      - uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.nombre }}
          path: dist/
```

- [ ] **Step 2: Escribir el .gitignore**

```
__pycache__/
*.pyc
build/
dist/
*.spec
config.json
```

- [ ] **Step 3: Escribir el README**

```markdown
# Etiquetas Zebra

Imprime etiquetas de producto en una Zebra GC420t con rollo 3-across, a partir
del TXT que exporta Odoo.

## Por que existe

El reporte de Odoo genera un ZPL para una etiqueta mucho mas ancha que el rollo
real, y usa `^BC` (Code 128) para codigos que son EAN-13 o UPC-A. Enviado tal
cual, el contenido se corta e invade la etiqueta vecina y el codigo no lee como
codigo de producto. Esta app extrae los datos y rearma la etiqueta con la
simbologia correcta y la calibracion del rollo.

## Uso

1. Elegir la impresora.
2. Cargar el TXT de Odoo (o escribir los campos a mano).
3. Ajustar el nombre si hace falta y marcar o desmarcar el precio.
4. Elegir cuantas filas imprimir. Cada fila son 3 etiquetas.

## Calibracion

En **Configuracion → Calibracion**. Se toca solo al cambiar de rollo.

Para recalibrar: **Imprimir regla**, mirar en que numero cae el borde izquierdo
de cada etiqueta, y poner esos numeros en "Offsets de columna".

Valores del rollo actual: ancho 736, alto 166, offsets `0, 256, 508`, margen 11,
ancho util 190, oscuridad -6.

La oscuridad negativa importa: sin ella las barras engordan y el codigo no lee.

## Desarrollo

Solo biblioteca estandar. Sin `pip install` para correrlo:

    python3 main.py
    python3 -m unittest discover -s tests -v

Los ejecutables los compila GitHub Actions con PyInstaller.
```

- [ ] **Step 4: Correr toda la suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 39 tests

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/build.yml README.md .gitignore
git commit -m "chore: build en CI para Windows y Linux, y documentacion"
```
