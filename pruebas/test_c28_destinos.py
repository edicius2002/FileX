"""C28: explicar el rechazo sin inventar aristas ni soporte universal."""
import unittest
from filex.grafo import Grafo
from filex.nucleo import FileX


class DestinosNoAdmitidos(unittest.TestCase):
    def test_rechazos_distinguen_objeto_y_falta_de_soporte(self):
        fx = FileX.__new__(FileX)
        fx.grafo = Grafo()
        casos = {"sup": "mapa de bits", "clip": "metadatos",
                 "eml": "no implementado", "chk": "paquete",
                 "oeb": "directorio", "rtsp": "red", "sap": "red",
                 "ac4": "encoder", "js": "encoder"}
        for destino, motivo in casos.items():
            with self.subTest(destino=destino):
                decision = fx.planificar("entrada.png", "salida." + destino)
                self.assertFalse(decision.hay)
                self.assertIn(motivo, decision.motivo)
                self.assertEqual(fx.destinos("png"), [])
