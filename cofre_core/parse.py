"""Parsing de valores/datas em formato brasileiro e de arquivos de extrato
(CSV/OFX) — funções puras, sem dependência de UI."""

import re


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


def _to_float_br(text):
    m = re.search(r"[\d.,]+", text or "")
    return parse_amount_br(m.group(0)) if m else None


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
