"""Diálogo de adicionar/editar transação — equivalente ao tx_dialog do
app Streamlit."""

from datetime import date

import flet as ft

from cofre_core import C, parse_amount_br, today_iso, uid


def open_tx_dialog(page: ft.Page, state, on_saved, tx=None):
    is_edit = tx is not None
    error_text = ft.Text("", color=C["expense"], size=12)

    tipo_dd = ft.Dropdown(
        label="Tipo",
        value=tx["type"] if is_edit else "despesa",
        options=[
            ft.DropdownOption("despesa", text="Despesa"),
            ft.DropdownOption("receita", text="Receita"),
        ],
    )
    desc_field = ft.TextField(label="Descrição", value=tx["description"] if is_edit else "")
    valor_field = ft.TextField(
        label="Valor (R$)",
        value=f"{tx['amount']:.2f}".replace(".", ",") if is_edit else "",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    data_field = ft.TextField(
        label="Data (AAAA-MM-DD)",
        value=tx["date"] if is_edit else today_iso(),
    )

    def cats_for(kind):
        return [c for c in state.categories if c["kind"] == kind]

    cat_dd = ft.Dropdown(
        label="Categoria",
        value=tx["categoryId"] if is_edit else None,
        options=[ft.DropdownOption(c["id"], text=c["name"]) for c in cats_for(tipo_dd.value)],
    )

    def on_tipo_change(e):
        cat_dd.options = [ft.DropdownOption(c["id"], text=c["name"]) for c in cats_for(tipo_dd.value)]
        cat_dd.value = None
        cat_dd.update()

    tipo_dd.on_select = on_tipo_change

    acc_dd = ft.Dropdown(
        label="Conta",
        value=tx["accountId"] if is_edit else (state.accounts[0]["id"] if state.accounts else None),
        options=[ft.DropdownOption(a["id"], text=a["name"]) for a in state.accounts],
    )

    def close(e=None):
        page.pop_dialog()

    def save(e):
        valor = parse_amount_br(valor_field.value)
        if not desc_field.value or valor <= 0 or not acc_dd.value:
            error_text.value = "Preencha descrição, valor e conta."
            error_text.update()
            return
        new_tx = {
            "id": tx["id"] if is_edit else uid(),
            "type": tipo_dd.value,
            "description": desc_field.value,
            "amount": valor,
            "date": data_field.value or today_iso(),
            "categoryId": cat_dd.value or "",
            "accountId": acc_dd.value,
        }
        if is_edit:
            idx = next(i for i, t in enumerate(state.transactions) if t["id"] == tx["id"])
            state.transactions[idx] = new_tx
        else:
            state.transactions.append(new_tx)
        state.persist()
        page.pop_dialog()
        on_saved()

    dialog = ft.AlertDialog(
        title=ft.Text("Transação"),
        content=ft.Column(
            [tipo_dd, desc_field, valor_field, data_field, cat_dd, acc_dd, error_text],
            tight=True,
            spacing=10,
            width=340,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=close),
            ft.FilledButton("Salvar", on_click=save),
        ],
    )
    page.show_dialog(dialog)
