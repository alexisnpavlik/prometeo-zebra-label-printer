# tests/test_config.py
import json
import os
import tempfile
import unittest

from config import config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ruta = os.path.join(self.dir, "config.json")

    def test_crea_el_archivo_si_no_existe(self):
        cal = config.cargar(self.ruta)
        self.assertTrue(os.path.exists(self.ruta))
        self.assertEqual(cal["offsets"], [0, 256, 508])

    def test_devuelve_los_valores_calibrados_por_defecto(self):
        cal = config.cargar(self.ruta)
        self.assertEqual(cal["ancho_total"], 736)
        self.assertEqual(cal["alto"], 166)
        self.assertEqual(cal["oscuridad"], -6)

    def test_el_lenguaje_por_defecto_es_zpl(self):
        self.assertEqual(config.cargar(self.ruta)["lenguaje"], "zpl")

    def test_guardar_y_volver_a_cargar(self):
        cal = config.cargar(self.ruta)
        cal["offsets"] = [0, 250, 500]
        config.guardar(cal, self.ruta)
        self.assertEqual(config.cargar(self.ruta)["offsets"], [0, 250, 500])

    def test_json_corrupto_vuelve_a_los_defectos(self):
        with open(self.ruta, "w") as f:
            f.write("{ esto no es json")
        self.assertEqual(config.cargar(self.ruta)["offsets"], [0, 256, 508])

    def test_completa_claves_faltantes(self):
        with open(self.ruta, "w") as f:
            json.dump({"offsets": [0, 1, 2]}, f)
        cal = config.cargar(self.ruta)
        self.assertEqual(cal["offsets"], [0, 1, 2])
        self.assertEqual(cal["margen"], 11)

    def test_no_mutates_default_offsets_in_place(self):
        cal = config.cargar(self.ruta)
        cal["offsets"][0] = 999
        self.assertEqual(config.CALIBRACION_DEFECTO["offsets"], [0, 256, 508])

    def test_loaded_offsets_are_different_object(self):
        cal1 = config.cargar(self.ruta)
        cal2 = config.cargar(self.ruta)
        self.assertIsNot(cal1["offsets"], cal2["offsets"])


if __name__ == "__main__":
    unittest.main()
