"""La campaña conserva errores como intentos fallidos, no pierde denominador."""
import unittest
from unittest.mock import patch
from ci import repetir_n38


class HistorialDeIntentos(unittest.TestCase):
    def test_error_de_barrido_se_conserva_en_el_denominador(self):
        with patch.object(repetir_n38.trabajo, "barrer_huerfanos",
                          side_effect=OSError("error de barrido simulado")):
            resultado = repetir_n38.medir(2)
        self.assertEqual(resultado["n"], 2)
        self.assertEqual(resultado["fallos"], 2)
        self.assertEqual(len(resultado["intentos"]), 2)
        self.assertIn("OSError", resultado["intentos"][0]["error"])
