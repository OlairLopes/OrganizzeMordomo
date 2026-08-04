"""Modelo de dados do Fiel Finance (contas, categorias, transações): dados de
exemplo, migração de paleta de cores e consultas simples sobre as coleções.
Funções puras — recebem as coleções (`accounts`/`categories`/`transactions`)
como parâmetro explícito, em vez de fechar sobre variáveis globais, para que
qualquer app (Streamlit, Flet, testes) possa chamá-las sobre seu próprio
estado."""

import calendar
from datetime import date

from .format import uid
from .theme import CAT_COLORS, LEGACY_COLOR_MAP, C


def seed_data():
    """Gera o conjunto de dados de exemplo (contas, categorias e transações)
    usado na primeira execução do app, com datas relativas a hoje."""
    today = date.today()

    def d(day, offset_months=0):
        m = today.month - 1 + offset_months
        y = today.year + m // 12
        m = m % 12 + 1
        day = min(day, calendar.monthrange(y, m)[1])
        return date(y, m, day).isoformat()

    accounts = [
        {"id": "acc-corrente", "name": "Conta Corrente", "type": "conta", "color": C["primary"]},
        {"id": "acc-cartao", "name": "Cartão de Crédito", "type": "cartao", "limit": 3000, "color": C["expense"]},
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


def migrate_legacy_colors(data):
    """Recolore contas/categorias salvas com a paleta antiga (clara) para a
    paleta atual, preservando a mesma cor relativa por item. Modifica `data`
    em memória (in place) e retorna True se algo mudou."""
    changed = False
    for item in data.get("accounts", []) + data.get("categories", []):
        new_color = LEGACY_COLOR_MAP.get(str(item.get("color", "")).upper())
        if new_color:
            item["color"] = new_color
            changed = True
    return changed


def cat_by_id(categories, cid):
    return next((c for c in categories if c["id"] == cid), None)


def acc_by_id(accounts, aid):
    return next((a for a in accounts if a["id"] == aid), None)


def account_balance(transactions, acc_id):
    total = 0.0
    for t in transactions:
        if t["accountId"] == acc_id:
            total += t["amount"] if t["type"] == "receita" else -t["amount"]
    return total
