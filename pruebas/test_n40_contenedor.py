"""N40: la frontera del bind debe recibir bytes del descriptor validado."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from filex.confinamiento import Confinamiento, _EntradaConfinada
from filex.grafo import Arista, Grafo, REAL
from filex.motor_contenedor import PandocEnContenedor
from filex.nucleo import FileX, Salto


class EntradaDelContenedor(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "sustitución de directorio: Linux")
    def test_sustitucion_real_del_directorio_despues_de_validar(self):
        with tempfile.TemporaryDirectory() as base:
            raiz = Path(base, "raiz")
            raiz.mkdir()
            permitido = raiz / "carpeta"
            permitido.mkdir()
            ajeno = Path(base, "ajeno")
            ajeno.mkdir()
            (permitido / "entrada.md").write_bytes(b"PERMITIDO")
            (ajeno / "entrada.md").write_bytes(b"AJENO")
            fx = FileX.__new__(FileX)
            fx.confinamiento = Confinamiento([str(raiz)], [str(raiz)])
            motor = PandocEnContenedor()
            fx.motores = {motor.nombre: motor}
            fx.grafo = Grafo([Arista("md", "html", motor.nombre, estado=REAL)])
            abrir = fx._abrir_entrada

            def abrir_y_conmutar(entrada):
                ent = abrir(entrada)
                permitido.rename(raiz / "guardada")
                permitido.symlink_to(ajeno, target_is_directory=True)
                self.assertEqual(Path(ent.real).read_bytes(), b"AJENO")
                return ent

            def leer(arista, entrada, *args, **kwargs):
                self.assertEqual(Path(entrada).read_bytes(), b"PERMITIDO")
                return Salto(arista=arista, rc=0, veredicto="ok")

            with patch.object(fx, "_abrir_entrada", side_effect=abrir_y_conmutar), \
                    patch.object(fx, "_un_salto", side_effect=leer):
                self.assertTrue(fx.convertir(str(permitido / "entrada.md"),
                                             str(raiz / "salida.html")).ok)

    @unittest.skipUnless(os.environ.get("FILEX_PRUEBA_DOC") == "1", "Docker CPU optativo")
    def test_pandoc_real_recibe_bytes_del_descriptor(self):
        with tempfile.TemporaryDirectory() as base:
            entrada = Path(base, "entrada.md")
            ajeno = Path(base, "ajeno.md")
            salida = Path(base, "salida.html")
            entrada.write_text("# FILEXSENTINELA7743\n", encoding="utf-8")
            ajeno.write_text("# CONTENIDOAJENO\n", encoding="utf-8")
            fx = FileX([base], [base])
            abiertos = []

            def abrir_validado(_entrada):
                fd = os.open(entrada, os.O_RDONLY | getattr(os, "O_BINARY", 0))
                abiertos.append(fd)
                return _EntradaConfinada(fd, str(entrada), str(ajeno))

            with patch.object(fx, "_abrir_entrada", side_effect=abrir_validado):
                resultado = fx.convertir(str(entrada), str(salida), timeout=60)
            self.assertTrue(resultado.ok, resultado.motivo)
            with self.assertRaises(OSError):
                os.fstat(abiertos[0])
            texto = salida.read_text(encoding="utf-8")
            self.assertIn("FILEXSENTINELA7743", texto)
            self.assertNotIn("CONTENIDOAJENO", texto)

    def test_bind_lee_descriptor_y_conserva_extension_y_limpieza(self):
        with tempfile.TemporaryDirectory() as base:
            seguro = Path(base, "seguro.md")
            veneno = Path(base, "veneno.md")
            seguro.write_bytes(b"CONTENIDO PERMITIDO")
            veneno.write_bytes(b"CONTENIDO AJENO")
            fx = FileX.__new__(FileX)
            fx.confinamiento = Confinamiento([base], [base])
            motor = PandocEnContenedor()
            fx.motores = {motor.nombre: motor}
            fx.grafo = Grafo()
            arista = Arista("md", "html", motor.nombre, estado=REAL)
            fx.grafo.añadir(arista)
            # Frontera tras validar: la cadena real apunta ahora a otro inodo.
            # El descriptor permanece abierto. Funciona también en Windows,
            # donde el bloqueo de rename impediría fabricar el mismo symlink.
            abiertos = []
            recibidas = []

            def abrir_validado(_entrada):
                # Respeta el orden de producción: resolver/preflight primero,
                # descriptor después. Abrirlo antes hace que Python 3.11 en
                # Windows hosted no pueda ejecutar el segundo ``stat``.
                fd = os.open(seguro, os.O_RDONLY | getattr(os, "O_BINARY", 0))
                abiertos.append(fd)
                return _EntradaConfinada(fd, str(seguro), str(veneno))

            def leer_bind(arista, entrada, *args, **kwargs):
                recibidas.append(entrada)
                self.assertEqual(Path(entrada).read_bytes(), seguro.read_bytes())
                self.assertEqual(Path(entrada).suffix, ".md")
                self.assertNotEqual(entrada, str(seguro))
                return Salto(arista=arista, rc=0, veredicto="ok")

            with patch.object(fx, "_abrir_entrada", side_effect=abrir_validado), \
                    patch("filex.nucleo.os.dup",
                          side_effect=OSError("duplicación CRT no disponible")), \
                    patch.dict(os.environ, {"FILEX_PRUEBA_PROPAGAR_N40": "1"}), \
                    patch.object(fx, "_un_salto", side_effect=leer_bind):
                resultado = fx.convertir(str(seguro), str(Path(base, "salida.html")))
            self.assertTrue(resultado.ok, resultado.motivo)
            self.assertFalse(Path(recibidas[0]).exists())
            with self.assertRaises(OSError):
                os.fstat(abiertos[0])


if __name__ == "__main__":
    unittest.main()
