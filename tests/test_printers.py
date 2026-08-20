# tests/test_printers.py
import unittest
from unittest import mock

from modules import printers


class TestListarLinux(unittest.TestCase):
    def test_parsea_la_salida_de_lpstat(self):
        salida = "printer QL-800 disabled since ayer\nprinter ZTC-GC420t idle\n"
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "check_output", return_value=salida):
                self.assertEqual(printers.listar(), ["QL-800", "ZTC-GC420t"])

    def test_sin_cups_devuelve_lista_vacia(self):
        with mock.patch.object(printers, "_es_windows", return_value=False):
            with mock.patch.object(printers.subprocess, "check_output", side_effect=OSError):
                self.assertEqual(printers.listar(), [])


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


if __name__ == "__main__":
    unittest.main()
