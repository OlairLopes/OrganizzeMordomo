"""Tela "Visão Geral" — KPIs, gráfico de despesas por categoria, tendência
de 6 meses, limites de gastos e últimos lançamentos."""

import flet as ft
import flet_charts as fc

from components import amount_text, card, stat_tile, transaction_row
from cofre_core import C, acc_by_id, cat_by_id, fmt, month_key
from dialogs.tx_dialog import open_tx_dialog

MONTHS_PT_SHORT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                    "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def build_overview(page: ft.Page, state, refresh):
    selected_date, selected_key, month_label, month_tx, income, expense, saldo_total = state.selected_month()
    net = income - expense

    kpis = ft.ResponsiveRow(
        [
            ft.Container(stat_tile("Saldo total", fmt(saldo_total), "🔐", C["gold"]), col=6),
            ft.Container(stat_tile("Receitas do mês", fmt(income), "⬆️", C["income"]), col=6),
            ft.Container(stat_tile("Despesas do mês", fmt(expense), "⬇️", C["expense"]), col=6),
            ft.Container(
                stat_tile(
                    "Resultado do mês", fmt(net), "✨",
                    C["income"] if net >= 0 else C["expense"],
                    hint=("↑ positivo este mês" if net >= 0 else "↓ atenção: no vermelho"),
                ),
                col=6,
            ),
        ],
        spacing=10,
        run_spacing=10,
    )

    # --- Despesas por categoria (pizza) ---
    exp_by_cat = {}
    for t in month_tx:
        if t["type"] == "despesa":
            exp_by_cat[t["categoryId"]] = exp_by_cat.get(t["categoryId"], 0) + t["amount"]

    if exp_by_cat:
        total_exp = sum(exp_by_cat.values()) or 1
        sections = []
        legend_rows = []
        for cid, val in sorted(exp_by_cat.items(), key=lambda kv: kv[1], reverse=True):
            c = cat_by_id(state.categories, cid)
            name = c["name"] if c else "Sem categoria"
            color = c["color"] if c else C["muted"]
            pct = val / total_exp * 100
            sections.append(fc.PieChartSection(value=val, color=color, title=f"{pct:.0f}%", radius=70))
            legend_rows.append(
                ft.Row(
                    [
                        ft.Container(width=9, height=9, border_radius=5, bgcolor=color),
                        ft.Text(name, size=12, color=C["ink_soft"]),
                    ],
                    spacing=6,
                )
            )
        pie_card = card(
            ft.Column(
                [
                    ft.Text("🥧 Despesas por categoria", size=13, weight=ft.FontWeight.W_600, color=C["ink"]),
                    fc.PieChart(sections=sections, sections_space=2, center_space_radius=40, height=220),
                    ft.Row(legend_rows, wrap=True, spacing=14, run_spacing=6),
                ],
                spacing=10,
            )
        )
    else:
        pie_card = card(
            ft.Column(
                [
                    ft.Text("🥧 Despesas por categoria", size=13, weight=ft.FontWeight.W_600, color=C["ink"]),
                    ft.Text("Nenhuma despesa neste mês ainda.", size=12, color=C["muted"]),
                ]
            )
        )

    # --- Receitas x despesas (6 meses) ---
    groups = []
    labels = []
    max_val = 1
    for i in range(5, -1, -1):
        mo = selected_date.month - 1 - i
        yr = selected_date.year + mo // 12
        mo = mo % 12 + 1
        key = f"{yr:04d}-{mo:02d}"
        txs = [t for t in state.transactions if month_key(t["date"]) == key]
        inc = sum(t["amount"] for t in txs if t["type"] == "receita")
        exp = sum(t["amount"] for t in txs if t["type"] == "despesa")
        max_val = max(max_val, inc, exp)
        idx = 5 - i
        labels.append(MONTHS_PT_SHORT[mo - 1])
        groups.append(
            fc.BarChartGroup(
                x=idx,
                rods=[
                    fc.BarChartRod(to_y=inc, color=C["income"], width=10, border_radius=4),
                    fc.BarChartRod(to_y=exp, color=C["expense"], width=10, border_radius=4),
                ],
                spacing=4,
            )
        )
    bar_card = card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("📈 Receitas x despesas (6 meses)", size=13, weight=ft.FontWeight.W_600, color=C["ink"]),
                    ]
                ),
                ft.Row(
                    [
                        ft.Row([ft.Container(width=9, height=9, border_radius=5, bgcolor=C["income"]), ft.Text("Receitas", size=11, color=C["ink_soft"])], spacing=4),
                        ft.Row([ft.Container(width=9, height=9, border_radius=5, bgcolor=C["expense"]), ft.Text("Despesas", size=11, color=C["ink_soft"])], spacing=4),
                    ],
                    spacing=14,
                ),
                fc.BarChart(
                    groups=groups,
                    max_y=max_val * 1.15,
                    height=220,
                    bottom_axis=fc.ChartAxis(
                        labels=[fc.ChartAxisLabel(value=i, label=labels[i]) for i in range(6)],
                        label_size=24,
                    ),
                    left_axis=fc.ChartAxis(show_labels=True, label_size=52),
                    horizontal_grid_lines=fc.ChartGridLines(color=C["surface_soft"], width=1),
                ),
            ],
            spacing=10,
        )
    )

    charts_row = ft.ResponsiveRow(
        [ft.Container(pie_card, col=12), ft.Container(bar_card, col=12)],
        spacing=10,
        run_spacing=10,
    )

    # --- Limites de gastos ---
    budget_cats = [c for c in state.categories if c["kind"] == "despesa" and c.get("budget")]
    budget_rows = []
    for c in budget_cats:
        spent = sum(t["amount"] for t in month_tx if t["categoryId"] == c["id"])
        pct = min(spent / c["budget"], 1.0) if c["budget"] else 0.0
        bar_color = C["expense"] if pct >= 1 else (C["gold"] if pct >= 0.8 else C["primary"])
        budget_rows.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Container(width=8, height=8, border_radius=4, bgcolor=c["color"]),
                                    ft.Text(c["name"], size=14, weight=ft.FontWeight.W_600, color=C["ink"]),
                                ],
                                spacing=6,
                            ),
                            ft.Text(f"{fmt(spent)} / {fmt(c['budget'])}", size=12, color=C["ink_soft"], font_family="monospace"),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.ProgressBar(value=pct, color=bar_color, bgcolor=C["surface_soft"], height=8, border_radius=4),
                ],
                spacing=6,
            )
        )
    budgets_card = (
        card(ft.Column([ft.Text("🎯 Limites de gastos", size=13, weight=ft.FontWeight.W_600, color=C["ink"])] + budget_rows, spacing=12))
        if budget_rows else None
    )

    # --- Últimos lançamentos ---
    def do_edit(t):
        open_tx_dialog(page, state, refresh, tx=t)

    def do_delete(t):
        state.transactions.remove(t)
        state.persist()
        refresh()

    recent = sorted(month_tx, key=lambda t: t["date"], reverse=True)[:6]
    recent_rows = [
        transaction_row(t, cat_by_id(state.categories, t["categoryId"]), acc_by_id(state.accounts, t["accountId"]), do_edit, do_delete)
        for t in recent
    ] or [ft.Text("Nenhum lançamento neste mês ainda.", size=12, color=C["muted"])]
    recent_card = card(ft.Column([ft.Text("🕒 Últimos lançamentos", size=13, weight=ft.FontWeight.W_600, color=C["ink"])] + recent_rows, spacing=4))

    content = [kpis, charts_row]
    if budgets_card:
        content.append(budgets_card)
    content.append(recent_card)

    return ft.Column(content, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
