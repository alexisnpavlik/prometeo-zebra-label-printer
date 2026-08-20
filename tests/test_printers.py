# tests/test_printers.py
import unittest
from unittest import mock

from modules import printers


class TestListarLinux(unittest.TestCase):
    def test_parsea_la_salida_de_lpstat(self):
        salida = "QL-800\nZTC-GC420t\n"
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "check_output", return_value=salida):
                self.assertEqual(printers.listar(), ["QL-800", "ZTC-GC420t"])

    def test_sin_cups_devuelve_lista_vacia(self):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "check_output", side_effect=OSError):
                self.assertEqual(printers.listar(), [])


class TestListarWindowsManejoDeErrores(unittest.TestCase):
    def test_error_real_no_se_confunde_con_lista_vacia(self):
        with mock.patch.object(printers, "_es_windows", return_value=True):
            with mock.patch.object(
                printers, "_listar_windows", side_effect=printers.ErrorImpresion("boom")
            ):
                resultado = printers.listar()
        self.assertEqual(resultado, [])
        self.assertIn("boom", printers.ultimo_error_listado)


class TestImprimirLinux(unittest.TestCase):
    def test_manda_lp_con_raw(self):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "run") as correr:
                correr.return_value = mock.Mock(returncode=0, stderr=b"")
                printers.imprimir_raw("ZTC-GC420t", "^XA^XZ")
        argumentos = correr.call_args[0][0]
        self.assertIn("-o", argumentos)
        self.assertIn("raw", argumentos)
        self.assertIn("ZTC-GC420t", argumentos)

    def test_error_de_lp_lanza_error_impresion(self):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "run") as correr:
                correr.return_value = mock.Mock(returncode=1, stderr=b"no such printer")
                with self.assertRaises(printers.ErrorImpresion):
                    printers.imprimir_raw("inexistente", "^XA^XZ")

    def test_datos_vacios_falla(self):
        with self.assertRaises(ValueError):
            printers.imprimir_raw("ZTC-GC420t", "")


SALIDA_LPSTAT_P = """printer QL-800 disabled since Thu 04 Jun 2026 12:02:03 PM -03 -
	Unplugged or turned off
printer ZTC-GC420t--EPL- disabled since Fri 22 May 2026 11:41:45 AM -03 -
	Unplugged or turned off
printer ZTC-GC420t--EPL--2 is idle.  enabled since Thu 20 Aug 2026 02:08:57 PM -03
printer ZTC-ZD421-203dpi-ZPL disabled since Tue 19 May 2026 08:06:24 PM -03 -
	Unplugged or turned off
"""


class TestEstadoLinux(unittest.TestCase):
    def _estado(self, salida):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(
                printers.subprocess, "check_output", return_value=salida
            ):
                return printers.estado()

    def test_distingue_habilitadas_de_deshabilitadas(self):
        estados = self._estado(SALIDA_LPSTAT_P)
        self.assertTrue(estados["ZTC-GC420t--EPL--2"])
        self.assertFalse(estados["QL-800"])
        self.assertFalse(estados["ZTC-GC420t--EPL-"])

    def test_ignora_las_lineas_de_motivo(self):
        estados = self._estado(SALIDA_LPSTAT_P)
        self.assertEqual(len(estados), 4)
        self.assertNotIn("Unplugged", estados)

    def test_sin_cups_devuelve_vacio(self):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(
                printers.subprocess, "check_output", side_effect=OSError
            ):
                self.assertEqual(printers.estado(), {})

    def test_nunca_lanza(self):
        with mock.patch.object(printers, "_es_windows", side_effect=RuntimeError):
            self.assertEqual(printers.estado(), {})


if __name__ == "__main__":
    unittest.main()
