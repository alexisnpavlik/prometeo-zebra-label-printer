# Etiquetas Zebra

Imprime etiquetas de producto en una Zebra GC420t o GT800/GT820 con rollo
3-across, a partir del TXT que exporta Odoo.

Hecho por [Prometeo](https://prometeo.com.ar).

![Interfaz](docs/img/ui-claro.png)

## Por que existe

El reporte de Odoo genera un ZPL para una etiqueta mucho mas ancha que el rollo
real, y usa `^BC` (Code 128) para codigos que son EAN-13 o UPC-A. Enviado tal
cual, el contenido se corta e invade la etiqueta vecina y el codigo no lee como
codigo de producto. Esta app extrae los datos y rearma la etiqueta con la
simbologia correcta y la calibracion del rollo.

## Tema

Claro y oscuro, en **Configuracion → Tema**. Se guarda en `config.json`.

El logo y el icono van embebidos en base64 dentro de `modules/branding.py`: Tk 8.6
lee PNG de forma nativa, asi que no hace falta Pillow ni `--add-data` en PyInstaller.
El icono de ventana y barra de tareas es la llama de Prometeo (`docs/img/icono.ico`
para el ejecutable de Windows).

## Uso

1. Elegir la impresora. La lista muestra el estado de cada una: `conectada` o
   `sin conexion`. Es el estado de la **cola** de impresion, no de la conexion
   fisica: una cola puede figurar conectada con la impresora apagada hasta que
   falla un trabajo. La app preselecciona la ultima usada, salvo que se sepa que
   esta sin conexion.
2. Cargar el TXT de Odoo (o escribir los campos a mano).
3. Ajustar el nombre si hace falta. El precio arranca **destildado** y no se
   tilda solo al cargar un archivo: hay que marcarlo cuando se lo quiere imprimir.
4. Elegir cuantas filas imprimir. Cada fila son 3 etiquetas.

La app recuerda la ultima impresora usada en `config.json`. La primera vez
conviene elegirla a mano: en este sistema hay varias colas para la misma
Zebra fisica y no todas funcionan.

## Simbologia de codigo de barras

El tipo de codigo se elige solo segun el codigo cargado: EAN-13, UPC-A, EAN-8
o Code 128. Un codigo de 13 digitos con digito verificador invalido cae a
Code 128 a proposito, porque no es un EAN valido.

## ZPL y EPL

La app emite los dos lenguajes. Se elige en **Configuracion → Calibracion →
Lenguaje**. El default es ZPL.

No se autodetecta: sin canal bidireccional no hay forma confiable de preguntarle
a la impresora que habla, y el nombre de la cola engana. La GC420t de esta
instalacion se llama `ZTC-GC420t--EPL--2` y sin embargo acepta ZPL.

Si las etiquetas salen en blanco o con texto crudo, el lenguaje esta al reves.

El generador EPL2 nunca se probo contra una impresora real. Ademas no declara
charset: ZPL emite `^CI28` (UTF-8), pero EPL2 no tiene un comando equivalente
en uso aca, asi que los acentos y la ñ pueden salir mal en esa impresora.
Verificar una impresion de prueba antes de usarlo en produccion.

## Calibracion

En **Configuracion → Calibracion**. Se toca solo al cambiar de rollo.

Para recalibrar: **Imprimir regla**, mirar en que numero cae el borde izquierdo
de cada etiqueta, y poner esos numeros en "Offsets de columna". Si algo sale
mal, el boton **Restaurar valores por defecto** vuelve a los valores del rollo
actual.

Valores del rollo actual: ancho 736, alto 166, offsets `0, 256, 508`, margen 11,
ancho util 190.

### Densidad (oscuridad)

La app **no manda ningun comando de densidad**, igual que `zebra_label_printer_odoo`,
que imprime nitido en todas las Zebra. Cada impresora usa la que tiene configurada.

Hasta v1.0.2 habia un campo "Oscuridad" que emitia `^MD` (o `D` en EPL), y los
`config.json` creados por v1.0.0 y v1.0.1 quedaron con `-6`. `^MD` es relativo:
una GT800 viene de fabrica en 10, y con `-6` imprimia en 4, borroso, como sin
tinta. Desde esta version esa clave del `config.json` se ignora.

Si una impresora sale clara, se ajusta en la impresora: la GT800 tiene un selector
fisico de oscuridad (bajo, medio +3, alto +6), o con Zebra Setup Utilities.

### Tamaño de letra

Misma disposicion y fuentes que la app vieja: barras arriba, numero, nombre en
una linea (`^A0N,20,10`) y precio en `^A0N,48,24`. Con letras mas chicas los
trazos quedan de 1 dot y salen borrosos. El nombre se recorta con un punto si no
entra en el ancho util; el precio pierde los centavos en cero.

## Impresoras compatibles

Toda la geometria esta en dots de **203 dpi**: GC420t, GT800, GT820, ZD421-203dpi.

- **GT800/GT820**: aceptan ZPL y EPL y detectan solas cual les llega, asi que
  sirven los dos lenguajes. Soportan UTF-8 (`^CI28`), asi que los acentos salen.
- **300 dpi** (GT830, GT800-300): no estan soportadas. Todo saldria a dos tercios
  del tamaño, y EPL directamente no existe en 300 dpi.

## Descargas

Los ejecutables se publican en
[Releases](https://github.com/alexisnpavlik/prometeo-zebra-label-printer/releases):
`etiquetas-zebra-windows.exe` y `etiquetas-zebra-linux`. No requieren instalar nada.

En Linux hay que darle permiso de ejecucion:

    chmod +x etiquetas-zebra-linux
    ./etiquetas-zebra-linux

### Lanzador en el menu de aplicaciones (Linux)

Para no tener que ir a la carpeta cada vez:

    chmod +x instalar-linux.sh
    ./instalar-linux.sh

Copia el ejecutable a `~/.local/share/etiquetas-zebra/`, instala el icono y crea
la entrada del menu. No pide sudo: todo queda en el home. Busca el ejecutable
junto al script o en `~/Descargas`; tambien se le puede pasar la ruta.

Para sacarlo:

    ./instalar-linux.sh --desinstalar

El ejecutable se instala en su propia carpeta a proposito, porque el
`config.json` se guarda al lado del binario.

Cada tag `vX.Y.Z` que se empuja dispara la compilacion y publica un release nuevo.

## Desarrollo

Solo biblioteca estandar. Sin `pip install` para correrlo:

    python3 main.py
    python3 -m unittest discover -s tests -v

Los ejecutables los compila GitHub Actions con PyInstaller.
