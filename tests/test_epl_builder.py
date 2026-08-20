import unittest

from config import config
from modules import epl_builder

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

    def test_traduce_la_oscuridad_a_absoluta(self):
        epl = epl_builder.etiqueta("ANAFE", None, "7794824658488", CAL)
        self.assertIn("D8", epl)
        self.assertNotIn("-6", epl)

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
            self.assertIn("A{},".format(offset + CAL["margen"]), epl)

    def test_con_precio_lo_incluye_tres_veces(self):
        epl = epl_builder.etiqueta("ANAFE", "$41.000,00", "7794824658488", CAL)
        self.assertEqual(epl.count("$41.000,00"), 3)

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
        """Compara propiedades de una columna, no el texto crudo de cada lenguaje.

        Ambos generadores deben elegir la misma simbologia, repetir nombre,
        precio y codigo una vez por columna, y nunca exceder el ancho util
        con el nombre. Este ultimo chequeo es el que habria detectado que
        EPL invadia la columna vecina al no envolver el nombre.
        """
        from modules import zpl_builder, barcodes

        casos = [
            ("ANAFE", "$41.000,00", "7794824658488"),
            ("SCUNCI DE TELA ESTAMPA LETRAS (CV)", None, "677870568079"),
            (
                "PILA ALCALINA AA CHICA PACK DOCE UNIDADES SURTIDAS",
                "$1.234,00",
                "123456",
            ),
        ]
        for nombre, precio, codigo in casos:
            with self.subTest(codigo=codigo):
                x = CAL["offsets"][0]
                comando_zpl, _ = barcodes.elegir_barcode(codigo, CAL["util"])
                tipo_epl_esperado = epl_builder.TIPOS_EPL[comando_zpl]

                bloque_zpl = zpl_builder._columna(x, nombre, precio, codigo, CAL)
                lineas_epl = epl_builder._columna(x, nombre, precio, codigo, CAL)
                bloque_epl = "\n".join(lineas_epl)

                # misma simbologia elegida en los dos
                self.assertIn(comando_zpl, bloque_zpl)
                lineas_b_epl = [l for l in lineas_epl if l.startswith("B")]
                self.assertTrue(
                    any(",{},".format(tipo_epl_esperado) in l for l in lineas_b_epl)
                )

                # el codigo se emite (barcode + texto legible), en los dos
                self.assertEqual(bloque_zpl.count(codigo), 2)
                self.assertEqual(bloque_epl.count(codigo), 2)

                # el precio se emite una vez en la columna, en los dos
                if precio:
                    self.assertEqual(bloque_zpl.count(precio), 1)
                    self.assertEqual(bloque_epl.count(precio), 1)

                # el nombre completo esta presente: ZPL lo envuelve via ^FB en el
                # firmware, asi que viaja entero; EPL lo parte a mano en hasta 2
                # lineas propias.
                self.assertIn(nombre, bloque_zpl)
                lineas_nombre_epl = [
                    l.split('"')[1]
                    for l in lineas_epl
                    if l.startswith("A") and (",6,0," in l or ",24,0," in l)
                ]
                self.assertGreater(len(lineas_nombre_epl), 0)
                self.assertLessEqual(len(lineas_nombre_epl), 2)

                # ningun texto de nombre en EPL excede el ancho util de la columna
                for linea in lineas_nombre_epl:
                    self.assertLessEqual(
                        len(linea) * epl_builder.ANCHO_CARACTER_FUENTE_2, CAL["util"]
                    )


if __name__ == "__main__":
    unittest.main()
