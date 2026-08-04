"""Paleta de cores e constantes de exibição do Fiel Finance — apenas dados, sem
nenhuma dependência de UI, compartilhados pelo app Streamlit (desktop/web) e
pelo app Flet (mobile).
"""

# Paleta "vault": fundo grafite-esverdeado escuro, esmeralda como cor de marca,
# dourado como acento de destaque. Conjunto categórico validado com
# scripts/validate_palette.js do skill de dataviz (CVD-safe em fundo escuro).
C = {
    "bg": "#0A0F0D",
    "bg_soft": "#0D1512",
    "surface": "#111A17",
    "surface_soft": "#182420",
    "ink": "#F4F7F5",
    "ink_soft": "#B7C3BE",
    "muted": "#7C8983",
    "line": "rgba(255,255,255,0.08)",
    "line_strong": "rgba(255,255,255,0.16)",
    "primary": "#1EAE76",
    "primary_bright": "#2BD696",
    "gold": "#E8B84B",
    "income": "#199E70",
    "expense": "#E66767",
    "warn": "#E8B84B",
}

CAT_COLORS = ["#3987E5", "#D95926", "#199E70", "#C98500", "#D55181", "#43C97A", "#9085E9", "#E66767"]

# Cores antigas (paleta clara) -> novas, para recolorir dados já salvos sem quebrar identidade.
LEGACY_COLOR_MAP = {
    "#145C43": "#3987E5", "#B5482A": "#D95926", "#B8860B": "#199E70", "#4B6FA8": "#C98500",
    "#7A4F9E": "#D55181", "#2F8F5B": "#43C97A", "#8A5A3C": "#9085E9", "#5C7A8A": "#E66767",
}

MONTHS_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
             "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
