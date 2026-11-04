"""Chromium smoke: real offline report, UTF-8 names and per-part densities."""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"portable-src"))
from dsac29.standalone_mass_materials import enhance_mass_html

MARKUP="""<!doctype html><html lang="pl"><head><title>Masa</title></head><body>
<h1>Model: B134201032_Złożeni.STEP</h1><p>Masa całkowita: 24 kg</p>
<table><thead><tr><th>Nazwa części</th><th>Ilość</th>
<th>Objętość jednej sztuki [mm³]</th><th>Masa jednej sztuki [kg]</th>
<th>Masa łączna [kg]</th></tr></thead><tbody>
<tr><td>P³yta dolna</td><td>2</td><td>1000000</td><td>8</td><td>16</td></tr>
<tr><td>Uchwyt ko³a</td><td>1</td><td>1000000</td><td>8</td><td>8</td></tr>
</tbody></table></body></html>"""

def run():
    with tempfile.TemporaryDirectory(prefix="dscompare_mass_browser_") as td:
        path=Path(td)/"RAPORT_MASY.html"
        path.write_text(MARKUP,encoding="utf-8")
        assert enhance_mass_html(td,8000)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(accept_downloads=True,locale="pl-PL")
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(path.as_uri())
            page.locator(".ds-material-select").first.wait_for()
            assert page.locator(".ds-material-select").count()==2
            assert "Płyta dolna" in page.locator("tbody").inner_text()
            assert "Uchwyt koła" in page.locator("tbody").inner_text()
            assert page.locator(".ds-material-select").first.input_value()=="Stal nierdzewna 316"
            assert "24,0000 kg" in page.locator(".ds-material-totals").inner_text()
            page.locator(".ds-material-select").first.select_option("Aluminium 6061")
            assert "13,4000 kg" in page.locator(".ds-material-totals").inner_text()
            page.locator(".ds-density-input").last.fill("5000")
            page.locator(".ds-density-input").last.press("Tab")
            assert "10,4000 kg" in page.locator(".ds-material-totals").inner_text()
            with page.expect_download() as download_info:
                page.get_by_role("button",name="Zapisz przypisania JSON").click()
            data=json.loads(Path(download_info.value.path()).read_text(encoding="utf-8"))
            assert data["version"]==2 and len(data["rows"])==2
            assert data["rows"][0]["material"]=="Aluminium 6061"
            with page.expect_download() as download_info:
                page.get_by_role("button",name="Eksportuj CSV").click()
            csv=Path(download_info.value.path()).read_bytes().decode("utf-8-sig")
            assert "Płyta dolna" in csv and "Aluminium 6061" in csv
            assert "\r\n" in csv and ";" in csv
            assert not errors,errors
            browser.close()
    print("OFFLINE_MASS_HTML_POLISH_AND_PER_PART_MATERIALS_PASS")


if __name__=="__main__":
    run()
