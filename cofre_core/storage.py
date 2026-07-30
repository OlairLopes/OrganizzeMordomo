"""Persistência local em arquivo JSON — I/O puro, sem nenhuma chamada de UI.
Cada app (Streamlit, Flet) chama `load_data_core`/`save_data_core` e decide
como exibir o aviso/erro devolvido, em vez de imprimir na tela diretamente
daqui."""

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .model import migrate_legacy_colors, seed_data

logger = logging.getLogger("cofre_core.storage")


@dataclass
class LoadResult:
    data: dict
    warning: Optional[str] = None
    backup_path: Optional[str] = None


def load_data_core(path):
    """Carrega os dados em `path`. Se o arquivo não existir, semeia com
    `seed_data()`. Se estiver corrompido, faz backup e recria com dados de
    exemplo, devolvendo um aviso em `LoadResult.warning` para o chamador
    exibir como quiser. Migra cores antigas automaticamente quando aplicável."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if migrate_legacy_colors(data):
                save_data_core(path, data)
            return LoadResult(data=data)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("%s corrompido, fazendo backup e recriando: %s", path, e)
            backup = f"{path}.corrupted-{datetime.now():%Y%m%d%H%M%S}.bak"
            try:
                os.replace(path, backup)
            except OSError:
                backup = None
            data = seed_data()
            save_data_core(path, data)
            warning = f"Não foi possível ler {path} (arquivo corrompido). "
            warning += (
                f"Uma cópia foi salva em {backup} e novos dados de exemplo foram criados."
                if backup else "Novos dados de exemplo foram criados."
            )
            return LoadResult(data=data, warning=warning, backup_path=backup)

    data = seed_data()
    save_data_core(path, data)
    return LoadResult(data=data)


def save_data_core(path, data):
    """Escrita atômica: grava em arquivo temporário e substitui o original,
    evitando corromper o arquivo se o processo for interrompido no meio da
    escrita. Levanta OSError em caso de falha — cabe ao chamador decidir como
    comunicar isso ao usuário."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".cofre_data-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except OSError as e:
        logger.error("Falha ao salvar %s: %s", path, e)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
