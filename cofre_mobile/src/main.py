import flet as ft

from cofre_core import C
from dialogs.tx_dialog import open_tx_dialog
from screens.accounts import build_accounts
from screens.categories import build_categories
from screens.overview import build_overview
from screens.transactions import build_transactions
from state import AppState
from theme import build_theme

TABS = [
    ("Visão Geral", ft.Icons.DASHBOARD_OUTLINED, ft.Icons.DASHBOARD, build_overview),
    ("Transações", ft.Icons.SWAP_HORIZ_OUTLINED, ft.Icons.SWAP_HORIZ, build_transactions),
    ("Contas", ft.Icons.ACCOUNT_BALANCE_OUTLINED, ft.Icons.ACCOUNT_BALANCE, build_accounts),
    ("Categorias", ft.Icons.LABEL_OUTLINE, ft.Icons.LABEL, build_categories),
]


def main(page: ft.Page):
    page.title = "Cofre"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = build_theme()
    page.dark_theme = build_theme()
    page.bgcolor = C["bg"]
    page.padding = 0

    state = AppState()
    selected = {"index": 0}

    body = ft.Column(expand=True)
    month_label_text = ft.Text("", size=14, weight=ft.FontWeight.W_600, color=C["ink"])

    def refresh():
        _, _, _, builder = TABS[selected["index"]]
        _, _, month_label, *_ = state.selected_month()
        month_label_text.value = month_label
        body.controls = [
            ft.Container(
                content=builder(page, state, refresh),
                padding=ft.Padding.all(14),
                expand=True,
            )
        ]
        page.update()

    def prev_month(e):
        state.month_offset -= 1
        refresh()

    def next_month(e):
        state.month_offset += 1
        refresh()

    def new_transaction(e):
        open_tx_dialog(page, state, refresh)

    def on_nav_change(e):
        selected["index"] = e.control.selected_index
        refresh()

    page.appbar = ft.AppBar(
        title=ft.Text("Cofre", weight=ft.FontWeight.W_700),
        center_title=False,
        bgcolor=C["bg_soft"],
        actions=[
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=prev_month),
            ft.Container(content=month_label_text, padding=ft.Padding.only(top=12)),
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=next_month),
            ft.Container(width=8),
        ],
    )
    page.floating_action_button = ft.FloatingActionButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.ADD, color="#062015"), ft.Text("Nova transação", color="#062015", weight=ft.FontWeight.W_600)],
            tight=True,
            spacing=6,
        ),
        on_click=new_transaction,
        bgcolor=C["primary"],
    )
    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=icon, selected_icon=sel_icon, label=label)
            for label, icon, sel_icon, _ in TABS
        ],
        selected_index=0,
        on_change=on_nav_change,
    )
    page.add(ft.SafeArea(expand=True, content=body))
    refresh()


if __name__ == "__main__":
    ft.run(main)
