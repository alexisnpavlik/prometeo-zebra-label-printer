# -*- coding: utf-8 -*-
import re
import unittest

from config import config
from modules import textos, zpl_builder

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

    def test_incluye_ancho_y_alto(self):
        zpl = zpl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertIn("^PW736", zpl)
        self.assertIn("^LL166", zpl)

    def test_nunca_emite_md(self):
        """Como la app vieja: la densidad la pone cada impresora, no la app."""
        zpl = zpl_builder.etiqueta("ANAFE", "$41.000,00", "7794824658488", CAL)
        self.assertNotIn("^MD", zpl)

    def test_un_config_viejo_con_oscuridad_tampoco_emite_md(self):
        """Los config.json de v1.0.0/v1.0.1 quedaron con oscuridad -6."""
        zpl = zpl_builder.etiqueta("ANAFE", None, "7794824658488", dict(CAL, oscuridad=-6))
        self.assertNotIn("^MD", zpl)

    def test_usa_las_fuentes_de_la_app_vieja(self):
        zpl = zpl_builder.etiqueta("ANAFE", "$41.000,00", "7794824658488", CAL)
        self.assertIn("^A0N,20,10^FB190,1,0,C,0^FH\\^FDANAFE^FS", zpl)
        self.assertIn("^A0N,48,24^FB190,1,0,C,0^FH\\^FD$41.000^FS", zpl)

    def test_precio_largo_va_en_la_fuente_chica(self):
        zpl = zpl_builder.etiqueta("ANAFE", "$1.234.567,50", "7794824658488", CAL)
        self.assertIn("^A0N,40,16^FB190,1,0,C,0^FH\\^FD$1.234.567,50^FS", zpl)

    def test_con_precio_lo_incluye_sin_centavos_en_cero(self):
        zpl = zpl_builder.etiqueta("ANAFE", "$41.000,00", "7794824658488", CAL)
        self.assertEqual(zpl.count("^FD$41.000^FS"), 3)
        self.assertNotIn(",00", zpl)

    def test_sin_precio_no_lo_incluye(self):
        zpl = zpl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertNotIn("$", zpl)

    def test_nombre_largo_se_recorta_para_no_pisarse(self):
        """^FB de una linea encima el texto que no entra: hay que cortarlo antes."""
        nombre = "ANAFE 1 HORNALLA ESMALTADO REDUCCION BRONCE CONOMETAL"
        zpl = zpl_builder.etiqueta(nombre, "$500", "7794824658488", CAL)
        self.assertNotIn(nombre, zpl)
        recortado = re.search(r"\^A0N,20,10\^FB190,1,0,C,0\^FH\\\^FD(.*?)\^FS", zpl).group(1)
        self.assertTrue(recortado.endswith("."))
        self.assertTrue(nombre.startswith(recortado[:-1]))
        self.assertLessEqual(textos.ancho(recortado, textos.ancho_a0_nombre), CAL["util"])

    def test_sin_precio_numero_y_nombre_van_grandes(self):
        zpl = zpl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertIn("^A0N,28,16^FB190,1,0,C,0^FH\\^FD7794824658488^FS", zpl)
        self.assertIn("^A0N,28,13^FB190,1,0,C,0^FH\\^FDANAFE^FS", zpl)
        self.assertNotIn("^A0N,20,10", zpl)

    def test_sin_precio_el_nombre_largo_ocupa_dos_lineas(self):
        nombre = '"OFERTA FINAL" CUCHILLO ACERO INOXIDABLE MANGO MADERA'
        bloque = zpl_builder._columna(0, nombre, None, "7794658976179", CAL)
        lineas = re.findall(r"\^A0N,28,13\^FB190,1,0,C,0\^FH\\\^FD(.*?)\^FS", bloque)
        self.assertEqual(len(lineas), 2)
        self.assertEqual(lineas[0], '"OFERTA FINAL" CUCHILLO')
        self.assertTrue(lineas[1].endswith("."))
        for linea in lineas:
            self.assertLessEqual(textos.ancho(linea, textos.ancho_a0(13)), CAL["util"])

    def test_sin_precio_un_codigo_largo_vuelve_a_la_fuente_chica(self):
        codigo = "123456789012345678901234"
        bloque = zpl_builder._columna(0, "PILA", None, codigo, CAL)
        self.assertIn("^A0N,18,10^FB190,1,0,C,0^FH\\^FD{}^FS".format(codigo), bloque)

    def test_el_margen_superior_baja_cada_campo_sin_tocar_lh(self):
        """^LH queda grabado en la impresora: el margen va sumado a cada ^FO."""
        for precio in (None, "$500"):
            with self.subTest(precio=precio):
                sin = zpl_builder.etiqueta("ANAFE", precio, "7794824658488", dict(CAL, margen_superior=0))
                con = zpl_builder.etiqueta("ANAFE", precio, "7794824658488", dict(CAL, margen_superior=12))
                self.assertIn("^LH0,0", con)
                ys_sin = [int(y) for y in re.findall(r"\^FO\d+,(\d+)", sin)]
                ys_con = [int(y) for y in re.findall(r"\^FO\d+,(\d+)", con)]
                self.assertEqual(ys_con, [y + 12 for y in ys_sin])

    def test_con_el_margen_por_defecto_todo_entra_en_el_alto(self):
        bajada = CAL["margen_superior"]
        fin_con_precio = zpl_builder.Y_PRECIO + 48
        fin_sin_precio = zpl_builder.Y_NOMBRE_GRANDE + zpl_builder.ALTO_NOMBRE_GRANDE * zpl_builder.LINEAS_NOMBRE_GRANDE
        self.assertLessEqual(bajada + max(fin_con_precio, fin_sin_precio), CAL["alto"])

    def test_sin_precio_los_bloques_grandes_entran_en_la_etiqueta(self):
        self.assertLessEqual(zpl_builder.Y_NUMERO + zpl_builder.ALTO_NUMERO_GRANDE, zpl_builder.Y_NOMBRE_GRANDE)
        fin_nombre = zpl_builder.Y_NOMBRE_GRANDE + zpl_builder.ALTO_NOMBRE_GRANDE * zpl_builder.LINEAS_NOMBRE_GRANDE
        self.assertLessEqual(fin_nombre, 160)

    def test_los_bloques_no_se_pisan_y_entran_en_la_etiqueta(self):
        """Barras, numero, nombre y precio, de arriba hacia abajo y sin solaparse."""
        fin_barras = zpl_builder.Y_BARRAS + zpl_builder.ALTO_BARRAS + zpl_builder.BAJADA_GUARDAS
        self.assertLess(fin_barras, zpl_builder.Y_NUMERO)
        self.assertLessEqual(zpl_builder.Y_NUMERO + zpl_builder.ALTO_NUMERO, zpl_builder.Y_NOMBRE)
        self.assertLessEqual(zpl_builder.Y_NOMBRE + 20, zpl_builder.Y_PRECIO)
        self.assertLessEqual(zpl_builder.Y_PRECIO + 48, 160)  # 20 mm a 203 dpi

    def test_codigo_invalido_propaga_el_error(self):
        with self.assertRaises(ValueError):
            zpl_builder.etiqueta("X", None, "A" * 60, CAL)


class TestEscapar(unittest.TestCase):
    def test_escapa_el_guion_bajo_para_que_no_se_lea_como_hex(self):
        # Con ^FH activo, "_5E" en el texto se leeria como el caracter que
        # codifica ese hex si el guion bajo original no se escapa primero.
        escapado = zpl_builder._escapar("SKU_5E123")
        self.assertNotIn("SKU_5E123", escapado)
        self.assertIn("_5F5E123", escapado)

    def test_escapa_circunflejo_virgulilla_y_guion_bajo_en_orden(self):
        escapado = zpl_builder._escapar("A^B~C_D")
        self.assertEqual(escapado, "A_5EB_7EC_5FD")

    def test_nombre_con_guion_bajo_no_genera_secuencia_hex_ambigua(self):
        zpl = zpl_builder.etiqueta("SKU_5E123", None, "7794824658488", CAL)
        # El literal original con guion bajo sin escapar no debe sobrevivir:
        # si aparece "SKU_5E123" tal cual, el firmware lo leeria como
        # SKU + el caracter 0x5E (o sea "^"), no como el texto real.
        self.assertNotIn("SKU_5E123", zpl)
        self.assertIn("SKU_5F5E123", zpl)


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
