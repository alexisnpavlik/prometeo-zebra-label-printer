# Zebra Label Printer — Diseño

Fecha: 2026-08-20

## Problema

El reporte de etiquetas de Odoo exporta un ZPL pensado para una etiqueta mucho
más ancha que el rollo real, y usa `^BC` (Code 128) para códigos que son EAN-13
o UPC-A. Enviado tal cual a la Zebra GC420t con rollo 3-across, el contenido se
corta e invade la etiqueta vecina, y el código de barras no corresponde a la
simbología del producto.

Hoy eso se resuelve a mano con un script de Python y `lp` desde la terminal.
Este proyecto lo convierte en una aplicación de escritorio que corra en Linux y
Windows sin instalación previa.

## Alcance

Incluye:
- Seleccionar la impresora entre las del sistema.
- Cargar el TXT de Odoo y extraer nombre, precio y código.
- Editar el nombre antes de imprimir.
- Check para imprimir con o sin precio.
- Elegir cuántas filas imprimir (cada fila = 3 etiquetas).
- Calibración editable, oculta en Configuración.

Excluye (por ahora):
- Tandas de varios productos.
- Historial de impresiones.
- Diseño libre de etiquetas.

## Restricciones

- **Sin dependencias externas.** Solo biblioteca estándar de Python 3, para que
  PyInstaller produzca un ejecutable único y liviano. Descarta customtkinter y
  pywin32.
- **Dos sistemas operativos** con mecanismos de impresión distintos.
- El envío debe ser **RAW**: el ZPL lo interpreta el firmware, no un driver.

## Arquitectura

```
zebra-label-printer/
├── main.py                    # GUI tkinter
├── config/config.py           # carga y guarda config.json
├── modules/
│   ├── printers.py            # listar impresoras + enviar RAW
│   ├── zpl_parser.py          # TXT de Odoo -> dict
│   ├── zpl_builder.py         # arma el ZPL 3-across
│   └── barcodes.py            # simbología + verificadores
└── .github/workflows/build.yml
```

Flujo: `zpl_parser` → campos editables en la GUI → `zpl_builder` (con la
calibración de `config`) → `printers`. Cada módulo es independiente y se puede
probar sin GUI ni impresora.

### modules/barcodes.py

`elegir_barcode(codigo, ancho_max)` devuelve `(comando_zpl, modulo)`.

| Código | Simbología | Ancho a módulo 2 |
|---|---|---|
| 13 dígitos, verificador válido | `^BE` EAN-13 | 190 dots |
| 12 dígitos, verificador válido | `^BU` UPC-A | 190 dots |
| 8 dígitos, verificador válido | `^B8` EAN-8 | 134 dots |
| cualquier otro | `^BC` Code 128 | según largo |

Para Code 128 baja el módulo de 3 a 2 a 1 hasta que entre en `ancho_max`; si no
entra ni con módulo 1, lanza `ValueError` con el motivo.

`verificador(datos)` calcula el dígito EAN/UPC con pesos 1-3 de derecha a
izquierda.

**Este módulo es el corazón del proyecto**: es donde estaba el error que hacía
que las etiquetas salieran cortadas.

### modules/zpl_parser.py

`parsear(texto)` devuelve `{"nombre", "precio", "codigo"}` desde el ZPL de Odoo.

- Nombre: primer `^FD` de un campo de texto, sin el prefijo `[CODIGO]` ni el
  sufijo `(NNNNNN)` que agrega Odoo.
- Precio: `^FD` que empieza con `$`; ausente si el reporte se generó sin precio.
- Código: `^FD` inmediatamente posterior a un comando de barcode (`^BC`, `^BE`,
  `^BU`, `^B8`).

Si no encuentra el código, lanza `ParseError`. La GUI lo captura y deja cargar
los campos a mano: un formato de Odoo que cambie no debe dejar la app inservible.

### modules/zpl_builder.py

`etiqueta(nombre, precio, codigo, cal)` arma un `^XA…^XZ` con una fila de 3
columnas, usando la calibración `cal`. `filas(…, n)` concatena n filas.

