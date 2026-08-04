from dataclasses import dataclass
from typing import Optional

import flet as ft


@dataclass
class QrScanEvent(ft.Event["FletQrscanner"]):
    """Emitted when a QR/barcode is detected by the camera."""

    code: str
    format: str = ""


@ft.control("FletQrscanner")
class FletQrscanner(ft.LayoutControl):
    """
    Live camera preview that scans QR codes / barcodes using the device
    camera (wraps the Flutter `mobile_scanner` package).
    """

    torch_enabled: bool = False
    camera_facing: str = "back"
    on_detect: Optional[ft.EventHandler[QrScanEvent]] = None
