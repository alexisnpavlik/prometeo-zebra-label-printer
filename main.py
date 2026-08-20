# main.py
# -*- coding: utf-8 -*-
"""GUI para imprimir etiquetas de producto en la Zebra con rollo 3-across."""

import os
import tkinter as tk
import webbrowser
from tkinter import filedialog, font as tkfont, messagebox, ttk

from config import config
from modules import barcodes, branding, epl_builder, printers, zpl_builder, zpl_parser

GENERADORES = {"zpl": zpl_builder, "epl": epl_builder}

NOMBRES_SIMBOLOGIA = {
    "^BEN": "EAN-13",
    "^BUN": "UPC-A",
    "^B8N": "EAN-8",
    "^BCN": "Code 128",
}

TITULO = "Etiquetas Zebra"


class Aplicacion(tk.Tk):
    """Ventana principal: cargar TXT, editar, imprimir."""

    def __init__(self):
        super().__init__()
        self.title(TITULO)
        self.resizable(False, False)
        self.calibracion = config.cargar()
        self._poner_icono()
        self.estilo = ttk.Style(self)
        self._preparar_fuentes()
        self._aplicar_tema(self.calibracion.get("tema", "claro"))
        self._construir_menu()
        self._construir_widgets()
        self._refrescar_impresoras()
        if not config.config_escribible():
            self._estado("La configuracion no se puede guardar en este directorio", True)

    def _poner_icono(self):
        """Pone la llama de Prometeo como icono de ventana y de barra de tareas.

        Se entregan varios tamanos para que el escritorio elija sin reescalar. Las
        referencias quedan en el objeto porque Tk no retiene las imagenes y el
        icono desapareceria al pasar el recolector.
        """
        self.iconos = [tk.PhotoImage(data=png) for png in branding.marcas()]
        self.iconphoto(True, *self.iconos)

    # ------------------------------------------------------------------ tema

    def _preparar_fuentes(self):
        """Deriva las fuentes de la app de la fuente por defecto del sistema."""
        base = tkfont.nametofont("TkDefaultFont")
        familia = base.cget("family")
        self.fuente_titulo = tkfont.Font(family=familia, size=15, weight="bold")
        self.fuente_seccion = tkfont.Font(family=familia, size=9, weight="bold")
        self.fuente_normal = tkfont.Font(family=familia, size=10)
        self.fuente_chica = tkfont.Font(family=familia, size=9)
        self.fuente_boton = tkfont.Font(family=familia, size=10, weight="bold")

    def _aplicar_tema(self, tema):
        """Configura los estilos ttk con la paleta del tema pedido."""
        self.tema = tema if tema in branding.PALETAS else "claro"
        self.paleta = branding.paleta(self.tema)
        color = self.paleta

        self.estilo.theme_use("clam")
        self.configure(background=color["fondo"])

        self.estilo.configure(".", font=self.fuente_normal)
        self.estilo.configure("TFrame", background=color["fondo"])
        self.estilo.configure("Tarjeta.TFrame", background=color["superficie"])
        self.estilo.configure(
            "TLabel", background=color["fondo"], foreground=color["texto"]
        )
        self.estilo.configure(
            "Tarjeta.TLabel", background=color["superficie"], foreground=color["texto"]
        )
        self.estilo.configure(
            "Titulo.TLabel",
            background=color["fondo"],
            foreground=color["texto"],
            font=self.fuente_titulo,
        )
        self.estilo.configure(
            "Seccion.TLabel",
            background=color["fondo"],
            foreground=color["texto_suave"],
            font=self.fuente_seccion,
        )
        self.estilo.configure(
            "Suave.TLabel",
            background=color["fondo"],
            foreground=color["texto_suave"],
            font=self.fuente_chica,
        )
        self.estilo.configure(
            "Enlace.TLabel",
            background=color["fondo"],
            foreground=color["acento"],
            font=self.fuente_chica,
        )
        self.estilo.configure(
            "Alerta.TLabel",
            background=color["fondo"],
            foreground=color["acento_hover"],
            font=self.fuente_chica,
        )

        self.estilo.configure(
            "TEntry",
            fieldbackground=color["campo"],
            foreground=color["texto"],
            bordercolor=color["borde"],
            lightcolor=color["borde"],
            darkcolor=color["borde"],
            insertcolor=color["texto"],
            padding=5,
        )
        self.estilo.map(
            "TEntry", bordercolor=[("focus", color["acento"])]
        )
        self.estilo.configure(
            "TCombobox",
            fieldbackground=color["campo"],
            background=color["campo"],
            foreground=color["texto"],
            bordercolor=color["borde"],
            arrowcolor=color["texto_suave"],
            padding=5,
        )
        # sin esto el combo readonly se dibuja siempre con el fondo de "seleccionado"
        self.estilo.map(
            "TCombobox",
            fieldbackground=[("readonly", color["campo"])],
            selectbackground=[("readonly", color["campo"])],
            selectforeground=[("readonly", color["texto"])],
            bordercolor=[("focus", color["acento"])],
            arrowcolor=[("active", color["acento"])],
        )
        self.option_add("*TCombobox*Listbox.background", color["campo"])
        self.option_add("*TCombobox*Listbox.foreground", color["texto"])
        self.option_add("*TCombobox*Listbox.selectBackground", color["acento"])
        self.option_add("*TCombobox*Listbox.selectForeground", color["acento_texto"])
        self.estilo.configure(
            "TSpinbox",
            fieldbackground=color["campo"],
            foreground=color["texto"],
            bordercolor=color["borde"],
            arrowcolor=color["texto_suave"],
            padding=4,
        )
        self.estilo.configure(
            "TCheckbutton",
            background=color["fondo"],
            foreground=color["texto"],
            indicatorbackground=color["campo"],
            indicatorforeground=color["acento_texto"],
            bordercolor=color["borde"],
            focuscolor=color["fondo"],
            padding=4,
        )
        self.estilo.map(
            "TCheckbutton",
            indicatorbackground=[
                ("selected", color["acento"]),
                ("active", color["campo"]),
            ],
            bordercolor=[("selected", color["acento"])],
        )
        self.estilo.configure("TSeparator", background=color["borde"])

        self.estilo.configure(
            "TButton",
            background=color["superficie"],
            foreground=color["texto"],
            bordercolor=color["borde"],
            focuscolor=color["acento"],
            padding=(12, 7),
        )
        self.estilo.map(
            "TButton",
            background=[("active", color["borde"])],
            bordercolor=[("active", color["acento"])],
        )
        self.estilo.configure(
            "Acento.TButton",
            background=color["acento"],
            foreground=color["acento_texto"],
            bordercolor=color["acento"],
            font=self.fuente_boton,
            padding=(22, 9),
        )
        self.estilo.map(
            "Acento.TButton",
            background=[("active", color["acento_hover"]), ("disabled", color["borde"])],
            foreground=[("disabled", color["texto_suave"])],
        )

    def _cambiar_tema(self, tema):
        """Cambia el tema en caliente y lo persiste."""
        self.logo = tk.PhotoImage(data=branding.logo(tema)).subsample(2)
        self._aplicar_tema(tema)
        self.marca.configure(image=self.logo)
        self.calibracion["tema"] = self.tema
        self._construir_menu()
        self._pintar_estado()
        self._actualizar_simbologia()
        try:
            config.guardar(self.calibracion)
        except OSError:
            pass  # preferencia visual: que no se recuerde no debe interrumpir

    # ------------------------------------------------------------- interfaz

    def _colores_menu(self):
        """Opciones de color para los tk.Menu, que no toman el tema de ttk."""
        color = self.paleta
        return {
            "background": color["superficie"],
            "foreground": color["texto"],
            "activebackground": color["acento"],
            "activeforeground": color["acento_texto"],
            "borderwidth": 0,
        }

    def _construir_menu(self):
        """Menu con la calibracion y el tema, fuera del uso diario."""
        colores = self._colores_menu()
        barra = tk.Menu(self, **colores)
        configuracion = tk.Menu(barra, tearoff=0, **colores)
        configuracion.add_command(label="Calibracion...", command=self._abrir_calibracion)
        configuracion.add_separator()
        configuracion.add_command(label="Imprimir regla", command=self._imprimir_regla)
        configuracion.add_separator()

        self.tema_elegido = tk.StringVar(value=self.tema)
        tema = tk.Menu(configuracion, tearoff=0, **colores)
        for clave, etiqueta in (("claro", "Claro"), ("oscuro", "Oscuro")):
            tema.add_radiobutton(
                label=etiqueta,
                value=clave,
                variable=self.tema_elegido,
                command=lambda c=clave: self._cambiar_tema(c),
            )
        configuracion.add_cascade(label="Tema", menu=tema)
        barra.add_cascade(label="Configuracion", menu=configuracion)
        self.config(menu=barra)

    def _construir_widgets(self):
        """Arma los controles de la pantalla principal."""
        marco = ttk.Frame(self, padding=(24, 18, 24, 14))
        marco.grid(row=0, column=0, sticky="nsew")
        marco.columnconfigure(1, weight=1)

        self._construir_cabecera(marco)

        fila = 1
        fila = self._seccion(marco, fila, "IMPRESORA")

        self.impresora = ttk.Combobox(marco, state="readonly", width=34)
        self.impresora.grid(row=fila, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(marco, text="Refrescar", command=self._refrescar_impresoras).grid(
            row=fila, column=2, sticky="e", padx=(10, 0), pady=(0, 4)
        )
        fila += 1

        fila = self._seccion(marco, fila, "PRODUCTO")

        ttk.Button(marco, text="Cargar TXT...", command=self._cargar_txt).grid(
            row=fila, column=0, sticky="w"
        )
        self.archivo = ttk.Label(
            marco, text="ningun archivo cargado", style="Suave.TLabel"
        )
        self.archivo.grid(row=fila, column=1, columnspan=2, sticky="w", padx=(12, 0))
        fila += 1

        ttk.Label(marco, text="Nombre").grid(row=fila, column=0, sticky="w", pady=(12, 2))
        fila += 1
        self.nombre = ttk.Entry(marco, font=self.fuente_normal)
        self.nombre.grid(row=fila, column=0, columnspan=3, sticky="ew")
        fila += 1

        ttk.Label(marco, text="Codigo").grid(row=fila, column=0, sticky="w", pady=(12, 2))
        ttk.Label(marco, text="Precio").grid(
            row=fila, column=1, sticky="w", padx=(12, 0), pady=(12, 2)
        )
        fila += 1

        self.codigo = ttk.Entry(marco, width=20, font=self.fuente_normal)
        self.codigo.grid(row=fila, column=0, sticky="ew")
        self.codigo.bind("<KeyRelease>", lambda _evento: self._actualizar_simbologia())
        self.precio = ttk.Entry(marco, width=16, font=self.fuente_normal)
        self.precio.grid(row=fila, column=1, sticky="w", padx=(12, 0))
        self.con_precio = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            marco, text="Imprimir con precio", variable=self.con_precio
        ).grid(row=fila, column=2, sticky="w", padx=(12, 0))
        fila += 1

        self.simbologia = ttk.Label(marco, text="", style="Suave.TLabel")
        self.simbologia.grid(row=fila, column=0, columnspan=3, sticky="w", pady=(6, 0))
        fila += 1

        fila = self._seccion(marco, fila, "IMPRESION")

        self.filas = tk.IntVar(value=1)
        ttk.Spinbox(
            marco, from_=1, to=99, width=5, textvariable=self.filas,
            font=self.fuente_normal,
        ).grid(row=fila, column=0, sticky="w")
        ttk.Label(
            marco, text="filas   ·   cada fila son 3 etiquetas", style="Suave.TLabel"
        ).grid(row=fila, column=1, sticky="w", padx=(12, 0))
        self.boton_imprimir = ttk.Button(
            marco, text="Imprimir", style="Acento.TButton", command=self._imprimir
        )
        self.boton_imprimir.grid(row=fila, column=2, sticky="e", padx=(10, 0))
        fila += 1

        ttk.Separator(marco, orient="horizontal").grid(
            row=fila, column=0, columnspan=3, sticky="ew", pady=(18, 8)
        )
        fila += 1

        self.estado = ttk.Label(marco, text="Listo", style="Suave.TLabel")
        self.estado.grid(row=fila, column=0, columnspan=3, sticky="w")
        self.estado_alerta = False

    def _construir_cabecera(self, marco):
        """Logo de Prometeo, nombre de la app y enlace al sitio."""
        cabecera = ttk.Frame(marco)
        cabecera.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        cabecera.columnconfigure(1, weight=1)

        self.logo = tk.PhotoImage(data=branding.logo(self.tema)).subsample(2)
        self.marca = ttk.Label(cabecera, image=self.logo)
        self.marca.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 14))

        ttk.Label(cabecera, text=TITULO, style="Titulo.TLabel").grid(
            row=0, column=1, sticky="sw"
        )
        enlace = ttk.Label(cabecera, text=branding.SITIO, style="Enlace.TLabel")
        enlace.grid(row=1, column=1, sticky="nw")
        enlace.bind("<Button-1>", lambda _evento: webbrowser.open(branding.URL))
        enlace.configure(cursor="hand2")

        ttk.Separator(marco, orient="horizontal").grid(
            row=0, column=0, columnspan=3, sticky="sew", pady=(0, 0)
        )

    def _seccion(self, marco, fila, texto):
        """Dibuja un encabezado de seccion y devuelve la fila siguiente."""
        ttk.Label(marco, text=texto, style="Seccion.TLabel").grid(
            row=fila, column=0, columnspan=3, sticky="w", pady=(16, 6)
        )
        return fila + 1

    def _estado(self, texto, alerta=False):
        """Escribe un mensaje en la barra de estado."""
        self.estado_alerta = alerta
        self.estado.configure(text=texto)
        self._pintar_estado()

    def _pintar_estado(self):
        """Aplica el color que corresponde al estado actual."""
        self.estado.configure(
            style="Alerta.TLabel" if self.estado_alerta else "Suave.TLabel"
        )

    # -------------------------------------------------------------- acciones

    def _refrescar_impresoras(self):
        """Recarga la lista de impresoras del sistema."""
        disponibles = printers.listar()
        self.impresora["values"] = disponibles
        if disponibles:
            recordada = self.calibracion.get("impresora", "")
            if recordada and recordada in disponibles:
                self.impresora.set(recordada)
            else:
                preferida = [n for n in disponibles if "GC420" in n or "ZTC" in n]
                self.impresora.set(preferida[0] if preferida else disponibles[0])
            self.boton_imprimir.state(["!disabled"])
        else:
            self.impresora.set("")
            self.boton_imprimir.state(["disabled"])
            self._estado("No se encontro ninguna impresora", True)

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
        try:
            datos = zpl_parser.parsear(texto)
        except zpl_parser.ParseError as error:
            messagebox.showwarning(
                "No se pudo leer el archivo",
                "{}\n\nCargá los campos a mano.".format(error),
            )
            self._estado("No se pudo leer el archivo: cargá los campos a mano", True)
            return
        self.archivo.configure(text=os.path.basename(ruta))
        self._completar(datos)
        self._estado("Cargado {}".format(os.path.basename(ruta)))

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
            self.simbologia.configure(text="", style="Suave.TLabel")
            return
        try:
            comando, modulo = barcodes.elegir_barcode(codigo, self.calibracion["util"])
        except ValueError as error:
            self.simbologia.configure(text=str(error)[:70], style="Alerta.TLabel")
            return
        nombre = NOMBRES_SIMBOLOGIA.get(comando, comando)
        if comando == "^BCN" and codigo.isdigit() and len(codigo) in (8, 12, 13):
            self.simbologia.configure(
                text="{} — verificador invalido, no leera como EAN".format(nombre),
                style="Alerta.TLabel",
            )
        else:
            self.simbologia.configure(
                text="{} · modulo {}".format(nombre, modulo), style="Suave.TLabel"
            )

    def _generador(self):
        """Devuelve el modulo generador segun el lenguaje configurado."""
        return GENERADORES.get(self.calibracion["lenguaje"], zpl_builder)

    def _imprimir(self):
        """Arma la etiqueta con los campos actuales y la manda a la impresora."""
        nombre = self.nombre.get().strip()
        codigo = self.codigo.get().strip()
        precio = self.precio.get().strip() if self.con_precio.get() else None
        if not codigo:
            messagebox.showerror("Falta el codigo", "Cargá el codigo del producto.")
            return
        try:
            cantidad = self.filas.get()
        except tk.TclError:
            messagebox.showerror(
                "Cantidad invalida", "Cargá una cantidad de filas valida."
            )
            return
        try:
            etiqueta = self._generador().filas(
                nombre, precio, codigo, self.calibracion, cantidad
            )
        except ValueError as error:
            messagebox.showerror("No se puede imprimir", str(error))
            return
        if self._enviar(etiqueta):
            self._estado(
                "Enviadas {} filas · {} etiquetas".format(cantidad, cantidad * 3)
            )

    def _imprimir_regla(self):
        """Imprime la regla de calibracion en el lenguaje configurado."""
        if self._enviar(self._generador().regla(self.calibracion)):
            self._estado("Regla de calibracion enviada")

    def _enviar(self, datos):
        """Envia los datos crudos. Devuelve True si salio, False si fallo."""
        impresora = self.impresora.get()
        try:
            printers.imprimir_raw(impresora, datos)
        except (printers.ErrorImpresion, ValueError) as error:
            messagebox.showerror("Error al imprimir", str(error))
            self._estado("Fallo la impresion: {}".format(error), True)
            return False
        if self.calibracion.get("impresora") != impresora:
            self.calibracion["impresora"] = impresora
            try:
                config.guardar(self.calibracion)
            except OSError:
                pass  # accion de fondo: que no se recuerde no debe interrumpir
        return True

    # ----------------------------------------------------------- calibracion

    def _validar_calibracion(self, datos):
        """Devuelve un mensaje de error si `datos` rompe la geometria, o None si esta bien."""
        if datos["ancho_total"] <= 0:
            return "El ancho total tiene que ser mayor que cero."
        if datos["alto"] <= 0:
            return "El alto tiene que ser mayor que cero."
        if datos["util"] <= 0:
            return "El ancho util tiene que ser mayor que cero."
        if datos["margen"] < 0:
            return "El margen no puede ser negativo."
        if datos["margen"] + datos["util"] > datos["ancho_total"]:
            return "Margen + ancho util no puede superar el ancho total."
        for offset in datos["offsets"]:
            if offset < 0:
                return "Los offsets no pueden ser negativos."
            if offset + datos["margen"] + datos["util"] > datos["ancho_total"]:
                return "Algun offset + margen + ancho util supera el ancho total."
        if not -30 <= datos["oscuridad"] <= 30:
            return "La oscuridad tiene que estar entre -30 y 30."
        return None

    def _abrir_calibracion(self):
        """Ventana de calibracion, con los valores del config.json."""
        ventana = tk.Toplevel(self)
        ventana.title("Calibracion")
        ventana.resizable(False, False)
        ventana.configure(background=self.paleta["fondo"])
        marco = ttk.Frame(ventana, padding=20)
        marco.grid(row=0, column=0)

        ttk.Label(marco, text="CALIBRACION DEL ROLLO", style="Seccion.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        campos = {}
        etiquetas = [
            ("ancho_total", "Ancho total (^PW)"),
            ("alto", "Alto (^LL)"),
            ("margen", "Margen interno"),
            ("util", "Ancho util"),
            ("oscuridad", "Oscuridad (^MD)"),
        ]
        for indice, (clave, texto) in enumerate(etiquetas):
            fila = indice + 1
            ttk.Label(marco, text=texto).grid(row=fila, column=0, sticky="w", pady=3)
            entrada = ttk.Entry(marco, width=12, font=self.fuente_normal)
            entrada.insert(0, str(self.calibracion[clave]))
            entrada.grid(row=fila, column=1, sticky="e", padx=(20, 0), pady=3)
            campos[clave] = entrada

        base = len(etiquetas) + 1
        ttk.Label(marco, text="Offsets de columna").grid(
            row=base, column=0, sticky="w", pady=3
        )
        offsets = ttk.Entry(marco, width=12, font=self.fuente_normal)
        offsets.insert(0, ", ".join(str(x) for x in self.calibracion["offsets"]))
        offsets.grid(row=base, column=1, sticky="e", padx=(20, 0), pady=3)

        ttk.Label(marco, text="Lenguaje").grid(row=base + 1, column=0, sticky="w", pady=3)
        lenguaje = ttk.Combobox(marco, width=10, state="readonly", values=["zpl", "epl"])
        lenguaje.set(self.calibracion["lenguaje"])
        lenguaje.grid(row=base + 1, column=1, sticky="e", padx=(20, 0), pady=3)

        def _refrescar_campos(datos):
            """Vuelca `datos` en los entries de la ventana de calibracion."""
            for clave, entrada in campos.items():
                entrada.delete(0, tk.END)
                entrada.insert(0, str(datos[clave]))
            offsets.delete(0, tk.END)
            offsets.insert(0, ", ".join(str(x) for x in datos["offsets"]))
            lenguaje.set(datos["lenguaje"])

        def restaurar():
            """Repone los valores por defecto en los campos, sin guardar aun."""
            _refrescar_campos(config.CALIBRACION_DEFECTO)

        def guardar():
            """Valida y persiste la calibracion; no guarda nada si algo es invalido."""
            try:
                nueva = {c: int(e.get()) for c, e in campos.items()}
                nueva["offsets"] = [int(x) for x in offsets.get().split(",")]
                nueva["lenguaje"] = lenguaje.get()
            except ValueError:
                messagebox.showerror(
                    "Valores invalidos", "Todos los campos deben ser numeros enteros."
                )
                return
            if len(nueva["offsets"]) < 1:
                messagebox.showerror("Offsets invalidos", "Poné al menos un offset.")
                return
            error = self._validar_calibracion(nueva)
            if error:
                messagebox.showerror("Valores invalidos", error)
                return
            self.calibracion.update(nueva)
            try:
                config.guardar(self.calibracion)
            except OSError as error:
                messagebox.showwarning(
                    "No se pudo guardar",
                    "La calibracion no se pudo persistir ({}).\n\n"
                    "El cambio vale solo para esta sesion.".format(error),
                )
            self._actualizar_simbologia()
            self._estado("Calibracion actualizada")
            ventana.destroy()

        ttk.Separator(marco, orient="horizontal").grid(
            row=base + 2, column=0, columnspan=2, sticky="ew", pady=16
        )
        acciones = ttk.Frame(marco)
        acciones.grid(row=base + 3, column=0, columnspan=2, sticky="ew")
        acciones.columnconfigure(0, weight=1)
        ttk.Button(acciones, text="Imprimir regla", command=self._imprimir_regla).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(acciones, text="Guardar", style="Acento.TButton", command=guardar).grid(
            row=0, column=1, sticky="e", padx=(10, 0)
        )
        ttk.Button(
            marco, text="Restaurar valores por defecto", command=restaurar
        ).grid(row=base + 4, column=0, columnspan=2, sticky="w", pady=(10, 0))


def main():
    """Punto de entrada."""
    Aplicacion().mainloop()


if __name__ == "__main__":
    main()
