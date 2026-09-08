"""Diagnóstico CPU de diferencias en los ficheros generados por apt."""
import subprocess


def ficheros(imagen):
    r = subprocess.run(["docker", "run", "--rm", "--init", "--network", "none",
                        "--entrypoint", "timeout", imagen, "-k", "5", "60",
                        "find", "/var", "/etc", "-type", "f", "-exec",
                        "sha256sum", "{}", "+"], capture_output=True, text=True,
                       timeout=90, check=True)
    return dict((linea[66:], linea[:64]) for linea in r.stdout.splitlines())


if __name__ == "__main__":
    import sys
    a, b = map(ficheros, sys.argv[1:3])
    for ruta in sorted(a.keys() | b.keys()):
        if a.get(ruta) != b.get(ruta):
            print(ruta, a.get(ruta), b.get(ruta))
