"""
Cofre — Controle Financeiro Pessoal
Versão em Python (Streamlit) do painel financeiro.

Como rodar:
    pip install -r requirements.txt
    streamlit run cofre_app.py

Para usar o Assistente (chat com IA), configure sua própria chave da API
da Anthropic como variável de ambiente ANTHROPIC_API_KEY, ou em
.streamlit/secrets.toml:
    ANTHROPIC_API_KEY = "sk-ant-..."
"""

import calendar
import hmac
import json
import logging
import os
import re
import tempfile
import uuid
from datetime import date, datetime
from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cofre")

# ---------------------------------------------------------------------------
# Configuração da página e tema
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Cofre — Controle Financeiro", page_icon="💰", layout="wide")

C = {
    "bg": "#F6F4EF",
    "surface": "#FFFFFF",
    "ink": "#1E2A24",
    "ink_soft": "#4B5750",
    "muted": "#8A948D",
    "line": "#E4E0D6",
    "primary": "#145C43",
    "primary_soft": "#DCE9E2",
    "income": "#2F8F5B",
    "expense": "#B5482A",
    "warn": "#B8860B",
}

CAT_COLORS = ["#145C43", "#B5482A", "#B8860B", "#4B6FA8", "#7A4F9E", "#2F8F5B", "#8A5A3C", "#5C7A8A"]
MONTHS_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
             "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .cofre-title {{ font-family: 'Fraunces', serif; font-weight: 700; }}
    .cofre-mono {{ font-family: 'IBM Plex Mono', monospace; }}
    [data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', monospace; color: {C['ink']}; }}
    .stApp {{ background-color: {C['bg']}; }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 14px; }}
