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
        self.assertIn('"E30"', epl)

    def test_usa_ua0_para_un_upca(self):
        epl = epl_builder.etiqueta("SCUNCI", None, "677870568079", CAL)
        self.assertIn('"UA0"', epl)

    def test_usa_code128_para_un_codigo_interno(self):
        epl = epl_builder.etiqueta("INTERNO", None, "123456", CAL)
        self.assertIn('"1"', epl)

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


if __name__ == "__main__":
    unittest.main()
