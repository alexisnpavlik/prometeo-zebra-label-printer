import unittest

from modules import zpl_parser

ODOO_CON_PRECIO = """
^XA^CI28
^FT100,80^A0N,40,30^FD[(658488/202039E/2020] "O.F" ANAFE 1 HORNALLA ESMALTADO REDUCCION BRONCE CONOMETAL (658488/202039E/202040E)^FS
^FT100,115^A0N,30,24^FD(658488/202039E^FS
^FO600,100,1
^A0N,66,48^FH^FD$41.000,00^FS
^FO100,160^BY3
^BCN,100,Y,N,N
^FD7794824658488^FS
^XZ
"""

ODOO_SIN_PRECIO = """
^XA^CI28
^FT100,80^A0N,40,30^FD[C-842B-17-7] SCUNCI DE TELA ESTAMPA LETRAS (CV) (568079)^FS
^FT100,150^A0N,30,24^FDC-842B-17-7^FS
^FO100,160^BY3
^BCN,100,Y,N,N
^FD677870568079^FS
^XZ
"""


class TestParsear(unittest.TestCase):
    def test_extrae_codigo_del_barcode(self):
        self.assertEqual(zpl_parser.parsear(ODOO_CON_PRECIO)["codigo"], "7794824658488")

    def test_extrae_precio(self):
        self.assertEqual(zpl_parser.parsear(ODOO_CON_PRECIO)["precio"], "$41.000,00")

    def test_sin_precio_devuelve_none(self):
        self.assertIsNone(zpl_parser.parsear(ODOO_SIN_PRECIO)["precio"])

    def test_nombre_sin_prefijo_ni_sufijo(self):
        nombre = zpl_parser.parsear(ODOO_SIN_PRECIO)["nombre"]
        self.assertEqual(nombre, 'SCUNCI DE TELA ESTAMPA LETRAS (CV)')

    def test_nombre_del_anafe_conserva_el_texto_util(self):
        nombre = zpl_parser.parsear(ODOO_CON_PRECIO)["nombre"]
        self.assertIn("ANAFE 1 HORNALLA", nombre)
        self.assertFalse(nombre.startswith("["))

    def test_texto_sin_barcode_lanza_parse_error(self):
        with self.assertRaises(zpl_parser.ParseError):
            zpl_parser.parsear("^XA^FT10,10^FDhola^FS^XZ")


EPL_DE_ENTRADA = """N
q736
Q166,24
A20,10,0,2,1,1,N,"[C-842B] SCUNCI DE TELA (CV)"
A20,48,0,2,2,2,N,"$500,00"
B20,84,0,"UA0",2,4,40,N,"677870568079"
P1
"""


class TestEpl(unittest.TestCase):
    def test_detecta_zpl(self):
        self.assertEqual(zpl_parser.detectar_lenguaje(ODOO_CON_PRECIO), "zpl")

    def test_detecta_epl(self):
        self.assertEqual(zpl_parser.detectar_lenguaje(EPL_DE_ENTRADA), "epl")

    def test_parsea_codigo_de_epl(self):
        self.assertEqual(zpl_parser.parsear(EPL_DE_ENTRADA)["codigo"], "677870568079")

    def test_parsea_precio_de_epl(self):
        self.assertEqual(zpl_parser.parsear(EPL_DE_ENTRADA)["precio"], "$500,00")

    def test_parsea_nombre_de_epl_sin_prefijo(self):
        self.assertEqual(
            zpl_parser.parsear(EPL_DE_ENTRADA)["nombre"], "SCUNCI DE TELA (CV)"
        )


class TestLimpiarNombre(unittest.TestCase):
    def test_saca_prefijo_entre_corchetes(self):
        self.assertEqual(zpl_parser.limpiar_nombre("[C-842B] SCUNCI"), "SCUNCI")

    def test_saca_sufijo_numerico_entre_parentesis(self):
        self.assertEqual(zpl_parser.limpiar_nombre("SCUNCI (568079)"), "SCUNCI")

    def test_conserva_parentesis_no_numericos(self):
        self.assertEqual(zpl_parser.limpiar_nombre("SCUNCI (CV)"), "SCUNCI (CV)")


if __name__ == "__main__":
    unittest.main()
