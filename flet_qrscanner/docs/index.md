# Introduction

FletQrscanner for Flet.

## Examples

```
import flet as ft

from flet_qrscanner import FletQrscanner


def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    page.add(

                ft.Container(height=150, width=300, alignment = ft.Alignment.CENTER, bgcolor=ft.Colors.PURPLE_200, content=FletQrscanner(
                    tooltip="My new FletQrscanner Control tooltip",
                    value = "My new FletQrscanner Flet Control",
                ),),

    )


ft.run(main)
```

## Classes

[FletQrscanner](FletQrscanner.md)
