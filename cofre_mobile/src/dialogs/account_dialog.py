"""Diálogo de adicionar/editar conta — equivalente ao account_dialog do
app Streamlit."""

import flet as ft

from cofre_core import CAT_COLORS, parse_amount_br, uid


def open_account_dialog(page: ft.Page, state, on_saved, acc=None):
    is_edit = acc is not None
    error_text = ft.Text("", color="#E66767", size=12)

    nome_field = ft.TextField(label="Nome", value=acc["name"] if is_edit else "")
    tipo_dd = ft.Dropdown(
        label="Tipo",
        value=acc["type"] if is_edit else "conta",
        options=[
            ft.DropdownOption("conta", text="Conta"),
            ft.DropdownOption("cartao", text="Cartão de crédito"),
        ],
    )
    limite_field = ft.TextField(
        label="Limite (R$)",
        value=(f"{acc.get('limit', 0):.2f}".replace(".", ",") if is_edit else ""),
        keyboard_type=ft.KeyboardType.NUMBER,
        visible=is_edit and acc["type"] == "cartao",
    )

    def on_tipo_change(e):
        limite_field.visible = tipo_dd.value == "cartao"
        limite_field.update()

    tipo_dd.on_select = on_tipo_change

    def close(e=None):
        page.pop_dialog()

    def save(e):
        if not nome_field.value:
            error_text.value = "Informe um nome."
            error_text.update()
            return
        new_acc = {
            "id": acc["id"] if is_edit else uid(),
            "name": nome_field.value,
            "type": tipo_dd.value,
            "color": acc["color"] if is_edit else CAT_COLORS[len(state.accounts) % len(CAT_COLORS)],
        }
        if tipo_dd.value == "cartao":
            new_acc["limit"] = parse_amount_br(limite_field.value)
        if is_edit:
            idx = next(i for i, a in enumerate(state.accounts) if a["id"] == acc["id"])
            state.accounts[idx] = new_acc
        else:
            state.accounts.append(new_acc)
        state.persist()
        page.pop_dialog()
        on_saved()

    dialog = ft.AlertDialog(
        title=ft.Text("Conta"),
        content=ft.Column([nome_field, tipo_dd, limite_field, error_text], tight=True, spacing=10, width=320),
        actions=[
            ft.TextButton("Cancelar", on_click=close),
            ft.FilledButton("Salvar", on_click=save),
        ],
    )
    page.show_dialog(dialog)
