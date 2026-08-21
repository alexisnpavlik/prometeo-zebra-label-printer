# Etiquetas Zebra

Imprime etiquetas de producto en una Zebra GC420t con rollo 3-across, a partir
del TXT que exporta Odoo.

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
ancho util 190, oscuridad 0.

### Oscuridad

Por defecto es **0: la app no toca la densidad** y cada impresora usa la que tiene
configurada. Es lo correcto, porque el ajuste no es portable entre impresoras:

- En ZPL, `^MD` es **relativo** a la densidad de la impresora. Un `-6` que queda
  bien en una configurada en 15 deja en 4 a una configurada en 10: sale borrosa,
  como si le faltara tinta.
- En EPL2 el comando `D` es **absoluto** y pisa directamente la calibracion de la
  impresora.

Solo conviene tocarla cuando una impresora concreta imprime mal por su propia
configuracion. En la GC420t de esta instalacion, con densidad 15 de fabrica, las
barras engordaban y el EAN no leia; ahi `-6` lo resolvia. Ese valor **vale para esa
impresora**, no para todas.

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
