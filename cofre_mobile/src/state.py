"""Estado do app: carrega/salva os dados locais (cofre_data.json no
diretório de armazenamento do Flet) e calcula o mês selecionado, espelhando
a lógica do app Streamlit (cofre_app.py)."""

import os
from datetime import date

from cofre_core import load_data_core, month_key, save_data_core


def data_file_path():
    base = os.environ.get("FLET_APP_STORAGE_DATA") or "."
    return os.path.join(base, "cofre_data.json")


MONTHS_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
             "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


class AppState:
    def __init__(self):
        self.path = data_file_path()
        result = load_data_core(self.path)
        self.data = result.data
        self.warning = result.warning
        self.month_offset = 0

    @property
    def accounts(self):
        return self.data["accounts"]

    @property
    def categories(self):
        return self.data["categories"]

    @property
    def transactions(self):
        return self.data["transactions"]

    def persist(self):
        save_data_core(self.path, self.data)

    def selected_month(self):
        """Retorna (selected_key "YYYY-MM", month_label, month_tx, income, expense, saldo_total)."""
        base = date.today().replace(day=1)
        m = base.month - 1 + self.month_offset
        y = base.year + m // 12
        m = m % 12 + 1
        selected_date = date(y, m, 1)
        selected_key = f"{y:04d}-{m:02d}"
        month_label = f"{MONTHS_PT[m - 1]} de {y}"

        month_tx = [t for t in self.transactions if month_key(t["date"]) == selected_key]
        income = sum(t["amount"] for t in month_tx if t["type"] == "receita")
        expense = sum(t["amount"] for t in month_tx if t["type"] == "despesa")
        saldo_total = sum(
            t["amount"] if t["type"] == "receita" else -t["amount"] for t in self.transactions
        )
        return selected_date, selected_key, month_label, month_tx, income, expense, saldo_total
