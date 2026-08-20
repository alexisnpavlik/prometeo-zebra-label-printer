import unittest

from modules import barcodes


class TestVerificador(unittest.TestCase):
    def test_ean13_del_anafe(self):
        self.assertEqual(barcodes.verificador("779482465848"), "8")

    def test_upca_del_scunci(self):
        self.assertEqual(barcodes.verificador("67787056807"), "9")


class TestElegirBarcode(unittest.TestCase):
    def test_ean13_valido_usa_be(self):
        self.assertEqual(barcodes.elegir_barcode("7794824658488"), ("^BEN", 2))

    def test_upca_valido_usa_bu(self):
        self.assertEqual(barcodes.elegir_barcode("677870568079"), ("^BUN", 2))

    def test_ean13_con_verificador_invalido_cae_a_code128(self):
        comando, _ = barcodes.elegir_barcode("7794824658487")
        self.assertEqual(comando, "^BCN")

    def test_codigo_interno_corto_usa_code128_que_entra(self):
        comando, modulo = barcodes.elegir_barcode("123456")
        self.assertEqual(comando, "^BCN")
        self.assertLessEqual(barcodes.modulos_code128("123456") * modulo, 190)

    def test_codigo_alfanumerico_baja_el_modulo(self):
        comando, modulo = barcodes.elegir_barcode("ABC-123")
        self.assertEqual(comando, "^BCN")
        self.assertEqual(modulo, 1)

    def test_codigo_demasiado_largo_falla(self):
        with self.assertRaises(ValueError):
            barcodes.elegir_barcode("A" * 60)

    def test_codigo_vacio_falla(self):
        with self.assertRaises(ValueError):
            barcodes.elegir_barcode("   ")


if __name__ == "__main__":
    unittest.main()
