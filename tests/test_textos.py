# -*- coding: utf-8 -*-
import unittest

from modules import textos


def ancho_fijo(caracter):
    return 10


class TestPrecioCorto(unittest.TestCase):
    def test_saca_los_centavos_en_cero(self):
        self.assertEqual(textos.precio_corto("$41.000,00"), "$41.000")
        self.assertEqual(textos.precio_corto("$41,000.00"), "$41,000")

    def test_conserva_los_centavos_que_no_son_cero(self):
        self.assertEqual(textos.precio_corto("$41.000,50"), "$41.000,50")

    def test_saca_espacios_de_los_bordes(self):
        self.assertEqual(textos.precio_corto("  $500,00 "), "$500")


class TestPartirEnLineas(unittest.TestCase):
    def test_si_entra_queda_en_una_linea(self):
        self.assertEqual(textos.partir_en_lineas("ANAFE", 100, ancho_fijo, 2), ["ANAFE"])

    def test_corta_entre_palabras(self):
        lineas = textos.partir_en_lineas("ANAFE ESMALTADO BRONCE", 160, ancho_fijo, 2)
        self.assertEqual(lineas, ["ANAFE ESMALTADO", "BRONCE"])

    def test_lo_que_sobra_se_recorta_en_la_ultima_linea(self):
        lineas = textos.partir_en_lineas("ANAFE ESMALTADO BRONCE GRANDE", 100, ancho_fijo, 2)
        self.assertEqual(lineas, ["ANAFE", "ESMALTADO."])

    def test_palabra_mas_larga_que_la_linea_se_corta_donde_cae(self):
        lineas = textos.partir_en_lineas("ABCDEFGHIJKL", 50, ancho_fijo, 2)
        self.assertEqual(lineas, ["ABCDE", "FGHI."])


class TestRecortar(unittest.TestCase):
    def test_si_entra_no_lo_toca(self):
        self.assertEqual(textos.recortar("ANAFE", 50, ancho_fijo), "ANAFE")

    def test_si_no_entra_lo_corta_con_punto(self):
        recortado = textos.recortar("ANAFE ESMALTADO", 60, ancho_fijo)
        self.assertEqual(recortado, "ANAFE.")
        self.assertLessEqual(textos.ancho(recortado, ancho_fijo), 60)

    def test_no_deja_un_espacio_antes_del_punto(self):
        self.assertEqual(textos.recortar("ANAF ESMALTADO", 60, ancho_fijo), "ANAF.")

    def test_lo_que_devuelve_siempre_entra(self):
        for nombre in ("W" * 40, "PILA ALCALINA AA PACK DOCE", "A B C D E F G H I J K"):
            for ancho_max in (30, 95, 190):
                recortado = textos.recortar(nombre, ancho_max, ancho_fijo)
                self.assertLessEqual(textos.ancho(recortado, ancho_fijo), ancho_max)


class TestAnchoA0(unittest.TestCase):
    def test_las_letras_anchas_miden_mas(self):
        self.assertGreater(textos.ancho_a0_nombre("W"), textos.ancho_a0_nombre("A"))
        self.assertGreater(textos.ancho_a0_nombre("A"), textos.ancho_a0_nombre(" "))

    def test_nunca_subestima_lo_medido_en_labelary(self):
        """Avances de ^A0N,20,10 medidos renderizando 10 repeticiones en Labelary."""
        medidos = {"W": 8.1, "M": 7.6, "-": 9.0, "H": 6.1, "A": 5.5, "0": 4.8, " ": 2.9, "I": 2.8}
        for caracter, medido in medidos.items():
            self.assertGreaterEqual(textos.ancho_a0_nombre(caracter), medido, caracter)


if __name__ == "__main__":
    unittest.main()
