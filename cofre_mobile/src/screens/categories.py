"""Tela "Categorias" — duas colunas (receitas/despesas), editar/excluir."""

import flet as ft

from components import card
from cofre_core import C, fmt
from dialogs.category_dialog import open_category_dialog


def build_categories(page: ft.Page, state, refresh):
    def new_category(e):
        open_category_dialog(page, state, refresh)

    def edit_category(c):
        open_category_dialog(page, state, refresh, cat=c)

    def delete_category(c):
        state.categories.remove(c)
        state.persist()
        refresh()

    def category_row(c):
        label = c["name"] + (f" · limite {fmt(c['budget'])}" if c.get("budget") else "")
        return card(
            ft.Row(
                [
                    ft.Container(width=10, height=10, border_radius=5, bgcolor=c["color"]),
                    ft.Text(label, size=14.5, weight=ft.FontWeight.W_600, color=C["ink"], expand=True),
                    ft.IconButton(icon=ft.Icons.EDIT, icon_size=16, on_click=lambda e, c=c: edit_category(c)),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_size=16, on_click=lambda e, c=c: delete_category(c)),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
        )

    receitas = [c for c in state.categories if c["kind"] == "receita"]
    despesas = [c for c in state.categories if c["kind"] == "despesa"]

    col_receitas = ft.Column(
        [ft.Text("⬆️ Receitas", size=14, weight=ft.FontWeight.W_700, color=C["income"])]
        + [category_row(c) for c in receitas],
        spacing=8,
        expand=True,
    )
    col_despesas = ft.Column(
        [ft.Text("⬇️ Despesas", size=14, weight=ft.FontWeight.W_700, color=C["expense"])]
        + [category_row(c) for c in despesas],
        spacing=8,
        expand=True,
    )

    return ft.Column(
        [
            ft.FilledButton("＋ Nova categoria", on_click=new_category),
            ft.ResponsiveRow(
                [
                    ft.Container(col_receitas, col={"xs": 12, "sm": 6}),
                    ft.Container(col_despesas, col={"xs": 12, "sm": 6}),
                ],
                spacing=16,
                run_spacing=16,
            ),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
