"""cofre_core — lógica de negócio pura do Fiel Finance (sem dependência de UI),
compartilhada pelo app Streamlit (desktop/web) e pelo app Flet (mobile).

Cada módulo cobre uma responsabilidade:
- theme: paleta de cores e constantes de exibição (só dados).
- format: formatação de moeda, ids, datas.
- parse: parsing de valores/datas em formato BR e de arquivos CSV/OFX.
- nfce: leitura de QR code de cupom fiscal (chave de acesso, consulta à Sefaz).
- model: dados de exemplo, migração de paleta, consultas sobre contas/categorias/transações.
- storage: persistência local em JSON (I/O puro, sem chamadas de UI).
"""

from .format import fmt, month_key, today_iso, uid
from .model import (
    account_balance,
    acc_by_id,
    cat_by_id,
    migrate_legacy_colors,
    seed_data,
)
try:
    from .nfce import NFCE_URL_RE, extract_chave_acesso, fetch_nfce_receipt
except ImportError:
    # requests/beautifulsoup4 são dependências opcionais, usadas só pela
    # leitura de NFC-e; ambientes sem essas libs (ex.: app mobile antes da
    # Fase 2) ainda devem conseguir importar cofre_core normalmente.
    NFCE_URL_RE = None

    def extract_chave_acesso(*args, **kwargs):
        raise ImportError("extract_chave_acesso requer 'requests' e 'beautifulsoup4'")

    def fetch_nfce_receipt(*args, **kwargs):
        raise ImportError("fetch_nfce_receipt requer 'requests' e 'beautifulsoup4'")
from .parse import (
    _to_float_br,
    decode_upload,
    parse_amount_br,
    parse_date_flexible,
    parse_ofx,
)
from .storage import LoadResult, load_data_core, save_data_core
from .theme import C, CAT_COLORS, LEGACY_COLOR_MAP, MONTHS_PT

__all__ = [
    "fmt", "month_key", "today_iso", "uid",
    "account_balance", "acc_by_id", "cat_by_id", "migrate_legacy_colors", "seed_data",
    "NFCE_URL_RE", "extract_chave_acesso", "fetch_nfce_receipt",
    "_to_float_br", "decode_upload", "parse_amount_br", "parse_date_flexible", "parse_ofx",
    "LoadResult", "load_data_core", "save_data_core",
    "C", "CAT_COLORS", "LEGACY_COLOR_MAP", "MONTHS_PT",
]