Calibración (valores medidos el 2026-08-20 contra el troquel real):

| Parámetro | Valor | Qué es |
|---|---|---|
| `ancho_total` | 736 | `^PW`, ancho del cabezal en dots |
| `alto` | 166 | `^LL`, largo de la etiqueta |
| `offsets` | `[0, 256, 508]` | x de cada columna; **no es un paso uniforme** |
| `margen` | 11 | margen interno de cada columna |
| `util` | 190 | ancho disponible para el contenido |
| `oscuridad` | -6 | `^MD`; sin esto las barras engordan y el EAN no lee |

`regla()` genera una fila con marcas y números cada 25 dots, para recalibrar.

### modules/printers.py

`listar()` devuelve los nombres de impresora del sistema.
`imprimir_raw(impresora, datos)` envía bytes crudos.

- **Linux:** `lpstat -a` para listar, `lp -d <impresora> -o raw` para imprimir.
- **Windows:** `winspool.drv` vía `ctypes`. `EnumPrinters` para listar;
  `OpenPrinter` + `StartDocPrinter` con datatype `RAW` + `WritePrinter` para
  imprimir. Evita pywin32, que obligaría a instalar.

El resto del programa no sabe en qué sistema corre.

### config/config.py

Carga `config.json` desde el directorio del ejecutable; si no existe, lo crea
con los valores calibrados por defecto. `guardar(cal)` lo persiste cuando el
usuario edita la calibración.

### main.py

Ventana única:

```
Impresora:  [ combo ▾ ]
[ Cargar TXT… ]   archivo.txt
Nombre:     [ editable                    ]
Precio:     [ $41.000,00 ]  [x] Imprimir con precio
Filas:      [ 1 ▲▼ ]   (cada fila = 3 etiquetas)
                                  [ Imprimir ]
```

Menú **Configuración → Calibración**: offsets por columna, ancho útil, margen,
oscuridad, y botón *Imprimir regla*. Se guarda en `config.json`.

La GUI muestra qué simbología se eligió para el código cargado, y avisa cuando
un código cae a Code 128 pudiendo parecer un EAN: es legible pero no va a
funcionar como código de producto en la caja.

## Manejo de errores

| Situación | Respuesta |
|---|---|
| TXT no reconocido | Aviso + campos manuales, no se cierra |
| Código no entra ni con módulo 1 | Se bloquea la impresión y se explica por qué |
| Verificador inválido en 13 dígitos | Cae a Code 128 con aviso explícito |
| Sin impresoras | Combo vacío y botón deshabilitado |
| Falla el envío | Se muestra el error del sistema tal cual |

## Testing

Los módulos `barcodes`, `zpl_parser` y `zpl_builder` son funciones puras y se
prueban con unittest de la stdlib, sin impresora. Casos mínimos: el EAN-13 real
del anafe, el UPC-A del scunci, un código interno corto, uno con verificador
inválido, y un TXT de Odoo con y sin precio.

`printers` y la GUI se verifican a mano contra la impresora.

## Distribución

GitHub Actions con dos jobs, `windows-latest` y `ubuntu-latest`, que corren
PyInstaller en modo onefile y publican los binarios como artefactos. El de
Windows es el que importa; el de Linux ahorra tener que instalar Python.

## Decisiones y por qué

- **tkinter sobre customtkinter:** cero dependencias pesa más que la estética en
  una herramienta operativa de una sola pantalla.
- **ctypes sobre pywin32:** misma razón; pywin32 rompería el "sin instalación".
- **Parsear el TXT en vez de mandarlo crudo:** es lo único que permite editar el
  nombre, sacar el precio y corregir la simbología.
- **Offsets por columna en vez de un paso uniforme:** medido contra el troquel,
  las tres columnas no están equiespaciadas.
- **Calibración oculta en Configuración:** se toca una vez por rollo, no en el
  uso diario.

## Pendiente

La causa raíz sigue siendo la plantilla de Odoo. Esta app es un traductor entre
ese reporte y la impresora real. Corregir el reporte en Odoo eliminaría la
necesidad de este paso, pero la app sirve igual para reimprimir y ajustar el
nombre.