</style>
""", unsafe_allow_html=True)

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

    st.markdown(
        f'<div class="cofre-title" style="font-size:28px; color:{C["primary"]}">💰 Cofre</div>',
        unsafe_allow_html=True,
    )
    st.caption("Controle financeiro pessoal — acesso restrito")
    senha = st.text_input("Senha", type="password", key="_login_password")
    if st.button("Entrar", type="primary"):
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
def fmt(n):
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        n = 0.0
    neg = n < 0
    s = f"R$ {abs(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-{s}" if neg else s


def month_key(date_str):
    return date_str[:7]


def uid():
    return uuid.uuid4().hex[:8]


def today_iso():
    return date.today().isoformat()


def parse_amount_br(raw):
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw or "").strip().replace("R$", "").replace(" ", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_date_flexible(raw):
    s = str(raw or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        dd, mo, yy = m.groups()
        if len(yy) == 2:
            yy = "20" + yy
        return f"{yy}-{mo.zfill(2)}-{dd.zfill(2)}"
    return s


_MD_ESCAPE_RE = re.compile(r"([\\`*_\[\]()#!<>])")


def md_escape(text):
    """Escapa caracteres especiais de Markdown em texto vindo do usuário
    (descrições, nomes de conta/categoria) antes de interpolar em st.write,
    evitando que formatação ou imagens/links markdown sejam injetados."""
    return _MD_ESCAPE_RE.sub(r"\\\1", str(text or ""))


def decode_upload(raw_bytes):
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def parse_ofx(text):
    blocks = re.findall(r"<STMTTRN>[\s\S]*?</STMTTRN>", text, re.IGNORECASE)
    rows = []
    for b in blocks:
        def get(tag):
            m = re.search(rf"<{tag}>([^<\r\n]+)", b, re.IGNORECASE)
            return m.group(1).strip() if m else ""
        dt_raw = get("DTPOSTED")
        if not dt_raw:
            continue
        date_str = f"{dt_raw[0:4]}-{dt_raw[4:6]}-{dt_raw[6:8]}"
        amount = parse_amount_br(get("TRNAMT"))
        memo = get("MEMO") or get("NAME") or "Lançamento importado"
        rows.append({"date": date_str, "description": memo, "amount": amount})
    return rows


# ---------------------------------------------------------------------------
# Persistência local (arquivo JSON)
# ---------------------------------------------------------------------------
def seed_data():
    today = date.today()

    def d(day, offset_months=0):
        m = today.month - 1 + offset_months
        y = today.year + m // 12
        m = m % 12 + 1
        day = min(day, calendar.monthrange(y, m)[1])
        return date(y, m, day).isoformat()

    accounts = [
        {"id": "acc-corrente", "name": "Conta Corrente", "type": "conta", "color": "#145C43"},
        {"id": "acc-cartao", "name": "Cartão de Crédito", "type": "cartao", "limit": 3000, "color": "#B5482A"},
    ]
    categories = [
        {"id": "cat-salario", "name": "Salário", "kind": "receita", "color": CAT_COLORS[0]},
        {"id": "cat-freelance", "name": "Freelance", "kind": "receita", "color": CAT_COLORS[3]},
        {"id": "cat-moradia", "name": "Moradia", "kind": "despesa", "color": CAT_COLORS[1], "budget": 1200},
        {"id": "cat-alimentacao", "name": "Alimentação", "kind": "despesa", "color": CAT_COLORS[2], "budget": 800},
        {"id": "cat-transporte", "name": "Transporte", "kind": "despesa", "color": CAT_COLORS[4], "budget": 350},
        {"id": "cat-lazer", "name": "Lazer", "kind": "despesa", "color": CAT_COLORS[5], "budget": 300},
        {"id": "cat-assinaturas", "name": "Assinaturas", "kind": "despesa", "color": CAT_COLORS[6], "budget": 150},
    ]
    transactions = [
        {"id": uid(), "date": d(5), "description": "Salário mensal", "amount": 4200, "type": "receita", "categoryId": "cat-salario", "accountId": "acc-corrente"},
        {"id": uid(), "date": d(2, -1), "description": "Salário mensal", "amount": 4200, "type": "receita", "categoryId": "cat-salario", "accountId": "acc-corrente"},
        {"id": uid(), "date": d(10), "description": "Projeto extra", "amount": 650, "type": "receita", "categoryId": "cat-freelance", "accountId": "acc-corrente"},
        {"id": uid(), "date": d(6), "description": "Aluguel", "amount": 1100, "type": "despesa", "categoryId": "cat-moradia", "accountId": "acc-corrente"},
        {"id": uid(), "date": d(6, -1), "description": "Aluguel", "amount": 1100, "type": "despesa", "categoryId": "cat-moradia", "accountId": "acc-corrente"},
        {"id": uid(), "date": d(8), "description": "Supermercado", "amount": 380, "type": "despesa", "categoryId": "cat-alimentacao", "accountId": "acc-cartao"},
        {"id": uid(), "date": d(14), "description": "Restaurante", "amount": 120, "type": "despesa", "categoryId": "cat-alimentacao", "accountId": "acc-cartao"},
        {"id": uid(), "date": d(3), "description": "Combustível", "amount": 220, "type": "despesa", "categoryId": "cat-transporte", "accountId": "acc-cartao"},
        {"id": uid(), "date": d(18), "description": "Cinema", "amount": 90, "type": "despesa", "categoryId": "cat-lazer", "accountId": "acc-cartao"},
        {"id": uid(), "date": d(1), "description": "Streaming", "amount": 55, "type": "despesa", "categoryId": "cat-assinaturas", "accountId": "acc-cartao"},
        {"id": uid(), "date": d(5, -2), "description": "Salário mensal", "amount": 4100, "type": "receita", "categoryId": "cat-salario", "accountId": "acc-corrente"},
        {"id": uid(), "date": d(9, -2), "description": "Supermercado", "amount": 410, "type": "despesa", "categoryId": "cat-alimentacao", "accountId": "acc-cartao"},
        {"id": uid(), "date": d(20, -3), "description": "Salário mensal", "amount": 4100, "type": "receita", "categoryId": "cat-salario", "accountId": "acc-corrente"},
        {"id": uid(), "date": d(11, -3), "description": "Manutenção do carro", "amount": 300, "type": "despesa", "categoryId": "cat-transporte", "accountId": "acc-cartao"},
    ]
    return {"accounts": accounts, "categories": categories, "transactions": transactions}


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("cofre_data.json corrompido, fazendo backup e recriando: %s", e)
            backup = f"{DATA_FILE}.corrupted-{datetime.now():%Y%m%d%H%M%S}.bak"
            try:
                os.replace(DATA_FILE, backup)
            except OSError:
                pass
            st.warning(
                f"Não foi possível ler {DATA_FILE} (arquivo corrompido). "
                f"Uma cópia foi salva em {backup} e novos dados de exemplo foram criados."
            )
    data = seed_data()
    save_data(data)
    return data


def save_data(data):
    """Escrita atômica: grava em arquivo temporário e substitui o original,
    evitando corromper cofre_data.json se o processo for interrompido no meio da escrita."""
    directory = os.path.dirname(os.path.abspath(DATA_FILE)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".cofre_data-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DATA_FILE)
    except OSError as e:
        logger.error("Falha ao salvar %s: %s", DATA_FILE, e)
        st.error(f"Não foi possível salvar os dados ({e}). Suas últimas alterações podem não ter sido gravadas.")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


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


def cat_by_id(cid):
    return next((c for c in categories if c["id"] == cid), None)


def acc_by_id(aid):
    return next((a for a in accounts if a["id"] == aid), None)


def account_balance(acc_id):
    total = 0.0
    for t in transactions:
        if t["accountId"] == acc_id:
            total += t["amount"] if t["type"] == "receita" else -t["amount"]
    return total


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


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f'<div class="cofre-title" style="font-size:22px; color:{C["primary"]}">💰 Cofre</div>', unsafe_allow_html=True)
    st.caption("Controle financeiro pessoal")
    tab = st.radio(
        "Navegação",
        ["Visão Geral", "Transações", "Contas", "Categorias", "Assistente"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Seus dados ficam salvos localmente em `cofre_data.json`.")

# ---------------------------------------------------------------------------
# Top bar: navegação de mês + nova transação
# ---------------------------------------------------------------------------
top1, top2, top3, top4 = st.columns([1, 3, 6, 2])
if top1.button("◀"):
    st.session_state.month_offset -= 1
    st.rerun()
top2.markdown(f'<div class="cofre-title" style="font-size:20px; text-align:center;">{month_label}</div>', unsafe_allow_html=True)
if top2.button("▶"):
    st.session_state.month_offset += 1
    st.rerun()
if top4.button("＋ Nova transação", type="primary", width="stretch"):
    tx_dialog()

st.write("")

# ---------------------------------------------------------------------------
# Aba: Visão Geral
# ---------------------------------------------------------------------------
if tab == "Visão Geral":
    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo total", fmt(saldo_total))
    c2.metric("Receitas do mês", fmt(income))
    c3.metric("Despesas do mês", fmt(expense), delta=fmt(income - expense))

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### Despesas por categoria")
        exp_by_cat = {}
        for t in month_tx:
            if t["type"] == "despesa":
                exp_by_cat[t["categoryId"]] = exp_by_cat.get(t["categoryId"], 0) + t["amount"]
        if exp_by_cat:
            rows = []
            for cid, val in exp_by_cat.items():
                c = cat_by_id(cid)
                rows.append({"categoria": c["name"] if c else "Sem categoria", "valor": val, "cor": c["color"] if c else C["muted"]})
            df_pie = pd.DataFrame(rows).sort_values("valor", ascending=False)
            fig = px.pie(df_pie, names="categoria", values="valor", hole=0.55,
                         color="categoria", color_discrete_map=dict(zip(df_pie["categoria"], df_pie["cor"])))
            fig.update_traces(textinfo="percent+label")
            fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Nenhuma despesa neste mês ainda.")

    with col_b:
        st.markdown("##### Receitas x despesas (6 meses)")
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
        fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280, legend_title_text="")
        st.plotly_chart(fig2, width="stretch")

    budget_cats = [c for c in categories if c["kind"] == "despesa" and c.get("budget")]
    if budget_cats:
        st.markdown("##### Limites de gastos")
        for c in budget_cats:
            spent = sum(t["amount"] for t in month_tx if t["categoryId"] == c["id"])
            pct = min(spent / c["budget"], 1.0)
            st.write(f"**{c['name']}** — {fmt(spent)} / {fmt(c['budget'])}")
            st.progress(pct)

    st.markdown("##### Últimos lançamentos")
    recent = sorted(month_tx, key=lambda t: t["date"], reverse=True)[:6]
    for t in recent:
        cat = cat_by_id(t["categoryId"])
        acc = acc_by_id(t["accountId"])
        cols = st.columns([5, 2, 1, 1])
        cols[0].write(f"**{md_escape(t['description'])}**  \n:gray[{t['date']} · {md_escape(cat['name']) if cat else 'Sem categoria'} · {md_escape(acc['name']) if acc else 'Sem conta'}]")
        color = C["income"] if t["type"] == "receita" else C["expense"]
        sign = "+" if t["type"] == "receita" else "-"
        cols[1].markdown(f'<span class="cofre-mono" style="color:{color}">{sign}{fmt(t["amount"])}</span>', unsafe_allow_html=True)
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
    if st.button("⬆️ Importar extrato"):
        import_dialog()

    f1, f2, f3 = st.columns([3, 2, 2])
    busca = f1.text_input("Buscar descrição...")
    conta_f = f2.selectbox("Conta", ["Todas as contas"] + [a["name"] for a in accounts])
    cat_f = f3.selectbox("Categoria", ["Todas as categorias"] + [c["name"] for c in categories])

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

    if not filtered:
        st.caption("Nenhum lançamento encontrado.")
    for t in filtered:
        cat = cat_by_id(t["categoryId"])
        acc = acc_by_id(t["accountId"])
        cols = st.columns([5, 2, 1, 1])
        cols[0].write(f"**{md_escape(t['description'])}**  \n:gray[{t['date']} · {md_escape(cat['name']) if cat else 'Sem categoria'} · {md_escape(acc['name']) if acc else 'Sem conta'}]")
        color = C["income"] if t["type"] == "receita" else C["expense"]
        sign = "+" if t["type"] == "receita" else "-"
        cols[1].markdown(f'<span class="cofre-mono" style="color:{color}">{sign}{fmt(t["amount"])}</span>', unsafe_allow_html=True)
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
    if st.button("＋ Nova conta"):
        account_dialog()
    cols = st.columns(3)
    for i, a in enumerate(accounts):
        with cols[i % 3]:
            with st.container(border=True):
                icon = "💳" if a["type"] == "cartao" else "🏦"
                st.markdown(f"**{icon} {a['name']}**")
                st.caption("Cartão de crédito" if a["type"] == "cartao" else "Conta")
                bal = account_balance(a["id"])
                color = C["expense"] if bal < 0 else C["ink"]
                st.markdown(f'<span class="cofre-mono" style="font-size:22px; color:{color}">{fmt(bal)}</span>', unsafe_allow_html=True)
                if a["type"] == "cartao" and a.get("limit"):
                    st.caption(f"Limite: {fmt(a['limit'])}")
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
    if st.button("＋ Nova categoria"):
        category_dialog()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"##### :green[Receitas]")
        for c in [c for c in categories if c["kind"] == "receita"]:
            cc1, cc2, cc3 = st.columns([5, 1, 1])
            cc1.write(f"🟢 {c['name']}")
            if cc2.button("✏️", key=f"edit-cat-{c['id']}"):
                category_dialog(c)
            if cc3.button("🗑️", key=f"del-cat-{c['id']}"):
                categories.remove(c)
                persist()
                st.rerun()
    with col2:
        st.markdown(f"##### :red[Despesas]")
        for c in [c for c in categories if c["kind"] == "despesa"]:
            cc1, cc2, cc3 = st.columns([5, 1, 1])
            label = f"🔴 {c['name']}" + (f" — limite {fmt(c['budget'])}" if c.get("budget") else "")
            cc1.write(label)
            if cc2.button("✏️", key=f"edit-cat2-{c['id']}"):
                category_dialog(c)
            if cc3.button("🗑️", key=f"del-cat2-{c['id']}"):
                categories.remove(c)
                persist()
                st.rerun()

# ---------------------------------------------------------------------------
# Aba: Assistente (chat com IA sobre os dados do usuário)
# ---------------------------------------------------------------------------
elif tab == "Assistente":
    st.caption("Pergunte sobre seus gastos, saldo e limites — a resposta usa só os dados já cadastrados aqui.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Oi! Sou o assistente do Cofre. Pergunte algo como \"quanto gastei com alimentação esse mês?\"."}
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
                    c = cat_by_id(cid)
                    return c["name"] if c else "Sem categoria"

                def acc_name(aid):
                    a = acc_by_id(aid)
                    return a["name"] if a else "Sem conta"

                recentes = sorted(transactions, key=lambda t: t["date"], reverse=True)[:120]
                linhas = [f"{t['date']} | {t['type']} | {fmt(t['amount'])} | {cat_name(t['categoryId'])} | {acc_name(t['accountId'])} | {t['description']}" for t in recentes]
                contas_str = "; ".join(f"{a['name']} (saldo {fmt(account_balance(a['id']))})" for a in accounts)
                limites_str = "; ".join(f"{c['name']} (limite {fmt(c['budget'])})" for c in categories if c.get("budget")) or "nenhuma"
                contexto = "\n".join([
                    f"Contas: {contas_str}",
                    f"Categorias com limite: {limites_str}",
                    f"Mês selecionado: {month_label} — receitas {fmt(income)}, despesas {fmt(expense)}, saldo total {fmt(saldo_total)}",
                    "Últimos lançamentos (data | tipo | valor | categoria | conta | descrição):",
                    *linhas,
                ])
                prompt = (
                    "Você é o assistente financeiro do app \"Cofre\". Responda em português do Brasil, de forma "
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
