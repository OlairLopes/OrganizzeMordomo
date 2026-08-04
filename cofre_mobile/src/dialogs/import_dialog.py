"""Diálogo de importação de extrato (CSV/OFX) — equivalente ao import_dialog
do app Streamlit, mas usando csv.DictReader da stdlib em vez de pandas
(pandas é pesado demais para empacotar no celular)."""

import csv
import io

import flet as ft

from cofre_core import C, decode_upload, fmt, parse_amount_br, parse_date_flexible, parse_ofx, uid


def open_import_dialog(page: ft.Page, state, on_saved):
    ctx = {"rows": None, "raw_text": None, "columns": None}

    body = ft.Column(spacing=12, tight=True, width=340)
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    def close(e=None):
        if file_picker in page.overlay:
            page.overlay.remove(file_picker)
        page.pop_dialog()

    def guess(cols, cands):
        for c in cols:
            if any(k in c.lower() for k in cands):
                return c
        return cols[0]

    def pick_controls(message=None):
        controls = [
            ft.Text("Envie um arquivo CSV ou OFX exportado do seu banco.", size=12, color=C["ink_soft"]),
            ft.FilledButton("Selecionar arquivo", on_click=pick_file),
        ]
        if message:
            controls.append(ft.Text(message, size=12, color=C["expense"]))
        return controls

    def show_pick_button(message=None):
        ctx["rows"] = None
        body.controls = pick_controls(message)
        body.update()

    def show_column_pickers(cols):
        date_dd = ft.Dropdown(label="Coluna de data", value=guess(cols, ["data", "date"]), options=[ft.DropdownOption(c) for c in cols])
        desc_dd = ft.Dropdown(label="Coluna de descrição", value=guess(cols, ["descri", "histor", "memo"]), options=[ft.DropdownOption(c) for c in cols])
        amount_dd = ft.Dropdown(label="Coluna de valor", value=guess(cols, ["valor", "amount"]), options=[ft.DropdownOption(c) for c in cols])

        def do_preview(e):
            reader = csv.DictReader(io.StringIO(ctx["raw_text"]))
            preview_rows = []
            skipped = 0
            for row in reader:
                dt = parse_date_flexible(row.get(date_dd.value, ""))
                amt_raw = row.get(amount_dd.value, "")
                amt = parse_amount_br(amt_raw)
                if dt and str(amt_raw).strip():
                    preview_rows.append({"date": dt, "description": row.get(desc_dd.value, ""), "amount": amt})
                else:
                    skipped += 1
            ctx["rows"] = preview_rows
            show_preview(skipped)

        body.controls = [date_dd, desc_dd, amount_dd, ft.FilledButton("Pré-visualizar", on_click=do_preview)]
        body.update()

    def show_preview(skipped=0):
        rows = ctx["rows"]
        if not rows:
            show_pick_button("Nenhum lançamento válido encontrado no arquivo.")
            return
        acc_dd = ft.Dropdown(
            label="Importar para a conta",
            value=state.accounts[0]["id"] if state.accounts else None,
            options=[ft.DropdownOption(a["id"], text=a["name"]) for a in state.accounts],
        )

        def do_import(e):
            acc_id = acc_dd.value
            for r in rows:
                state.transactions.append(
                    {
                        "id": uid(),
                        "date": r["date"],
                        "description": r["description"] or "Lançamento importado",
                        "amount": abs(r["amount"]),
                        "type": "despesa" if r["amount"] < 0 else "receita",
                        "categoryId": "",
                        "accountId": acc_id,
                    }
                )
            state.persist()
            close()
            on_saved()

        rows_col = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(r["date"], size=11, color=C["ink_soft"], width=80),
                        ft.Text(r["description"], size=12, color=C["ink"], expand=True),
                        ft.Text(fmt(r["amount"]), size=12, color=C["income"] if r["amount"] >= 0 else C["expense"]),
                    ]
                )
                for r in rows
            ],
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            height=200,
        )
        controls = [ft.Text(f"{len(rows)} lançamento(s) encontrado(s)", size=13, weight=ft.FontWeight.W_600, color=C["income"])]
        if skipped:
            controls.append(ft.Text(f"{skipped} linha(s) ignorada(s) por falta de data ou valor válido.", size=11, color=C["warn"]))
        controls += [rows_col, acc_dd, ft.FilledButton("Importar", on_click=do_import)]
        body.controls = controls
        body.update()

    async def pick_file(e):
        files = await file_picker.pick_files(
            dialog_title="Selecionar extrato",
            allowed_extensions=["csv", "ofx", "txt"],
            file_type=ft.FilePickerFileType.CUSTOM,
            with_data=True,
        )
        if not files:
            return
        f = files[0]
        if not f.bytes:
            show_pick_button("Não foi possível ler o arquivo selecionado.")
            return
        text = decode_upload(f.bytes)
        ext = (f.name or "").split(".")[-1].lower()
        if ext == "ofx":
            ctx["rows"] = parse_ofx(text)
            show_preview()
        else:
            ctx["raw_text"] = text
            try:
                reader = csv.reader(io.StringIO(text))
                cols = next(reader)
            except StopIteration:
                show_pick_button("Arquivo CSV vazio.")
                return
            ctx["columns"] = cols
            show_column_pickers(cols)

    body.controls = pick_controls()

    dialog = ft.AlertDialog(
        title=ft.Text("Importar extrato"),
        content=body,
        actions=[ft.TextButton("Cancelar", on_click=close)],
    )
    page.show_dialog(dialog)
