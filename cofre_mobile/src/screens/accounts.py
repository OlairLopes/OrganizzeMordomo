"""Tela "Contas" — cartões de conta/cartão com saldo, editar/excluir."""

import flet as ft

from components import card
from cofre_core import C, account_balance, fmt
from dialogs.account_dialog import open_account_dialog


def build_accounts(page: ft.Page, state, refresh):
    def new_account(e):
        open_account_dialog(page, state, refresh)

    def edit_account(a):
        open_account_dialog(page, state, refresh, acc=a)

    def delete_account(a):
        state.accounts.remove(a)
        state.persist()
        refresh()

    cards = []
    for a in state.accounts:
        icon = "💳" if a["type"] == "cartao" else "🏦"
        bal = account_balance(state.transactions, a["id"])
        bal_color = C["expense"] if bal < 0 else C["ink"]
        extra = []
        if a["type"] == "cartao" and a.get("limit"):
            extra.append(ft.Text(f"Limite: {fmt(a['limit'])}", size=12, color=C["muted"]))
        cards.append(
            ft.Container(
                card(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(icon, size=18),
                                    ft.Column(
                                        [
                                            ft.Text(a["name"], size=15, weight=ft.FontWeight.W_700, color=C["ink"]),
                                            ft.Text("Cartão de crédito" if a["type"] == "cartao" else "Conta", size=12, color=C["muted"]),
                                        ],
                                        spacing=0,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Text(fmt(bal), size=22, weight=ft.FontWeight.W_600, color=bal_color, font_family="monospace"),
                            *extra,
                            ft.Row(
                                [
                                    ft.OutlinedButton("Editar", on_click=lambda e, a=a: edit_account(a), expand=True),
                                    ft.OutlinedButton("Excluir", on_click=lambda e, a=a: delete_account(a), expand=True),
                                ],
                                spacing=8,
                            ),
                        ],
                        spacing=8,
                    )
                ),
                col={"xs": 12, "sm": 6},
            )
        )

    return ft.Column(
        [
            ft.FilledButton("＋ Nova conta", on_click=new_account),
            ft.ResponsiveRow(cards, spacing=10, run_spacing=10),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
