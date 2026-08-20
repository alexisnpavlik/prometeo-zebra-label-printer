# main.py
# -*- coding: utf-8 -*-
"""GUI para imprimir etiquetas de producto en la Zebra con rollo 3-across."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from config import config
from modules import barcodes, epl_builder, printers, zpl_builder, zpl_parser

GENERADORES = {"zpl": zpl_builder, "epl": epl_builder}

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
            etiqueta = self._generador().filas(
                nombre, precio, codigo, self.calibracion, self.filas.get()
            )
        except ValueError as error:
            messagebox.showerror("No se puede imprimir", str(error))
            return
        self._enviar(etiqueta)

    def _imprimir_regla(self):
        """Imprime la regla de calibracion en el lenguaje configurado."""
        self._enviar(self._generador().regla(self.calibracion))

    def _enviar(self, datos):
        """Envia los datos crudos, mostrando el error del sistema si falla."""
        try:
            printers.imprimir_raw(self.impresora.get(), datos)
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

        ttk.Label(marco, text="Lenguaje").grid(
            row=len(etiquetas) + 1, column=0, sticky="w", pady=2
        )
        lenguaje = ttk.Combobox(
            marco, width=8, state="readonly", values=["zpl", "epl"]
        )
        lenguaje.set(self.calibracion["lenguaje"])
        lenguaje.grid(row=len(etiquetas) + 1, column=1, sticky="w", pady=2)

        def guardar():
            """Valida y persiste la calibracion."""
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
            self.calibracion.update(nueva)
            config.guardar(self.calibracion)
            self._actualizar_simbologia()
            ventana.destroy()

        ttk.Button(marco, text="Imprimir regla", command=self._imprimir_regla).grid(
            row=len(etiquetas) + 2, column=0, pady=10, sticky="w"
        )
        ttk.Button(marco, text="Guardar", command=guardar).grid(
            row=len(etiquetas) + 2, column=1, pady=10, sticky="e"
        )


def main():
    """Punto de entrada."""
    Aplicacion().mainloop()


if __name__ == "__main__":
    main()
