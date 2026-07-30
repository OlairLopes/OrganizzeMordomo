"""Copia o pacote cofre_core (a fonte de verdade fica em ../cofre_core, usado
também pelo app Streamlit) para dentro de src/, onde o `flet build`/`flet run`
consegue empacotá-lo junto com o resto do app. Rode este script sempre que
cofre_core mudar.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT.parent / "cofre_core"
DEST = ROOT / "src" / "cofre_core"

if not SRC.exists():
    raise SystemExit(f"cofre_core não encontrado em {SRC}")

if DEST.exists():
    shutil.rmtree(DEST)
shutil.copytree(SRC, DEST, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
print(f"Copiado {SRC} -> {DEST}")
