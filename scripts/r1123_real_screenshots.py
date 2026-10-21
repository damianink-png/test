"""Real Qt screenshots taken from DS Compare R11.23, not generated mockups.

Runs actual gui46.Window on Windows CI after the full R11.23 source patch
sequence. Captures the actual live QWidgets for each tab in both UI themes.
"""
from __future__ import annotations

import json
from pathlib import Path
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from dsac29.gui46 import Window

root = Path(os.environ.get("SCREENSHOT_OUT", "real_screenshots")).resolve()
root.mkdir(parents=True, exist_ok=True)
app = QApplication.instance() or QApplication([])
app.setQuitOnLastWindowClosed(False)
window = Window()
window.setWindowTitle("DS Compare")
window.resize(1440, 960)
window.show()
app.processEvents()

mapping = (
    ("compare", "Porownanie"),
    ("mass", "Masa_czesci"),
    ("settings", "Ustawienia"),
)
manifest = {
    "capture": "actual DS Compare R11.23 PySide6.QtWidgets screens",
    "method": "QWidget.grab on windows-2022 GitHub runner with QT_QPA_PLATFORM=offscreen",
    "source": "dsac29.gui46.Window",
    "images": [],
}
for theme, theme_label in (("Ciemny", "Ciemny"), ("Jasny", "Jasny")):
    window.apply_theme(theme)
    for tab, label in mapping:
        window.navigate(tab)
        window.resize(1440, 960)
        app.processEvents()
        assert window.nav[tab].isChecked(), f"Wrong tab selected: {tab}"
        # Screenshots are from live window. Nothing is drawn by image tooling.
        pixmap = window.grab()
        assert pixmap.width() >= 1400 and pixmap.height() >= 900, (
            label, pixmap.width(), pixmap.height()
        )
        output = root / f"DSCompare_R1123_{label}_{theme_label}.png"
        assert pixmap.save(str(output), "PNG"), output
        assert output.is_file() and output.stat().st_size >= 15000, output
        manifest["images"].append({
            "tab": tab,
            "theme": theme_label,
            "file": output.name,
            "width": pixmap.width(),
            "height": pixmap.height(),
            "bytes": output.stat().st_size,
        })
        print(f"REAL SCREENSHOT: {output} ({pixmap.width()}x{pixmap.height()})")
window.close()
(root / "SCREENSHOTS_INFO.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8"
)
assert len(manifest["images"]) == 6
print("PASS: six real screenshots captured from running DS Compare R11.23")
