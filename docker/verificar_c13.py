"""C51: identidad y arranque de tres motores en CPU, sin red ni GPU."""
import argparse
import json
from pathlib import Path
import subprocess

RAIZ = Path(__file__).resolve().parents[1]

# Código fijo, sin interpolar entrada del usuario. Todos los procesos internos
# tienen tope; timeout es PID hijo de init y no deja motores huérfanos.
SONDA = r'''
import json, os, pathlib, subprocess, tempfile, zipfile
def run(*argv):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, timeout=35, check=True).stdout
with tempfile.TemporaryDirectory() as t:
    os.chdir(t)
    pathlib.Path('entrada.md').write_text('# FILEXSENTINELA7743\n', encoding='utf-8')
    run('pandoc', 'entrada.md', '-o', 'salida.html')
    assert 'FILEXSENTINELA7743' in pathlib.Path('salida.html').read_text()
    run('pandoc', 'entrada.md', '-o', 'entrada.docx')
    run('soffice', '--headless', '--convert-to', 'pdf', '--outdir', t, 'entrada.docx')
    run('qpdf', '--check', 'entrada.pdf')
    run('ebook-convert', 'entrada.docx', 'salida.epub')
    with zipfile.ZipFile('salida.epub') as z:
        assert any(b'FILEXSENTINELA7743' in z.read(n) for n in z.namelist() if n.endswith(('.html', '.xhtml')))
    print(json.dumps({'pandoc_html': True, 'libreoffice_pdf_qpdf': True,
        'calibre_epub_centinela': True, 'fidelidad_general': 'no evaluada',
        'qpdf': run('qpdf', '--version').splitlines()[0],
        'tesseract': run('tesseract', '--list-langs').splitlines()}))
'''


def verificar(imagen):
    lock = json.loads((RAIZ / "docker/c13.lock.json").read_text(encoding="utf-8"))
    r = subprocess.run(["docker", "image", "inspect", imagen],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=30, check=True)
    dato = json.loads(r.stdout)[0]
    # Docker clásico presenta config como Id; containerd presenta manifest.
    if dato["Id"] not in (lock["imagen_manifest"], lock["imagen_config"]):
        raise ValueError("C51: digest distinto del build medido; no se heredan sellos")
    if (dato["Os"], dato["Architecture"]) != ("linux", "amd64"):
        raise ValueError("C51: plataforma sin medida")
    r = subprocess.run(["docker", "run", "--rm", "--init", "--network", "none",
                        "-e", "HOME=/tmp", "--entrypoint", "timeout", dato["Id"],
                        "-k", "5", "120", "python3", "-c", SONDA],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=140, check=True)
    print(json.dumps({"id": dato["Id"], "cpu": True, "sonda": json.loads(r.stdout)},
                     ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("imagen", nargs="?", default="filex-c13-repro")
    verificar(p.parse_args().imagen)
