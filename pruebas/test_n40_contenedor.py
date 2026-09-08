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
            fd = os.open(entrada, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            ent = _EntradaConfinada(fd, str(entrada), str(ajeno))
            with patch.object(fx, "_abrir_entrada", return_value=ent):
                resultado = fx.convertir(str(entrada), str(salida), timeout=60)
            self.assertTrue(resultado.ok, resultado.motivo)
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
            fd = os.open(seguro, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            ent = _EntradaConfinada(fd, str(seguro), str(veneno))
            recibidas = []

            def leer_bind(arista, entrada, *args, **kwargs):
                recibidas.append(entrada)
                self.assertEqual(Path(entrada).read_bytes(), seguro.read_bytes())
                self.assertEqual(Path(entrada).suffix, ".md")
                self.assertNotEqual(entrada, str(seguro))
                return Salto(arista=arista, rc=0, veredicto="ok")

            with patch.object(fx, "_abrir_entrada", return_value=ent), \
                    patch.object(fx, "_un_salto", side_effect=leer_bind):
                resultado = fx.convertir(str(seguro), str(Path(base, "salida.html")))
            self.assertTrue(resultado.ok, resultado.motivo)
            self.assertFalse(Path(recibidas[0]).exists())
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_el_descriptor_gana_si_el_alias_resuelto_no_se_puede_reabrir(self):
        """Windows hosted puede negar un segundo ``stat`` con el HANDLE abierto.

        No debe haber una comprobación previa por ruta: la autoridad real es el
        descriptor que ``abrir_confinado`` abre y valida una sola vez.
        """
        with tempfile.TemporaryDirectory() as base:
            seguro = Path(base, "seguro.md")
            salida = Path(base, "salida.html")
            seguro.write_bytes(b"DESCRIPTOR VALIDADO")
            alias_no_reabrible = str(Path(base, "alias-que-no-existe.md"))
            fd = os.open(seguro, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            ent = _EntradaConfinada(fd, str(seguro), str(seguro))
            fx = FileX.__new__(FileX)
            fx.confinamiento = Confinamiento([base], [base])
            motor = PandocEnContenedor()
            fx.motores = {motor.nombre: motor}
            arista = Arista("md", "html", motor.nombre, estado=REAL)
            fx.grafo = Grafo([arista])

            def leer_bind(arista, entrada, *args, **kwargs):
                self.assertEqual(Path(entrada).read_bytes(), b"DESCRIPTOR VALIDADO")
                return Salto(arista=arista, rc=0, veredicto="ok")

            try:
                with patch.object(fx, "_resolver", return_value=(alias_no_reabrible,
                                                                  str(salida))), \
                        patch.object(fx, "_abrir_entrada", return_value=ent), \
                        patch("filex.nucleo.os.path.isfile", return_value=False), \
                        patch.object(fx, "_un_salto", side_effect=leer_bind):
                    resultado = fx.convertir(str(seguro), str(salida))
                self.assertTrue(resultado.ok, resultado.motivo)
            finally:
                ent.cerrar()

    def test_la_copia_no_duplica_el_descriptor_validado(self):
        """El CRT de Windows no debe mediar entre el descriptor y la copia."""
        with tempfile.TemporaryDirectory() as base:
            seguro = Path(base, "seguro.md")
            salida = Path(base, "salida.html")
            seguro.write_bytes(b"DESCRIPTOR SIN DUPLICAR")
            fd = os.open(seguro, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            ent = _EntradaConfinada(fd, str(seguro), str(seguro))
            fx = FileX.__new__(FileX)
            fx.confinamiento = Confinamiento([base], [base])
            motor = PandocEnContenedor()
            fx.motores = {motor.nombre: motor}
            arista = Arista("md", "html", motor.nombre, estado=REAL)
            fx.grafo = Grafo([arista])

            def leer_bind(arista, entrada, *args, **kwargs):
                self.assertEqual(Path(entrada).read_bytes(),
                                 b"DESCRIPTOR SIN DUPLICAR")
                return Salto(arista=arista, rc=0, veredicto="ok")

            with patch.object(fx, "_abrir_entrada", return_value=ent), \
                    patch.object(fx, "_un_salto", side_effect=leer_bind), \
                    patch("filex.nucleo.os.dup",
                          side_effect=OSError("duplicación CRT no disponible")):
                resultado = fx.convertir(str(seguro), str(salida))
            self.assertTrue(resultado.ok, resultado.motivo)


if __name__ == "__main__":
    unittest.main()
