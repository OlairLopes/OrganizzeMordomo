"""Diálogo de leitura de QR code do cupom fiscal (NFC-e) — usa a câmera via
a extensão flet_qrscanner e reaproveita cofre_core.nfce para consultar a
Sefaz, com o mesmo fallback de 3 níveis do app desktop: itens da nota →
valor total → preenchimento manual."""

from datetime import date

import flet as ft
from flet_qrscanner import FletQrscanner

from cofre_core import (
    C,
    NFCE_URL_RE,
    fetch_nfce_receipt,
    fmt,
    parse_amount_br,
    today_iso,
    uid,
)


def open_qrcode_dialog(page: ft.Page, state, on_saved):
    ctx = {"handled_url": None}

    body = ft.Column(spacing=12, tight=True, width=340)

    def close(e=None):
        page.pop_dialog()

    def cats_despesa():
        return [c for c in state.categories if c["kind"] == "despesa"]

    def scanning_controls(message=None):
        scanner = FletQrscanner(on_detect=on_detect, height=280, width=310)
        controls = [
            ft.Text(
                "Aponte a câmera para o QR code do cupom (NFC-e).",
                size=12,
                color=C["ink_soft"],
            ),
            ft.Container(content=scanner, border_radius=10, clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
        ]
        if message:
            controls.append(ft.Text(message, size=12, color=C["expense"]))
        return controls

    def show_scanning(message=None):
        ctx["handled_url"] = None
        body.controls = scanning_controls(message)
        body.update()

    def show_loading():
        body.controls = [
            ft.Row([ft.ProgressRing(width=20, height=20), ft.Text("Consultando nota fiscal...", size=13, color=C["ink"])], spacing=10)
        ]
        body.update()

    def import_items(result, conta_dd, categoria_dd):
        def do_import(e):
            acc_id = conta_dd.value
            cat_id = categoria_dd.value or ""
            data_tx = result["date"] or today_iso()
            for item in result["items"]:
                state.transactions.append(
                    {
                        "id": uid(),
                        "date": data_tx,
                        "description": item["description"],
                        "amount": item["amount"],
                        "type": "despesa",
                        "categoryId": cat_id,
                        "accountId": acc_id,
                    }
                )
            state.persist()
            page.pop_dialog()
            on_saved()

        return do_import

    def show_items_result(result):
        acc_dd = ft.Dropdown(
            label="Conta",
            value=state.accounts[0]["id"] if state.accounts else None,
            options=[ft.DropdownOption(a["id"], text=a["name"]) for a in state.accounts],
        )
        cat_dd = ft.Dropdown(
            label="Categoria (aplicada a todos os itens)",
            options=[ft.DropdownOption(c["id"], text=c["name"]) for c in cats_despesa()],
        )
        items_col = ft.Column(
            [
                ft.Row(
                    [ft.Text(it["description"], size=12, color=C["ink"], expand=True), ft.Text(fmt(it["amount"]), size=12, color=C["ink_soft"])],
                )
                for it in result["items"]
            ],
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            height=180,
        )
        body.controls = [
            ft.Text(f"{len(result['items'])} item(ns) encontrados nesta nota.", size=13, weight=ft.FontWeight.W_600, color=C["income"]),
            items_col,
            ft.Text(f"Total: {fmt(sum(i['amount'] for i in result['items']))}", size=12, color=C["ink_soft"]),
            acc_dd,
            cat_dd,
            ft.FilledButton(
                f"Importar {len(result['items'])} item(ns)",
                on_click=import_items(result, acc_dd, cat_dd),
            ),
        ]
        body.update()

    def show_total_result(result):
        desc_field = ft.TextField(label="Descrição", value="Compra (cupom fiscal)")
        acc_dd = ft.Dropdown(
            label="Conta",
            value=state.accounts[0]["id"] if state.accounts else None,
            options=[ft.DropdownOption(a["id"], text=a["name"]) for a in state.accounts],
        )
        cat_dd = ft.Dropdown(
            label="Categoria",
            options=[ft.DropdownOption(c["id"], text=c["name"]) for c in cats_despesa()],
        )

        def do_import(e):
            state.transactions.append(
                {
                    "id": uid(),
                    "date": result["date"] or today_iso(),
                    "description": desc_field.value or "Compra (cupom fiscal)",
                    "amount": result["total"],
                    "type": "despesa",
                    "categoryId": cat_dd.value or "",
                    "accountId": acc_dd.value,
                }
            )
            state.persist()
            page.pop_dialog()
            on_saved()

        body.controls = [
            ft.Text(
                "Não foi possível obter os itens desta nota (portal do seu estado não é compatível), "
                "mas o valor total foi identificado.",
                size=12,
                color=C["ink_soft"],
            ),
            ft.Text(fmt(result["total"]), size=22, weight=ft.FontWeight.W_700, color=C["ink"]),
            desc_field,
            acc_dd,
            cat_dd,
            ft.FilledButton("Importar despesa", on_click=do_import),
        ]
        body.update()

    def show_manual_fallback():
        desc_field = ft.TextField(label="Descrição", value="Compra (cupom fiscal)")
        valor_field = ft.TextField(label="Valor (R$)", keyboard_type=ft.KeyboardType.NUMBER)
        data_field = ft.TextField(label="Data (AAAA-MM-DD)", value=today_iso())
        acc_dd = ft.Dropdown(
            label="Conta",
            value=state.accounts[0]["id"] if state.accounts else None,
            options=[ft.DropdownOption(a["id"], text=a["name"]) for a in state.accounts],
        )
        cat_dd = ft.Dropdown(
            label="Categoria",
            options=[ft.DropdownOption(c["id"], text=c["name"]) for c in cats_despesa()],
        )
        error_text = ft.Text("", size=12, color=C["expense"])

        def do_import(e):
            valor = parse_amount_br(valor_field.value)
            if valor <= 0 or not acc_dd.value:
                error_text.value = "Informe um valor e uma conta."
                error_text.update()
                return
            state.transactions.append(
                {
                    "id": uid(),
                    "date": data_field.value or today_iso(),
                    "description": desc_field.value or "Compra (cupom fiscal)",
                    "amount": valor,
                    "type": "despesa",
                    "categoryId": cat_dd.value or "",
                    "accountId": acc_dd.value,
                }
            )
            state.persist()
            page.pop_dialog()
            on_saved()

        body.controls = [
            ft.Text(
                "Não consegui consultar essa nota automaticamente (portal fora do ar, "
                "sem conexão ou QR code inválido). Preencha manualmente abaixo.",
                size=12,
                color=C["ink_soft"],
            ),
            desc_field,
            valor_field,
            data_field,
            acc_dd,
            cat_dd,
            error_text,
            ft.FilledButton("Adicionar despesa", on_click=do_import),
        ]
        body.update()

    def on_detect(e):
        url = e.code
        if not url or url == ctx["handled_url"]:
            return
        if not NFCE_URL_RE.match(url):
            return
        ctx["handled_url"] = url
        show_loading()
        try:
            result = fetch_nfce_receipt(url)
        except Exception:
            result = None
        if result and result.get("items"):
            show_items_result(result)
        elif result and result.get("total") is not None:
            show_total_result(result)
        else:
            show_manual_fallback()

    body.controls = scanning_controls()

    dialog = ft.AlertDialog(
        title=ft.Text("Ler QR code do cupom fiscal"),
        content=body,
        actions=[ft.TextButton("Cancelar", on_click=close)],
    )
    page.show_dialog(dialog)
