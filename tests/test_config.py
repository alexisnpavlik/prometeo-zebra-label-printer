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
        self.assertEqual(cal["oscuridad"], 0)  # 0 = respetar la de la impresora

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


class TestConfigDirectorioNoEscribible(unittest.TestCase):
    """Simula un directorio de solo lectura, como C:\\Program Files sin permiso."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ruta = os.path.join(self.dir, "config.json")
        os.chmod(self.dir, 0o555)

    def tearDown(self):
        os.chmod(self.dir, 0o755)

    def test_cargar_no_lanza_si_el_directorio_no_es_escribible(self):
        cal = config.cargar(self.ruta)
        self.assertEqual(cal["offsets"], [0, 256, 508])

    def test_cargar_devuelve_los_defectos_sin_poder_crear_el_archivo(self):
        cal = config.cargar(self.ruta)
        self.assertEqual(cal["ancho_total"], 736)
        self.assertFalse(os.path.exists(self.ruta))

    def test_config_no_escribible_devuelve_false(self):
        self.assertFalse(config.config_escribible(self.ruta))

    def test_guardar_propaga_oserror(self):
        with self.assertRaises(OSError):
            config.guardar(config.CALIBRACION_DEFECTO, self.ruta)


class TestConfigEscribible(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ruta = os.path.join(self.dir, "config.json")

    def test_config_escribible_devuelve_true_en_directorio_normal(self):
        self.assertTrue(config.config_escribible(self.ruta))


if __name__ == "__main__":
    unittest.main()
