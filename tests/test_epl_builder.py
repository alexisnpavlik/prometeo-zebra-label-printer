import unittest

from config import config
from modules import epl_builder, textos

CAL = dict(config.CALIBRACION_DEFECTO)


class TestEtiqueta(unittest.TestCase):
    def test_limpia_el_buffer_y_manda_imprimir(self):
        epl = epl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertTrue(epl.startswith("N\n"))
        self.assertTrue(epl.strip().endswith("P1"))

    def test_declara_ancho_y_largo(self):
        epl = epl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertIn("q736", epl)
        self.assertIn("Q166,24", epl)

    def test_nunca_emite_densidad(self):
        """En EPL la densidad es absoluta: emitirla pisaria la de la impresora."""
        for cal in (CAL, dict(CAL, oscuridad=-6)):  # -6: config.json de v1.0.0/v1.0.1
            epl = epl_builder.etiqueta("ANAFE", "$41.000,00", "7794824658488", cal)
            for linea in epl.splitlines():
                self.assertFalse(linea.startswith("D"), linea)

    def test_usa_e30_para_un_ean13(self):
        epl = epl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        lineas_b = [l for l in epl.splitlines() if l.startswith("B")]
        self.assertTrue(any(",E30," in l for l in lineas_b))
        self.assertIn('"7794824658488"', epl)

    def test_usa_ua0_para_un_upca(self):
        epl = epl_builder.etiqueta("SCUNCI", None, "677870568079", CAL)
        lineas_b = [l for l in epl.splitlines() if l.startswith("B")]
        self.assertTrue(any(",UA0," in l for l in lineas_b))
        self.assertIn('"677870568079"', epl)

    def test_usa_code128_para_un_codigo_interno(self):
        epl = epl_builder.etiqueta("INTERNO", None, "123456", CAL)
        lineas_b = [l for l in epl.splitlines() if l.startswith("B")]
        self.assertTrue(any(",1," in l for l in lineas_b))
        self.assertIn('"123456"', epl)

    def test_dibuja_las_tres_columnas(self):
        epl = epl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        for offset in CAL["offsets"]:
            self.assertIn("B{},".format(offset + CAL["margen"]), epl)

    def test_con_precio_lo_incluye_tres_veces_sin_centavos_en_cero(self):
        epl = epl_builder.etiqueta("ANAFE", "$41.000,00", "7794824658488", CAL)
        self.assertEqual(epl.count('"$41.000"'), 3)
        self.assertNotIn(",00", epl)

    def test_ningun_texto_se_sale_de_su_columna(self):
        """Las fuentes EPL son de ancho fijo: el ancho real es largo x avance."""
        casos = [
            ("ANAFE 1 HORNALLA ESMALTADO REDUCCION BRONCE", "$41.000,00", "7794824658488"),
            ("PILA", "$1.234.567,50", "123456"),
            ("WWWWWWWWWWWWWWWWWWWWWWWW", "$5", "677870568079"),
        ]
        for nombre, precio, codigo in casos:
            for linea in epl_builder._columna(0, nombre, precio, codigo, CAL):
                if not linea.startswith("A"):
                    continue
                x, _, _, fuente, mult_h = (int(v) for v in linea[1:].split(",")[:5])
                texto = linea.split('"', 1)[1].rsplit('"', 1)[0].replace('\\"', '"')
                fin = x + len(texto) * epl_builder.AVANCE_FUENTE[fuente] * mult_h
                self.assertGreaterEqual(x, CAL["margen"], linea)
                self.assertLessEqual(fin, CAL["margen"] + CAL["util"], linea)

    def test_sin_precio_no_lo_incluye(self):
        epl = epl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertNotIn("$", epl)

    def test_escapa_las_comillas_del_nombre(self):
        epl = epl_builder.etiqueta('ANAFE "O.F"', None, "7794824658488", CAL)
        self.assertIn('\\"O.F\\"', epl)

    def test_barra_invertida_no_se_duplica(self):
        epl = epl_builder.etiqueta("ANAFE\\OTRA", None, "7794824658488", CAL)
        # La barra invertida no es escape en EPL2, debe sobrevivir tal cual
        self.assertIn('ANAFE\\OTRA', epl)
        self.assertNotIn('ANAFE\\\\OTRA', epl)

    def test_codigo_invalido_propaga_el_error(self):
        with self.assertRaises(ValueError):
            epl_builder.etiqueta("X", None, "A" * 60, CAL)


class TestFilas(unittest.TestCase):
    def test_tres_filas_son_tres_bloques(self):
        epl = epl_builder.filas("ANAFE", None, "7794824658488", CAL, 3)
        self.assertEqual(epl.count("P1"), 3)

    def test_cantidad_menor_a_uno_falla(self):
        with self.assertRaises(ValueError):
            epl_builder.filas("ANAFE", None, "7794824658488", CAL, 0)


class TestRegla(unittest.TestCase):
    def test_tiene_marcas_numeradas(self):
        epl = epl_builder.regla(CAL)
        self.assertIn("LO", epl)
        self.assertIn('"25"', epl)


class TestMismaInterfazQueZpl(unittest.TestCase):
    def test_expone_las_mismas_funciones(self):
        from modules import zpl_builder

        for nombre in ("etiqueta", "filas", "regla"):
            self.assertTrue(hasattr(epl_builder, nombre))
            self.assertTrue(hasattr(zpl_builder, nombre))

    def test_generan_columnas_equivalentes(self):
        """Misma simbologia, codigo dos veces (barras + texto) y precio una vez."""
        from modules import zpl_builder, barcodes

        casos = [
            ("ANAFE", "$41.000,00", "7794824658488"),
            ("SCUNCI DE TELA ESTAMPA LETRAS (CV)", None, "677870568079"),
            ("PILA ALCALINA AA CHICA PACK DOCE UNIDADES SURTIDAS", "$1.234,50", "123456"),
        ]
        for nombre, precio, codigo in casos:
            with self.subTest(codigo=codigo):
                x = CAL["offsets"][0]
                comando_zpl, _ = barcodes.elegir_barcode(codigo, CAL["util"])
                tipo_epl_esperado = epl_builder.TIPOS_EPL[comando_zpl]

                bloque_zpl = zpl_builder._columna(x, nombre, precio, codigo, CAL)
                lineas_epl = epl_builder._columna(x, nombre, precio, codigo, CAL)
                bloque_epl = "\n".join(lineas_epl)

                self.assertIn(comando_zpl, bloque_zpl)
                lineas_b_epl = [l for l in lineas_epl if l.startswith("B")]
                self.assertTrue(
                    any(",{},".format(tipo_epl_esperado) in l for l in lineas_b_epl)
                )

                self.assertEqual(bloque_zpl.count(codigo), 2)
                self.assertEqual(bloque_epl.count(codigo), 2)

                if precio:
                    corto = textos.precio_corto(precio)
                    self.assertEqual(bloque_zpl.count(corto), 1)
                    self.assertEqual(bloque_epl.count(corto), 1)


if __name__ == "__main__":
    unittest.main()
