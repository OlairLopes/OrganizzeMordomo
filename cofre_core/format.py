"""Formatação e geração de identificadores — funções puras, sem dependência de UI."""

import uuid
from datetime import date


def fmt(n):
    """Formata um número como moeda BRL: "R$ 1.234,56" / "-R$ 1.234,56"."""
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
