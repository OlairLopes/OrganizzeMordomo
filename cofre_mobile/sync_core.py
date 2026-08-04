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
    # Remove só o conteúdo, não o diretório em si: dentro do OneDrive, o
    # diretório costuma ficar momentaneamente travado por sincronização e
    # shutil.rmtree(DEST) falha no rmdir final mesmo após apagar os arquivos,
    # deixando src/cofre_core vazio.
    for child in DEST.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        except PermissionError:
            # __pycache__ e afins não são copiados de qualquer forma (ver
            # ignore_patterns abaixo); não vale travar o sync por um lock
            # passageiro do OneDrive num diretório que será apenas ignorado.
            pass
shutil.copytree(SRC, DEST, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
print(f"Copiado {SRC} -> {DEST}")
