"""Copia los documentos de funcionalidades (plantilla técnica) a docs/funcionalidades/.

La fuente de verdad es el repo TecLogi-Server-Java (pom-teclogi/docs/features). Este script deja
docs/funcionalidades/ como espejo exacto de los .md de esa carpeta: copia los nuevos/cambiados y
borra los que ya no existen en el origen. Se ignoran README.md y todo lo que empiece con `_`
(p. ej. `_fuente/`), igual que hooks/docflow.py.

Uso:
    python scripts/sync_features.py [ORIGEN] [DESTINO]

ORIGEN por defecto: variable FEATURES_SRC o el repo hermano en C:/AMBIENTES.
DESTINO por defecto: docs/funcionalidades (relativo a la raíz de este repo).
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT.parent / "TecLogi-Server-Java" / "TecLogi-Server-Java-" / "pom-teclogi" / "docs" / "features"
DEFAULT_DST = ROOT / "docs" / "funcionalidades"


def is_doc(p: Path) -> bool:
    return p.suffix == ".md" and p.name.lower() != "readme.md" and not p.name.startswith("_")


def main(argv):
    src = Path(argv[1] if len(argv) > 1 else os.environ.get("FEATURES_SRC", DEFAULT_SRC)).resolve()
    dst = Path(argv[2] if len(argv) > 2 else DEFAULT_DST).resolve()
    if not src.is_dir():
        sys.exit(f"sync_features: no existe la carpeta origen: {src}")

    docs = sorted(p for p in src.iterdir() if p.is_file() and is_doc(p))
    if not docs:
        sys.exit(f"sync_features: no hay documentos .md en {src}; no se toca el destino")

    dst.mkdir(parents=True, exist_ok=True)
    keep = {p.name for p in docs}
    for old in dst.glob("*.md"):
        if old.name not in keep:
            old.unlink()
            print(f"  - {old.name} (ya no existe en el origen)")
    for p in docs:
        shutil.copyfile(p, dst / p.name)
        print(f"  + {p.name}")
    print(f"sync_features: {len(docs)} documento(s) {src} -> {dst}")


if __name__ == "__main__":
    main(sys.argv)
