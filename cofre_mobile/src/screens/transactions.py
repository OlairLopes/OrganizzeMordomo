"""Tela "Transações" — filtros de busca/conta/categoria e lista de
lançamentos do mês selecionado."""

import flet as ft

from components import card, transaction_row
from cofre_core import acc_by_id, cat_by_id, C
from dialogs.tx_dialog import open_tx_dialog


def build_transactions(page: ft.Page, state, refresh):
    _, _, _, month_tx, _, _, _ = state.selected_month()

    busca_field = ft.TextField(hint_text="🔎 Buscar descrição...", dense=True)
    conta_dd = ft.Dropdown(
        hint_text="Todas as contas",
        options=[ft.DropdownOption("", text="Todas as contas")] + [ft.DropdownOption(a["id"], text=a["name"]) for a in state.accounts],
        value="",
        dense=True,
        expand=True,
    )
    cat_dd = ft.Dropdown(
        hint_text="Todas as categorias",
        options=[ft.DropdownOption("", text="Todas as categorias")] + [ft.DropdownOption(c["id"], text=c["name"]) for c in state.categories],
        value="",
        dense=True,
        expand=True,
    )

    list_column = ft.Column(spacing=0)

    def do_edit(t):
        open_tx_dialog(page, state, refresh, tx=t)

    def do_delete(t):
        state.transactions.remove(t)
        state.persist()
        refresh()

    def filtered_rows():
        filtered = month_tx
        busca = (busca_field.value or "").strip().lower()
        if busca:
            filtered = [t for t in filtered if busca in t["description"].lower()]
        if conta_dd.value:
            filtered = [t for t in filtered if t["accountId"] == conta_dd.value]
        if cat_dd.value:
            filtered = [t for t in filtered if t["categoryId"] == cat_dd.value]
        filtered = sorted(filtered, key=lambda t: t["date"], reverse=True)

        if filtered:
            return [
                transaction_row(t, cat_by_id(state.categories, t["categoryId"]), acc_by_id(state.accounts, t["accountId"]), do_edit, do_delete)
                for t in filtered
            ]
        return [ft.Text("Nenhum lançamento encontrado.", size=12, color=C["muted"])]

    def apply_filters(e=None):
        list_column.controls = filtered_rows()
        list_column.update()

    busca_field.on_change = apply_filters
    conta_dd.on_select = apply_filters
    cat_dd.on_select = apply_filters

    list_column.controls = filtered_rows()

    filters_card = card(ft.Column([busca_field, ft.Row([conta_dd, cat_dd], spacing=10)], spacing=10))
    list_card = card(list_column)

    return ft.Column([filters_card, list_card], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
