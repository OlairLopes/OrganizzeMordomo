"""Diálogo de adicionar/editar categoria — equivalente ao category_dialog do
app Streamlit."""

import flet as ft

from cofre_core import CAT_COLORS, parse_amount_br, uid


def open_category_dialog(page: ft.Page, state, on_saved, cat=None):
    is_edit = cat is not None
    error_text = ft.Text("", color="#E66767", size=12)

    nome_field = ft.TextField(label="Nome", value=cat["name"] if is_edit else "")
    kind_dd = ft.Dropdown(
        label="Tipo",
        value=cat["kind"] if is_edit else "despesa",
        options=[
            ft.DropdownOption("despesa", text="Despesa"),
            ft.DropdownOption("receita", text="Receita"),
        ],
    )
    budget_field = ft.TextField(
        label="Limite mensal (opcional)",
        value=(f"{cat.get('budget', 0):.2f}".replace(".", ",") if is_edit and cat.get("budget") else ""),
        keyboard_type=ft.KeyboardType.NUMBER,
        visible=(not is_edit) or cat["kind"] == "despesa",
    )

    def on_kind_change(e):
        budget_field.visible = kind_dd.value == "despesa"
        budget_field.update()

    kind_dd.on_select = on_kind_change

    def close(e=None):
        page.pop_dialog()

    def save(e):
        if not nome_field.value:
            error_text.value = "Informe um nome."
            error_text.update()
            return
        new_cat = {
            "id": cat["id"] if is_edit else uid(),
            "name": nome_field.value,
            "kind": kind_dd.value,
            "color": cat["color"] if is_edit else CAT_COLORS[len(state.categories) % len(CAT_COLORS)],
        }
        if kind_dd.value == "despesa" and budget_field.value:
            budget = parse_amount_br(budget_field.value)
            if budget:
                new_cat["budget"] = budget
        if is_edit:
            idx = next(i for i, c in enumerate(state.categories) if c["id"] == cat["id"])
            state.categories[idx] = new_cat
        else:
            state.categories.append(new_cat)
        state.persist()
        page.pop_dialog()
        on_saved()

    dialog = ft.AlertDialog(
        title=ft.Text("Categoria"),
        content=ft.Column([nome_field, kind_dd, budget_field, error_text], tight=True, spacing=10, width=320),
        actions=[
            ft.TextButton("Cancelar", on_click=close),
            ft.FilledButton("Salvar", on_click=save),
        ],
    )
    page.show_dialog(dialog)
