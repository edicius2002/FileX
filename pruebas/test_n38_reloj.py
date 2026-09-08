"""N38: edad negativa y umbral de barrido explícito, sin esperas reales."""
import os
import tempfile
import unittest
from unittest.mock import patch

from filex import trabajo


class RelojDelBarrido(unittest.TestCase):
    def test_cero_desactiva_edad_aunque_mtime_adelante_al_reloj(self):
        with tempfile.TemporaryDirectory() as base:
            d = tempfile.mkdtemp(prefix=trabajo.PREFIJO, dir=base)
            ahora = os.stat(d).st_mtime - 0.015625
            with patch.object(trabajo.time, "time", return_value=ahora):
                parte = trabajo.barrer_huerfanos(base=base, edad_sin_candado=0)
            self.assertFalse(os.path.exists(d), parte)
            self.assertEqual(parte["borrados"], 1)

    def test_umbral_positivo_conserva_directorio_con_fecha_futura(self):
        with tempfile.TemporaryDirectory() as base:
            d = tempfile.mkdtemp(prefix=trabajo.PREFIJO, dir=base)
            with patch.object(trabajo.time, "time", return_value=os.stat(d).st_mtime - 1):
                parte = trabajo.barrer_huerfanos(base=base, edad_sin_candado=60)
            self.assertTrue(os.path.isdir(d))
            self.assertEqual(parte["sin_candado_jovenes"], 1)
