"""Leitura de QR code de cupom fiscal (NFC-e): extração da chave de acesso e
busca/parse da página de consulta pública da Sefaz. Depende apenas de
`requests`/`beautifulsoup4` (puro Python, portátil) — a decodificação da
imagem do QR code em si é específica de cada app (desktop usa `cv2`; mobile
usa uma extensão nativa) e não mora aqui."""

import re

from .parse import _to_float_br, parse_amount_br, parse_date_flexible

NFCE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def extract_chave_acesso(url):
    """Extrai a chave de acesso (44 dígitos) de uma URL de QR code de NFC-e,
    tanto no formato com parâmetros nomeados (chNFe=...) quanto no formato
    compacto (?p=CHAVE|versao|ambiente|hash)."""
    m = re.search(r"[?&](?:chNFe|chnfe)=(\d{44})", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]p=(\d{44})", url)
    if m:
        return m.group(1)
    m = re.search(r"(\d{44})", url)
    return m.group(1) if m else None


def fetch_nfce_receipt(url):
    """Busca e interpreta a página de consulta pública da NFC-e (portal da
    Sefaz do estado emissor) a partir da URL do QR code.

    Vários estados usam um template compartilhado (tabela #tabResult com
    spans .txtTit/.Rqtd/.RvlUnit por item, total em #linhaTotal, chave em
    span.chave) — quando o portal do estado emissor segue esse padrão,
    retornamos os itens um a um; caso contrário, tentamos ao menos obter o
    valor total via busca textual. Retorna um dict com chaves 'items'
    (lista, pode ser vazia), 'total' (float ou None) e 'date' (str ISO ou
    None). Levanta exceção em caso de falha de rede."""
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(
        url, timeout=12,
        headers={"User-Agent": "Mozilla/5.0 (compatible; FielFinanceApp/1.0)"},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    table = soup.find("table", id="tabResult")
    if table:
        nomes = [s.get_text(strip=True) for s in table.select("span.txtTit")]
        qtds = [s.get_text(strip=True) for s in table.select("span.Rqtd")]
        valores_unit = [s.get_text(strip=True) for s in table.select("span.RvlUnit")]
        for i, nome in enumerate(nomes):
            qtd = _to_float_br(qtds[i]) if i < len(qtds) else None
            v_unit = _to_float_br(valores_unit[i]) if i < len(valores_unit) else None
            if not nome or v_unit is None:
                continue
            qtd = qtd or 1.0
            items.append({
                "description": nome,
                "amount": round(qtd * v_unit, 2),
            })

    total = None
    total_div = soup.find("div", id="linhaTotal")
    if total_div:
        total_span = total_div.find("span")
        if total_span:
            total = _to_float_br(total_span.get_text(strip=True))
    if total is None:
        m = re.search(r"Valor\s+a\s+pagar[^\d]{0,20}R?\$?\s*([\d.,]+)", resp.text, re.IGNORECASE)
        if not m:
            m = re.search(r"Valor\s+total[^\d]{0,20}R?\$?\s*([\d.,]+)", resp.text, re.IGNORECASE)
        if m:
            total = parse_amount_br(m.group(1))

    date_iso = None
    info_list = soup.find("ul", class_="ui-listview")
    if info_list:
        first_li = info_list.find("li")
        if first_li:
            m = re.search(r"(\d{2}/\d{2}/\d{4})", first_li.get_text())
            if m:
                date_iso = parse_date_flexible(m.group(1))
    if date_iso is None:
        m = re.search(r"(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}:\d{2}", resp.text)
        if m:
            date_iso = parse_date_flexible(m.group(1))

    return {"items": items, "total": total, "date": date_iso}
