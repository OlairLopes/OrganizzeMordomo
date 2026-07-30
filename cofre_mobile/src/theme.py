"""Tema escuro "vault" do Cofre para o app Flet, construído a partir da
mesma paleta usada no app Streamlit (cofre_core.theme.C)."""

import flet as ft

from cofre_core import C

ON_PRIMARY = "#062015"


def build_theme():
    return ft.Theme(
        color_scheme_seed=C["primary"],
        use_material3=True,
        scaffold_bgcolor=C["bg"],
        card_bgcolor=C["surface"],
        divider_color=C["surface_soft"],
        color_scheme=ft.ColorScheme(
            primary=C["primary"],
            on_primary=ON_PRIMARY,
            primary_container=C["surface_soft"],
            on_primary_container=C["ink"],
            secondary=C["gold"],
            on_secondary=ON_PRIMARY,
            error=C["expense"],
            on_error="#2B0000",
            surface=C["surface"],
            on_surface=C["ink"],
            on_surface_variant=C["ink_soft"],
            surface_container=C["surface_soft"],
            surface_container_high=C["surface_soft"],
            surface_container_highest=C["surface_soft"],
            surface_container_low=C["surface"],
            surface_container_lowest=C["bg"],
            outline=C["surface_soft"],
            outline_variant=C["surface_soft"],
            inverse_surface=C["ink"],
            on_inverse_surface=C["surface"],
        ),
        navigation_bar_theme=ft.NavigationBarTheme(
            bgcolor=C["bg_soft"],
            indicator_color=C["primary"],
        ),
    )
