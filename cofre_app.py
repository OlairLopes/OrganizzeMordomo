"""
Fiel Finance — Controle Financeiro Pessoal
Versão em Python (Streamlit) do painel financeiro.

Como rodar:
    pip install -r requirements.txt
    streamlit run cofre_app.py

Para usar o Assistente (chat com IA), configure sua própria chave da API
da Anthropic como variável de ambiente ANTHROPIC_API_KEY, ou em
.streamlit/secrets.toml:
    ANTHROPIC_API_KEY = "sk-ant-..."
"""

import hmac
import html
import logging
import os
from datetime import date, datetime
from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st

from cofre_core import (
    C,
    CAT_COLORS,
    MONTHS_PT,
    NFCE_URL_RE,
    acc_by_id,
    account_balance,
    cat_by_id,
    decode_upload,
    fetch_nfce_receipt,
    fmt,
    load_data_core,
    month_key,
    parse_amount_br,
    parse_date_flexible,
    parse_ofx,
    save_data_core,
    today_iso,
    uid,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cofre")

# ---------------------------------------------------------------------------
# Configuração da página e tema
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Fiel Finance — Controle Financeiro", page_icon="💰", layout="wide")

# A paleta de cores (C, CAT_COLORS, MONTHS_PT) vem de cofre_core.theme,
# compartilhada com o app mobile (Flet).

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .cofre-title {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; letter-spacing: -0.01em; }}
    .cofre-mono {{ font-family: 'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums; }}

    /* --- Base / fundo --- */
    .stApp {{
        background: radial-gradient(120% 140% at 12% -10%, #102A20 0%, {C['bg_soft']} 38%, {C['bg']} 70%);
        color: {C['ink']};
    }}
    [data-testid="stHeader"] {{ background: transparent; }}
    [data-testid="stAppViewContainer"] {{ color: {C['ink']}; }}
    h1, h2, h3, h4, h5, h6 {{ font-family: 'Space Grotesk', sans-serif; color: {C['ink']}; letter-spacing: -0.01em; }}
    p, span, label, div {{ color: {C['ink_soft']}; }}
    hr {{ border-color: {C['line']}; }}

    /* --- Sidebar --- */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {C['bg_soft']} 0%, {C['bg']} 100%);
        border-right: 1px solid {C['line']};
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 4px; }}
    [data-testid="stSidebar"] div[role="radiogroup"] label {{
        padding: 10px 14px; border-radius: 10px; transition: background .15s ease;
        width: 100%;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: {C['surface_soft']}; }}
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"],
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: linear-gradient(90deg, rgba(30,174,118,0.22), rgba(30,174,118,0.04));
        border-left: 2px solid {C['primary_bright']};
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label p {{
        font-weight: 600; color: {C['ink']} !important; font-size: 0.95rem;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{ display: none; }}

    /* --- Cards / containers com borda --- */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {C['surface']};
        border: 1px solid {C['line']} !important;
        border-radius: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.24), 0 8px 24px -12px rgba(0,0,0,0.45);
        transition: border-color .15s ease, transform .15s ease;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {{ border-color: {C['line_strong']} !important; }}

    /* --- Botões --- */
    .stButton button {{
        border-radius: 10px; font-weight: 600; border: 1px solid {C['line']};
        transition: all .15s ease;
    }}
    .stButton button[kind="primary"] {{
        background: linear-gradient(135deg, {C['primary_bright']}, {C['primary']});
        border: none; color: #062015;
        box-shadow: 0 4px 16px -4px rgba(30,174,118,0.55);
    }}
    .stButton button[kind="primary"]:hover {{
        box-shadow: 0 6px 22px -4px rgba(43,214,150,0.7);
        transform: translateY(-1px);
    }}
    .stButton button[kind="secondary"] {{ background: {C['surface_soft']}; color: {C['ink']}; }}
    .stButton button[kind="secondary"]:hover {{ border-color: {C['line_strong']}; }}
    /* O reset global de cor (p, span, label, div) acima também atinge o texto
       interno dos botões do Streamlit; força a herdar a cor definida no botão. */
    .stButton button p, .stButton button span, .stButton button div {{ color: inherit !important; }}

    /* --- Inputs --- */
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input, .stSelectbox div[data-baseweb="select"] > div,
    [data-testid="stTextArea"] textarea {{
        background: {C['surface_soft']} !important; color: {C['ink']} !important;
        border-radius: 10px !important; border: 1px solid {C['line']} !important;
    }}

    /* --- Métricas (fallback nativo) --- */
    [data-testid="stMetric"] {{
        background: {C['surface']}; border: 1px solid {C['line']}; border-radius: 16px; padding: 16px 18px;
    }}
    [data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', monospace; color: {C['ink']}; }}
    [data-testid="stMetricLabel"] {{ color: {C['muted']}; }}

    /* --- Progresso --- */
    [data-testid="stProgress"] > div > div {{ background: {C['surface_soft']}; }}
    [data-testid="stProgress"] > div > div > div {{
        background: linear-gradient(90deg, {C['primary']}, {C['primary_bright']});
    }}

    /* --- Diálogos (modais) --- */
    div[role="dialog"] {{
        background: {C['bg_soft']} !important; border: 1px solid {C['line']} !important;
    }}
    div[role="dialog"] button svg {{ color: {C['ink_soft']}; fill: {C['ink_soft']}; }}

    /* --- Chat --- */
    [data-testid="stChatMessage"] {{ background: {C['surface']}; border: 1px solid {C['line']}; border-radius: 14px; }}
    [data-testid="stBottom"] > div {{ background: transparent; }}
    [data-testid="stBottomBlockContainer"] {{
        background: linear-gradient(180deg, transparent, {C['bg']} 40%);
    }}
    [data-testid="stChatInput"] > div, [data-testid="stChatInput"] div[data-baseweb="base-input"] {{
        background: transparent !important;
    }}
    [data-testid="stChatInput"] div[data-baseweb="textarea"] {{
        background: {C['surface']} !important; border: 1px solid {C['line_strong']} !important; border-radius: 14px !important;
    }}
    [data-testid="stChatInputTextArea"] {{ background: transparent !important; color: {C['ink']} !important; }}
    [data-testid="stChatInputTextArea"]::placeholder {{ color: {C['muted']} !important; }}
    [data-testid="stChatInputSubmitButton"] {{ background: {C['primary']} !important; }}

    /* --- DataFrame --- */
    [data-testid="stDataFrame"] {{ border: 1px solid {C['line']}; border-radius: 12px; overflow: hidden; }}

    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-thumb {{ background: {C['surface_soft']}; border-radius: 8px; }}
</style>
""", unsafe_allow_html=True)


def plotly_dark_layout(fig, height=280):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=C["ink_soft"], size=13),
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(font=dict(color=C["ink_soft"])),
    )
    fig.update_xaxes(showgrid=False, color=C["muted"], linecolor=C["line"])
    fig.update_yaxes(showgrid=True, gridcolor=C["line"], zeroline=False, color=C["muted"])
    return fig

DATA_FILE = "cofre_data.json"


def get_secret(name):
    """st.secrets.get() lança StreamlitSecretNotFoundError quando não existe
    nenhum secrets.toml (em vez de retornar o default), então acessamos com
    try/except para tratar 'sem secrets configurados' como 'valor ausente'."""
    try:
        return st.secrets.get(name)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Acesso (senha opcional via st.secrets/variável de ambiente APP_PASSWORD)
# ---------------------------------------------------------------------------
def check_password():
    """Tela de login simples. Se APP_PASSWORD não estiver configurada
    (uso local sem secrets), o app roda livremente sem pedir senha."""
    app_password = os.environ.get("APP_PASSWORD") or get_secret("APP_PASSWORD")
    if not app_password:
        return True
    if st.session_state.get("_authenticated"):
        return True

    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.markdown(
                f'''<div style="text-align:center; padding: 8px 0 4px;">
                    <div style="font-size:40px;">🔐</div>
                    <div class="cofre-title" style="font-size:30px; background: linear-gradient(135deg,{C["primary_bright"]},{C["gold"]});
                        -webkit-background-clip:text; background-clip:text; color:transparent; margin-top:6px;">Fiel Finance</div>
                    <div style="color:{C["muted"]}; font-size:14px; margin-top:2px;">Controle financeiro pessoal — acesso restrito</div>
                </div>''',
                unsafe_allow_html=True,
            )
            senha = st.text_input("Senha", type="password", key="_login_password", label_visibility="collapsed", placeholder="Digite sua senha")
            if st.button("Entrar", type="primary", width="stretch"):
                if hmac.compare_digest(senha, app_password):
                    st.session_state["_authenticated"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
    return False


if not check_password():
    st.stop()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def stat_tile(col, label, value, icon="", accent=None, hint=None):
    """Renderiza um cartão de indicador (KPI) customizado dentro da coluna dada."""
    accent = accent or C["primary"]
    hint_html = f'<div style="font-size:12.5px; color:{accent}; margin-top:6px; font-weight:600;">{hint}</div>' if hint else ""
    col.markdown(f'''
    <div style="background:{C['surface']}; border:1px solid {C['line']}; border-radius:16px; padding:18px 20px;
        box-shadow: 0 1px 2px rgba(0,0,0,.24), 0 8px 24px -12px rgba(0,0,0,.45);">
        <div style="display:flex; align-items:center; gap:8px; color:{C['muted']}; font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:.03em;">
            <span style="font-size:15px;">{icon}</span>{label}
        </div>
        <div class="cofre-mono" style="font-size:26px; font-weight:600; color:{C['ink']}; margin-top:8px;">{value}</div>
        {hint_html}
    </div>
    ''', unsafe_allow_html=True)


def esc_html(text):
    """Escapa HTML em texto vindo do usuário (descrições, nomes de conta/
    categoria) antes de interpolar em blocos st.markdown(unsafe_allow_html=True),
    evitando a injeção de HTML/tags arbitrárias."""
    return html.escape(str(text or ""))


# ---------------------------------------------------------------------------
# Leitura de QR code de cupom fiscal (NFC-e)
# ---------------------------------------------------------------------------
def decode_qr_image(image_bytes):
    """Decodifica o conteúdo de um QR code a partir dos bytes de uma imagem.
    Retorna o texto decodificado (normalmente uma URL) ou None se nenhum QR
    code for encontrado."""
    import cv2
    import numpy as np

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    detector = cv2.QRCodeDetector()
    data, _points, _straight = detector.detectAndDecode(img)
    return data or None


# ---------------------------------------------------------------------------
# Persistência local (arquivo JSON) — a lógica de I/O pura mora em
# cofre_core.storage; aqui só traduzimos o resultado para st.warning/st.error.
# ---------------------------------------------------------------------------
def load_data():
    result = load_data_core(DATA_FILE)
    if result.warning:
        st.warning(result.warning)
    return result.data


def save_data(data):
    try:
        save_data_core(DATA_FILE, data)
    except OSError as e:
        st.error(f"Não foi possível salvar os dados ({e}). Suas últimas alterações podem não ter sido gravadas.")


if "data" not in st.session_state:
    st.session_state.data = load_data()
if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

data = st.session_state.data
accounts = data["accounts"]
categories = data["categories"]
transactions = data["transactions"]


def persist():
    save_data(st.session_state.data)


# ---------------------------------------------------------------------------
# Mês selecionado
# ---------------------------------------------------------------------------
_base = date.today().replace(day=1)
_m = _base.month - 1 + st.session_state.month_offset
_y = _base.year + _m // 12
_m = _m % 12 + 1
selected_date = date(_y, _m, 1)
selected_key = f"{_y:04d}-{_m:02d}"
month_label = f"{MONTHS_PT[_m - 1]} de {_y}"

month_tx = [t for t in transactions if month_key(t["date"]) == selected_key]
income = sum(t["amount"] for t in month_tx if t["type"] == "receita")
expense = sum(t["amount"] for t in month_tx if t["type"] == "despesa")
saldo_total = sum(t["amount"] if t["type"] == "receita" else -t["amount"] for t in transactions)

# ---------------------------------------------------------------------------
# Diálogos (modais)
# ---------------------------------------------------------------------------
@st.dialog("Transação")
def tx_dialog(tx=None):
    is_edit = tx is not None
    tipo = st.radio("Tipo", ["despesa", "receita"], index=0 if not is_edit or tx["type"] == "despesa" else 1,
                     format_func=lambda x: "Despesa" if x == "despesa" else "Receita", horizontal=True)
    descricao = st.text_input("Descrição", value=tx["description"] if is_edit else "")
    valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, value=float(tx["amount"]) if is_edit else 0.0)
    data_tx = st.date_input("Data", value=datetime.fromisoformat(tx["date"]) if is_edit else date.today())
    cats_disponiveis = [c for c in categories if c["kind"] == tipo]
    cat_names = [c["name"] for c in cats_disponiveis]
    default_idx = 0
    if is_edit:
        found = next((i for i, c in enumerate(cats_disponiveis) if c["id"] == tx["categoryId"]), 0)
        default_idx = found
    categoria = st.selectbox("Categoria", cat_names, index=default_idx if cat_names else None) if cat_names else None
    acc_names = [a["name"] for a in accounts]
    acc_default = next((i for i, a in enumerate(accounts) if a["id"] == tx["accountId"]), 0) if is_edit else 0
    conta = st.selectbox("Conta", acc_names, index=acc_default) if acc_names else None

    col1, col2 = st.columns(2)
    if col1.button("Cancelar", width="stretch"):
        st.rerun()
    if col2.button("Salvar", type="primary", width="stretch"):
        if not descricao or valor <= 0 or conta is None:
            st.warning("Preencha descrição, valor e conta.")
            return
        cat_obj = next((c for c in cats_disponiveis if c["name"] == categoria), None) if categoria else None
        acc_obj = next(a for a in accounts if a["name"] == conta)
        new_tx = {
            "id": tx["id"] if is_edit else uid(),
            "type": tipo,
            "description": descricao,
            "amount": valor,
            "date": data_tx.isoformat(),
            "categoryId": cat_obj["id"] if cat_obj else "",
            "accountId": acc_obj["id"],
        }
        if is_edit:
            idx = next(i for i, t in enumerate(transactions) if t["id"] == tx["id"])
            transactions[idx] = new_tx
        else:
            transactions.append(new_tx)
        persist()
        st.rerun()


@st.dialog("Conta")
def account_dialog(acc=None):
    is_edit = acc is not None
    nome = st.text_input("Nome", value=acc["name"] if is_edit else "")
    tipo = st.selectbox("Tipo", ["conta", "cartao"], index=0 if not is_edit or acc["type"] == "conta" else 1,
                         format_func=lambda x: "Conta" if x == "conta" else "Cartão de crédito")
    limite = None
    if tipo == "cartao":
        limite = st.number_input("Limite (R$)", min_value=0.0, step=100.0, value=float(acc.get("limit", 0)) if is_edit else 0.0)
    col1, col2 = st.columns(2)
    if col1.button("Cancelar", width="stretch"):
        st.rerun()
    if col2.button("Salvar", type="primary", width="stretch"):
        if not nome:
            st.warning("Informe um nome.")
            return
        new_acc = {
            "id": acc["id"] if is_edit else uid(),
            "name": nome,
            "type": tipo,
            "color": acc["color"] if is_edit else CAT_COLORS[len(accounts) % len(CAT_COLORS)],
        }
        if limite is not None:
            new_acc["limit"] = limite
        if is_edit:
            idx = next(i for i, a in enumerate(accounts) if a["id"] == acc["id"])
            accounts[idx] = new_acc
        else:
            accounts.append(new_acc)
        persist()
        st.rerun()


@st.dialog("Categoria")
def category_dialog(cat=None):
    is_edit = cat is not None
    nome = st.text_input("Nome", value=cat["name"] if is_edit else "")
    kind = st.selectbox("Tipo", ["despesa", "receita"], index=0 if not is_edit or cat["kind"] == "despesa" else 1,
                         format_func=lambda x: "Despesa" if x == "despesa" else "Receita")
    budget = None
    if kind == "despesa":
        budget = st.number_input("Limite mensal (opcional)", min_value=0.0, step=50.0,
                                  value=float(cat.get("budget", 0)) if is_edit else 0.0)
    col1, col2 = st.columns(2)
    if col1.button("Cancelar", width="stretch"):
        st.rerun()
    if col2.button("Salvar", type="primary", width="stretch"):
        if not nome:
            st.warning("Informe um nome.")
            return
        new_cat = {
            "id": cat["id"] if is_edit else uid(),
            "name": nome,
            "kind": kind,
            "color": cat["color"] if is_edit else CAT_COLORS[len(categories) % len(CAT_COLORS)],
        }
        if budget:
            new_cat["budget"] = budget
        if is_edit:
            idx = next(i for i, c in enumerate(categories) if c["id"] == cat["id"])
            categories[idx] = new_cat
        else:
            categories.append(new_cat)
        persist()
        st.rerun()


@st.dialog("Importar extrato", width="large")
def import_dialog():
    st.caption("Envie um arquivo CSV ou OFX exportado do seu banco.")
    uploaded = st.file_uploader("Arquivo", type=["csv", "ofx", "txt"])
    if uploaded is None:
        return
    ext = uploaded.name.split(".")[-1].lower()
    text = decode_upload(uploaded.getvalue())

    preview_rows = []
    if ext == "ofx":
        preview_rows = parse_ofx(text)
    else:
        try:
            df = pd.read_csv(StringIO(text))
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as e:
            st.error(f"Não foi possível ler o CSV: {e}")
            return
        cols = list(df.columns)

        def guess(cands):
            for c in cols:
                if any(k in c.lower() for k in cands):
                    return c
            return cols[0]

        date_col = st.selectbox("Coluna de data", cols, index=cols.index(guess(["data", "date"])))
        desc_col = st.selectbox("Coluna de descrição", cols, index=cols.index(guess(["descri", "histor", "memo"])))
        amount_col = st.selectbox("Coluna de valor", cols, index=cols.index(guess(["valor", "amount"])))
        if st.button("Pré-visualizar"):
            skipped = 0
            for _, row in df.iterrows():
                dt = parse_date_flexible(row[date_col])
                amt_raw = row[amount_col]
                amt = parse_amount_br(amt_raw)
                if dt and str(amt_raw).strip() not in ("", "nan"):
                    preview_rows.append({"date": dt, "description": str(row[desc_col]), "amount": amt})
                else:
                    skipped += 1
            st.session_state["_import_preview"] = preview_rows
            if skipped:
                st.warning(f"{skipped} linha(s) ignorada(s) por falta de data ou valor válido.")

    preview_rows = st.session_state.get("_import_preview", preview_rows)
    if preview_rows:
        st.write(f"**{len(preview_rows)} lançamentos encontrados**")
        prev_df = pd.DataFrame(preview_rows)
        st.dataframe(prev_df, width="stretch", height=220)
        acc_names = [a["name"] for a in accounts]
        conta = st.selectbox("Importar para a conta", acc_names)
        if st.button("Importar", type="primary"):
            acc_obj = next(a for a in accounts if a["name"] == conta)
            for r in preview_rows:
                transactions.append({
                    "id": uid(),
                    "date": r["date"],
                    "description": r["description"] or "Lançamento importado",
                    "amount": abs(r["amount"]),
                    "type": "despesa" if r["amount"] < 0 else "receita",
                    "categoryId": "",
                    "accountId": acc_obj["id"],
                })
            persist()
            st.session_state.pop("_import_preview", None)
            st.rerun()


_QR_STATE_KEYS = ("_qr_url", "_qr_result", "_qr_error")


@st.dialog("Ler QR code do cupom fiscal", width="large")
def qrcode_dialog():
    st.caption(
        "Aponte a câmera para o QR code do cupom (NFC-e) ou envie uma foto. "
        "Sempre que possível, importamos cada item da nota como uma despesa; "
        "se o portal da Sefaz do seu estado não for compatível, importamos o valor total."
    )
    modo = st.radio("Captura", ["📷 Câmera", "🖼️ Enviar imagem"], horizontal=True, label_visibility="collapsed")
    image_bytes = None
    if modo == "📷 Câmera":
        foto = st.camera_input("Aponte para o QR code", label_visibility="collapsed")
        if foto is not None:
            image_bytes = foto.getvalue()
    else:
        up = st.file_uploader("Imagem do cupom", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        if up is not None:
            image_bytes = up.getvalue()

    if image_bytes is None:
        return

    try:
        url = decode_qr_image(image_bytes)
    except Exception as e:
        # Decodificação de imagem pode falhar de várias formas (arquivo
        # corrompido, formato inesperado); qualquer falha aqui só impede a
        # leitura do QR, não é motivo para quebrar o app.
        logger.error("Falha ao decodificar QR code: %s", e)
        st.error("Não foi possível processar essa imagem.")
        return

    if not url:
        st.warning("Nenhum QR code encontrado na imagem. Tente novamente com mais foco/luz.")
        return
    if not NFCE_URL_RE.match(url):
        st.error("O QR code lido não parece ser de um cupom fiscal (NFC-e).")
        return

    if st.session_state.get("_qr_url") != url:
        st.session_state["_qr_url"] = url
        st.session_state.pop("_qr_result", None)
        st.session_state.pop("_qr_error", None)

    if "_qr_result" not in st.session_state and "_qr_error" not in st.session_state:
        with st.spinner("Consultando nota fiscal..."):
            try:
                st.session_state["_qr_result"] = fetch_nfce_receipt(url)
            except Exception as e:
                # Consulta a um portal público de terceiros (Sefaz estadual):
                # timeout, portal fora do ar ou HTML inesperado não devem
                # derrubar o app — caem no fallback manual abaixo.
                logger.error("Falha ao consultar portal da NFC-e: %s", e)
                st.session_state["_qr_error"] = str(e)

    result = st.session_state.get("_qr_result")
    acc_names = [a["name"] for a in accounts]
    cat_names = ["Sem categoria"] + [c["name"] for c in categories if c["kind"] == "despesa"]

    if result and result["items"]:
        st.success(f"{len(result['items'])} item(ns) encontrados nesta nota.")
        prev_df = pd.DataFrame(result["items"]).rename(columns={"description": "Descrição", "amount": "Valor"})
        st.dataframe(prev_df, width="stretch", height=220)
        st.caption(f"Total: {fmt(sum(i['amount'] for i in result['items']))}")
        conta = st.selectbox("Conta", acc_names, key="_qr_conta")
        categoria = st.selectbox("Categoria (aplicada a todos os itens)", cat_names, key="_qr_categoria")
        if st.button(f"Importar {len(result['items'])} item(ns) como despesas", type="primary"):
            acc_obj = next(a for a in accounts if a["name"] == conta)
            cat_obj = next((c for c in categories if c["name"] == categoria), None) if categoria != "Sem categoria" else None
            data_tx = result["date"] or today_iso()
            for item in result["items"]:
                transactions.append({
                    "id": uid(),
                    "date": data_tx,
                    "description": item["description"],
                    "amount": item["amount"],
                    "type": "despesa",
                    "categoryId": cat_obj["id"] if cat_obj else "",
                    "accountId": acc_obj["id"],
                })
            persist()
            for k in _QR_STATE_KEYS:
                st.session_state.pop(k, None)
            st.rerun()

    elif result and result["total"] is not None:
        st.info(
            "Não foi possível obter os itens desta nota (o portal do seu estado não é "
            "compatível), mas o valor total foi identificado."
        )
        st.metric("Valor total", fmt(result["total"]))
        descricao = st.text_input("Descrição", value="Compra (cupom fiscal)", key="_qr_desc")
        conta = st.selectbox("Conta", acc_names, key="_qr_conta")
        categoria = st.selectbox("Categoria", cat_names, key="_qr_categoria")
        if st.button("Importar despesa", type="primary"):
            acc_obj = next(a for a in accounts if a["name"] == conta)
            cat_obj = next((c for c in categories if c["name"] == categoria), None) if categoria != "Sem categoria" else None
            transactions.append({
                "id": uid(),
                "date": result["date"] or today_iso(),
                "description": descricao or "Compra (cupom fiscal)",
                "amount": result["total"],
                "type": "despesa",
                "categoryId": cat_obj["id"] if cat_obj else "",
                "accountId": acc_obj["id"],
            })
            persist()
            for k in _QR_STATE_KEYS:
                st.session_state.pop(k, None)
            st.rerun()

    else:
        st.warning(
            "Não consegui consultar essa nota automaticamente (portal fora do ar, "
            "sem conexão ou QR code inválido). Preencha manualmente abaixo."
        )
        descricao = st.text_input("Descrição", value="Compra (cupom fiscal)", key="_qr_desc_manual")
        valor = st.number_input("Valor (R$)", min_value=0.0, step=1.0, key="_qr_valor_manual")
        data_manual = st.date_input("Data", value=date.today(), key="_qr_data_manual")
        conta = st.selectbox("Conta", acc_names, key="_qr_conta_manual")
        categoria = st.selectbox("Categoria", cat_names, key="_qr_categoria_manual")
        if st.button("Adicionar despesa", type="primary"):
            if valor <= 0:
                st.warning("Informe um valor.")
                return
            acc_obj = next(a for a in accounts if a["name"] == conta)
            cat_obj = next((c for c in categories if c["name"] == categoria), None) if categoria != "Sem categoria" else None
            transactions.append({
                "id": uid(),
                "date": data_manual.isoformat(),
                "description": descricao or "Compra (cupom fiscal)",
                "amount": valor,
                "type": "despesa",
                "categoryId": cat_obj["id"] if cat_obj else "",
                "accountId": acc_obj["id"],
            })
            persist()
            for k in _QR_STATE_KEYS:
                st.session_state.pop(k, None)
            st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
TABS = {
    "Visão Geral": ("📊", "Seu panorama financeiro do mês"),
    "Transações": ("💸", "Todos os seus lançamentos, filtrados"),
    "Contas": ("🏦", "Contas e cartões sob controle"),
    "Categorias": ("🏷️", "Organize receitas e despesas"),
    "Assistente": ("✨", "Converse sobre suas finanças"),
}

with st.sidebar:
    st.markdown(f'''
    <div style="display:flex; align-items:center; gap:10px; padding: 4px 2px 18px;">
        <div style="width:38px; height:38px; border-radius:11px; display:flex; align-items:center; justify-content:center;
            font-size:19px; background: linear-gradient(135deg, {C["primary_bright"]}, {C["primary"]}); box-shadow: 0 4px 14px -4px rgba(30,174,118,.6);">🔐</div>
        <div>
            <div class="cofre-title" style="font-size:20px; line-height:1.1; color:{C["ink"]};">Fiel Finance</div>
            <div style="font-size:11px; color:{C["muted"]}; letter-spacing:.04em; text-transform:uppercase;">Controle financeiro</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    tab = st.radio(
        "Navegação",
        list(TABS.keys()),
        format_func=lambda t: f"{TABS[t][0]}  {t}",
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("🔒 Seus dados ficam salvos localmente em `cofre_data.json`.")

# ---------------------------------------------------------------------------
# Cabeçalho da página + barra de controle (mês / nova transação)
# ---------------------------------------------------------------------------
icon, subtitle = TABS[tab]
hl, hr = st.columns([3, 2])
with hl:
    st.markdown(
        f'''<div style="display:flex; align-items:baseline; gap:10px;">
            <span class="cofre-title" style="font-size:30px; color:{C["ink"]};">{icon} {tab}</span>
        </div>
        <div style="color:{C["muted"]}; font-size:14px; margin-top:2px;">{subtitle}</div>''',
        unsafe_allow_html=True,
    )
with hr:
    top1, top2, top3, top4 = st.columns([1, 3, 1, 4])
    if top1.button("◀", key="_prev_month", width="stretch"):
        st.session_state.month_offset -= 1
        st.rerun()
    top2.markdown(
        f'<div class="cofre-mono" style="text-align:center; padding-top:8px; font-size:15px; color:{C["ink"]}; font-weight:600;">{month_label}</div>',
        unsafe_allow_html=True,
    )
    if top3.button("▶", key="_next_month", width="stretch"):
        st.session_state.month_offset += 1
        st.rerun()
    if top4.button("＋ Nova transação", type="primary", width="stretch"):
        tx_dialog()

st.write("")

# ---------------------------------------------------------------------------
# Aba: Visão Geral
# ---------------------------------------------------------------------------
if tab == "Visão Geral":
    net = income - expense
    c1, c2, c3, c4 = st.columns(4)
    stat_tile(c1, "Saldo total", fmt(saldo_total), icon="🔐", accent=C["gold"])
    stat_tile(c2, "Receitas do mês", fmt(income), icon="⬆️", accent=C["income"])
    stat_tile(c3, "Despesas do mês", fmt(expense), icon="⬇️", accent=C["expense"])
    stat_tile(
        c4, "Resultado do mês", fmt(net), icon="✨",
        accent=C["income"] if net >= 0 else C["expense"],
        hint=("↑ positivo este mês" if net >= 0 else "↓ atenção: no vermelho"),
    )

    st.write("")
    col_a, col_b = st.columns(2)
    with col_a, st.container(border=True):
        st.markdown("###### 🥧 Despesas por categoria")
        exp_by_cat = {}
        for t in month_tx:
            if t["type"] == "despesa":
                exp_by_cat[t["categoryId"]] = exp_by_cat.get(t["categoryId"], 0) + t["amount"]
        if exp_by_cat:
            rows = []
            for cid, val in exp_by_cat.items():
                c = cat_by_id(categories, cid)
                rows.append({"categoria": c["name"] if c else "Sem categoria", "valor": val, "cor": c["color"] if c else C["muted"]})
            df_pie = pd.DataFrame(rows).sort_values("valor", ascending=False)
            fig = px.pie(df_pie, names="categoria", values="valor", hole=0.6,
                         color="categoria", color_discrete_map=dict(zip(df_pie["categoria"], df_pie["cor"])))
            fig.update_traces(textinfo="percent", textfont_color=C["ink"], marker=dict(line=dict(color=C["surface"], width=2)))
            fig = plotly_dark_layout(fig, height=280)
            fig.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.18, x=0, font=dict(size=11)))
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Nenhuma despesa neste mês ainda.")

    with col_b, st.container(border=True):
        st.markdown("###### 📈 Receitas x despesas (6 meses)")
        trend_rows = []
        for i in range(5, -1, -1):
            mo = selected_date.month - 1 - i
            yr = selected_date.year + mo // 12
            mo = mo % 12 + 1
            key = f"{yr:04d}-{mo:02d}"
            txs = [t for t in transactions if month_key(t["date"]) == key]
            trend_rows.append({
                "mes": MONTHS_PT[mo - 1][:3],
                "Receitas": sum(t["amount"] for t in txs if t["type"] == "receita"),
                "Despesas": sum(t["amount"] for t in txs if t["type"] == "despesa"),
            })
        df_trend = pd.DataFrame(trend_rows).melt(id_vars="mes", value_vars=["Receitas", "Despesas"], var_name="tipo", value_name="valor")
        fig2 = px.bar(df_trend, x="mes", y="valor", color="tipo", barmode="group",
                      color_discrete_map={"Receitas": C["income"], "Despesas": C["expense"]})
        fig2.update_traces(marker_line_width=0)
        fig2 = plotly_dark_layout(fig2, height=280)
        fig2.update_layout(
            legend_title_text="", xaxis_title="", yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        st.plotly_chart(fig2, width="stretch")

    budget_cats = [c for c in categories if c["kind"] == "despesa" and c.get("budget")]
    if budget_cats:
        st.write("")
        with st.container(border=True):
            st.markdown("###### 🎯 Limites de gastos")
            for c in budget_cats:
                spent = sum(t["amount"] for t in month_tx if t["categoryId"] == c["id"])
                pct = min(spent / c["budget"], 1.0) if c["budget"] else 0.0
                bar_color = C["expense"] if pct >= 1 else (C["gold"] if pct >= 0.8 else C["primary"])
                st.markdown(f'''
                <div style="display:flex; justify-content:space-between; margin-top:10px; margin-bottom:4px;">
                    <span style="color:{C['ink']}; font-weight:600; font-size:14px;">
                        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{c['color']}; margin-right:6px;"></span>
                        {esc_html(c['name'])}
                    </span>
                    <span class="cofre-mono" style="color:{C['ink_soft']}; font-size:13px;">{fmt(spent)} / {fmt(c['budget'])}</span>
                </div>
                <div style="background:{C['surface_soft']}; border-radius:8px; height:8px; overflow:hidden;">
                    <div style="width:{pct*100:.1f}%; height:100%; background:{bar_color}; border-radius:8px;"></div>
                </div>
                ''', unsafe_allow_html=True)

    st.write("")
    with st.container(border=True):
        st.markdown("###### 🕒 Últimos lançamentos")
        recent = sorted(month_tx, key=lambda t: t["date"], reverse=True)[:6]
        if not recent:
            st.caption("Nenhum lançamento neste mês ainda.")
        for t in recent:
            cat = cat_by_id(categories, t["categoryId"])
            acc = acc_by_id(accounts, t["accountId"])
            is_income = t["type"] == "receita"
            color = C["income"] if is_income else C["expense"]
            sign = "+" if is_income else "-"
            dot = cat["color"] if cat else C["muted"]
            cols = st.columns([5, 2, 1, 1], vertical_alignment="center")
            cols[0].markdown(f'''
                <div style="border-left:3px solid {dot}; padding-left:10px;">
                    <div style="color:{C['ink']}; font-weight:600; font-size:14.5px;">{esc_html(t['description'])}</div>
                    <div style="color:{C['muted']}; font-size:12.5px;">{t['date']} · {esc_html(cat['name']) if cat else 'Sem categoria'} · {esc_html(acc['name']) if acc else 'Sem conta'}</div>
                </div>''', unsafe_allow_html=True)
            cols[1].markdown(f'<span class="cofre-mono" style="color:{color}; font-weight:600;">{sign}{fmt(t["amount"])}</span>', unsafe_allow_html=True)
            if cols[2].button("✏️", key=f"edit-recent-{t['id']}"):
                tx_dialog(t)
            if cols[3].button("🗑️", key=f"del-recent-{t['id']}"):
                transactions.remove(t)
                persist()
                st.rerun()

# ---------------------------------------------------------------------------
# Aba: Transações
# ---------------------------------------------------------------------------
elif tab == "Transações":
    imp1, imp2 = st.columns(2)
    if imp1.button("⬆️ Importar extrato", width="stretch"):
        import_dialog()
    if imp2.button("🧾 Ler QR code do cupom", width="stretch"):
        qrcode_dialog()

    with st.container(border=True):
        f1, f2, f3 = st.columns([3, 2, 2])
        busca = f1.text_input("Buscar descrição...", placeholder="🔎 Buscar descrição...", label_visibility="collapsed")
        conta_f = f2.selectbox("Conta", ["Todas as contas"] + [a["name"] for a in accounts], label_visibility="collapsed")
        cat_f = f3.selectbox("Categoria", ["Todas as categorias"] + [c["name"] for c in categories], label_visibility="collapsed")

    filtered = month_tx
    if busca:
        filtered = [t for t in filtered if busca.lower() in t["description"].lower()]
    if conta_f != "Todas as contas":
        acc_id = next(a["id"] for a in accounts if a["name"] == conta_f)
        filtered = [t for t in filtered if t["accountId"] == acc_id]
    if cat_f != "Todas as categorias":
        cat_id = next(c["id"] for c in categories if c["name"] == cat_f)
        filtered = [t for t in filtered if t["categoryId"] == cat_id]
    filtered = sorted(filtered, key=lambda t: t["date"], reverse=True)

    st.write("")
    with st.container(border=True):
        if not filtered:
            st.caption("Nenhum lançamento encontrado.")
        for t in filtered:
            cat = cat_by_id(categories, t["categoryId"])
            acc = acc_by_id(accounts, t["accountId"])
            is_income = t["type"] == "receita"
            color = C["income"] if is_income else C["expense"]
            sign = "+" if is_income else "-"
            dot = cat["color"] if cat else C["muted"]
            cols = st.columns([5, 2, 1, 1], vertical_alignment="center")
            cols[0].markdown(f'''
                <div style="border-left:3px solid {dot}; padding-left:10px;">
                    <div style="color:{C['ink']}; font-weight:600; font-size:14.5px;">{esc_html(t['description'])}</div>
                    <div style="color:{C['muted']}; font-size:12.5px;">{t['date']} · {esc_html(cat['name']) if cat else 'Sem categoria'} · {esc_html(acc['name']) if acc else 'Sem conta'}</div>
                </div>''', unsafe_allow_html=True)
            cols[1].markdown(f'<span class="cofre-mono" style="color:{color}; font-weight:600;">{sign}{fmt(t["amount"])}</span>', unsafe_allow_html=True)
            if cols[2].button("✏️", key=f"edit-tx-{t['id']}"):
                tx_dialog(t)
            if cols[3].button("🗑️", key=f"del-tx-{t['id']}"):
                transactions.remove(t)
                persist()
                st.rerun()

# ---------------------------------------------------------------------------
# Aba: Contas
# ---------------------------------------------------------------------------
elif tab == "Contas":
    if st.button("＋ Nova conta", type="primary"):
        account_dialog()
    st.write("")
    cols = st.columns(3)
    for i, a in enumerate(accounts):
        with cols[i % 3]:
            with st.container(border=True):
                icon = "💳" if a["type"] == "cartao" else "🏦"
                acc_color = a.get("color") or C["primary"]
                st.markdown(f'''
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                    <div style="width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center;
                        font-size:16px; background: {acc_color}22; border: 1px solid {acc_color}55;">{icon}</div>
                    <div>
                        <div style="color:{C['ink']}; font-weight:700; font-size:15px;">{esc_html(a['name'])}</div>
                        <div style="color:{C['muted']}; font-size:12px;">{"Cartão de crédito" if a["type"] == "cartao" else "Conta"}</div>
                    </div>
                </div>''', unsafe_allow_html=True)
                bal = account_balance(transactions, a["id"])
                color = C["expense"] if bal < 0 else C["ink"]
                st.markdown(f'<span class="cofre-mono" style="font-size:24px; font-weight:600; color:{color}">{fmt(bal)}</span>', unsafe_allow_html=True)
                if a["type"] == "cartao" and a.get("limit"):
                    st.caption(f"Limite: {fmt(a['limit'])}")
                st.write("")
                b1, b2 = st.columns(2)
                if b1.button("Editar", key=f"edit-acc-{a['id']}", width="stretch"):
                    account_dialog(a)
                if b2.button("Excluir", key=f"del-acc-{a['id']}", width="stretch"):
                    accounts.remove(a)
                    persist()
                    st.rerun()

# ---------------------------------------------------------------------------
# Aba: Categorias
# ---------------------------------------------------------------------------
elif tab == "Categorias":
    if st.button("＋ Nova categoria", type="primary"):
        category_dialog()
    st.write("")
    col1, col2 = st.columns(2)

    def category_row(cols_parent, c, key_prefix):
        with cols_parent, st.container(border=True):
            cc1, cc2, cc3 = st.columns([5, 1, 1], vertical_alignment="center")
            label = esc_html(c["name"]) + (f" · limite {fmt(c['budget'])}" if c.get("budget") else "")
            cc1.markdown(f'''
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:10px; height:10px; border-radius:50%; background:{c['color']}; display:inline-block;"></span>
                    <span style="color:{C['ink']}; font-weight:600; font-size:14.5px;">{label}</span>
                </div>''', unsafe_allow_html=True)
            if cc2.button("✏️", key=f"edit-{key_prefix}-{c['id']}"):
                category_dialog(c)
            if cc3.button("🗑️", key=f"del-{key_prefix}-{c['id']}"):
                categories.remove(c)
                persist()
                st.rerun()

    with col1:
        st.markdown(f'<h6 style="color:{C["income"]};">⬆️ Receitas</h6>', unsafe_allow_html=True)
        for c in [c for c in categories if c["kind"] == "receita"]:
            category_row(col1, c, "cat")
    with col2:
        st.markdown(f'<h6 style="color:{C["expense"]};">⬇️ Despesas</h6>', unsafe_allow_html=True)
        for c in [c for c in categories if c["kind"] == "despesa"]:
            category_row(col2, c, "cat2")

# ---------------------------------------------------------------------------
# Aba: Assistente (chat com IA sobre os dados do usuário)
# ---------------------------------------------------------------------------
elif tab == "Assistente":
    st.caption("Pergunte sobre seus gastos, saldo e limites — a resposta usa só os dados já cadastrados aqui.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Oi! Sou o assistente do Fiel Finance. Pergunte algo como \"quanto gastei com alimentação esse mês?\"."}
        ]

    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    pergunta = st.chat_input("Pergunte sobre suas finanças...")
    if pergunta:
        st.session_state.chat_messages.append({"role": "user", "content": pergunta})

        api_key = os.environ.get("ANTHROPIC_API_KEY") or get_secret("ANTHROPIC_API_KEY")
        if not api_key:
            resposta = ("Para usar o assistente, configure sua chave da API da Anthropic na variável de "
                        "ambiente ANTHROPIC_API_KEY ou em `.streamlit/secrets.toml`.")
        else:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)

                def cat_name(cid):
                    c = cat_by_id(categories, cid)
                    return c["name"] if c else "Sem categoria"

                def acc_name(aid):
                    a = acc_by_id(accounts, aid)
                    return a["name"] if a else "Sem conta"

                recentes = sorted(transactions, key=lambda t: t["date"], reverse=True)[:120]
                linhas = [f"{t['date']} | {t['type']} | {fmt(t['amount'])} | {cat_name(t['categoryId'])} | {acc_name(t['accountId'])} | {t['description']}" for t in recentes]
                contas_str = "; ".join(f"{a['name']} (saldo {fmt(account_balance(transactions, a['id']))})" for a in accounts)
                limites_str = "; ".join(f"{c['name']} (limite {fmt(c['budget'])})" for c in categories if c.get("budget")) or "nenhuma"
                contexto = "\n".join([
                    f"Contas: {contas_str}",
                    f"Categorias com limite: {limites_str}",
                    f"Mês selecionado: {month_label} — receitas {fmt(income)}, despesas {fmt(expense)}, saldo total {fmt(saldo_total)}",
                    "Últimos lançamentos (data | tipo | valor | categoria | conta | descrição):",
                    *linhas,
                ])
                prompt = (
                    "Você é o assistente financeiro do app \"Fiel Finance\". Responda em português do Brasil, de forma "
                    "curta e direta, com base apenas nos dados abaixo. Nunca invente valores que não estejam nos "
                    "dados.\n\nDADOS FINANCEIROS DO USUÁRIO:\n" + contexto +
                    f"\n\nPERGUNTA DO USUÁRIO: \"{pergunta}\""
                )
                msg = client.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                )
                resposta = "".join(block.text for block in msg.content if hasattr(block, "text"))
            except Exception as e:
                logger.error("Falha ao chamar a API da Anthropic: %s", e)
                resposta = "Não consegui falar com o assistente agora. Tente novamente em instantes."

        st.session_state.chat_messages.append({"role": "assistant", "content": resposta})
        st.rerun()
