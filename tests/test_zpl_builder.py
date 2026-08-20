# -*- coding: utf-8 -*-
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
