"""Componentes reutilizáveis (equivalentes aos cartões/linhas do app
Streamlit) usados pelas telas do app Flet."""

import flet as ft

from cofre_core import C


def card(content, padding=16):
    """Container com a mesma linguagem visual dos cartões do Streamlit
    (fundo `surface`, cantos arredondados, sem borda forte)."""
    return ft.Container(
        content=content,
        bgcolor=C["surface"],
        border_radius=16,
        padding=padding,
        border=ft.Border.all(1, C["surface_soft"]),
    )


def stat_tile(label, value, icon=None, accent=None, hint=None):
    accent = accent or C["primary"]
    children = [
        ft.Row(
            [
                ft.Text(icon, size=15) if icon else ft.Container(width=0),
                ft.Text(label.upper(), size=12, weight=ft.FontWeight.W_600, color=C["muted"]),
            ],
            spacing=6,
        ),
        ft.Text(value, size=24, weight=ft.FontWeight.W_600, color=C["ink"], font_family="monospace"),
    ]
    if hint:
        children.append(ft.Text(hint, size=12, weight=ft.FontWeight.W_600, color=accent))
    return card(ft.Column(children, spacing=6, tight=True))


def amount_text(value, is_income, size=14):
    color = C["income"] if is_income else C["expense"]
    sign = "+" if is_income else "-"
    from cofre_core import fmt
    return ft.Text(f"{sign}{fmt(value)}", color=color, weight=ft.FontWeight.W_600, size=size, font_family="monospace")


def color_dot(color, size=10):
    return ft.Container(width=size, height=size, border_radius=size / 2, bgcolor=color)


def transaction_row(t, cat, acc, on_edit, on_delete):
    is_income = t["type"] == "receita"
    dot_color = cat["color"] if cat else C["muted"]
    subtitle = f"{t['date']} · {cat['name'] if cat else 'Sem categoria'} · {acc['name'] if acc else 'Sem conta'}"
    return ft.Container(
        padding=ft.Padding.symmetric(vertical=8, horizontal=0),
        content=ft.Row(
            [
                ft.Container(width=3, height=36, bgcolor=dot_color, border_radius=2),
                ft.Column(
                    [
                        ft.Text(t["description"], size=14.5, weight=ft.FontWeight.W_600, color=C["ink"]),
                        ft.Text(subtitle, size=12, color=C["muted"]),
                    ],
                    spacing=2,
                    expand=True,
                ),
                amount_text(t["amount"], is_income),
                ft.IconButton(icon=ft.Icons.EDIT, icon_size=16, on_click=lambda e: on_edit(t)),
                ft.IconButton(icon=ft.Icons.DELETE, icon_size=16, on_click=lambda e: on_delete(t)),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
