"""Offline mass HTML and reversible Polish STEP naming regressions."""
import re
import shutil
import subprocess

from dsac29.name_encoding import repair_polish_name
from dsac29.standalone_mass_materials import enhance_mass_html


HTML = """<!doctype html><html lang="pl"><head><title>Raport masy</title></head><body>
<h1>Model: B134201032_Złożeni.STEP</h1>
<p>Liczba brył: 149, Pozycji BOM: 87</p>
<p>Masa całkowita: 2532,134 kg, Gęstość: 8000 kg/m³</p>
<table><thead><tr><th>Nazwa części</th><th>Ilość</th>
<th>Objętość jednej sztuki [mm³]</th><th>Masa jednej sztuki [kg]</th>
<th>Masa łączna [kg]</th></tr></thead>
<tbody><tr><td>B154001037_P³yta dolna wspornika</td><td>2</td>
<td>1017682,5000</td><td>8,1415</td><td>16,2829</td></tr>
<tr><td>B154001038_ko³a linowego</td><td>1</td>
<td>5816.1166</td><td>0,0465</td><td>0,0465</td></tr></tbody></table>
</body></html>"""


def test_step_name_mojibake_repair_is_conservative():
    assert repair_polish_name("B154001037_P³yta dolna") == "B154001037_Płyta dolna"
    assert repair_polish_name("Uchwyt ko³a") == "Uchwyt koła"
    assert repair_polish_name("PÅ‚yta") == "Płyta"
    assert repair_polish_name("Aluminium 300 mm³") == "Aluminium 300 mm³"
    assert repair_polish_name("Płyta nośna") == "Płyta nośna"
    assert repair_polish_name("P�yta") == "P�yta"  # irrecoverable data is not guessed


def test_enhanced_mass_report_is_utf8_interactive_and_idempotent(tmp_path):
    report=tmp_path/"RAPORT_MASY.html"
    report.write_text(HTML,encoding="utf-8")
    assert enhance_mass_html(tmp_path,8000)
    generated=report.read_text(encoding="utf-8")
    assert '<meta charset="utf-8">' in generated
    assert "B154001037_Płyta dolna wspornika" in generated
    assert "B154001038_koła linowego" in generated
    assert "mm³" in generated
    assert 'id="ds-material-enhancement"' in generated
    assert "Gęstość [kg/m³]" in generated
    assert "Materiał dla wszystkich" in generated
    assert "Zapisz przypisania JSON" in generated
    assert "Eksportuj CSV" in generated
    assert "Masa całkowita po wyborze materiałów" in generated
    assert "baseMaterial=Object.keys(library).find(k=>library[k]===baseDensity)" in generated
    assert "8000.0" in generated
    assert enhance_mass_html(tmp_path,8000)
    assert report.read_text(encoding="utf-8")==generated
    if shutil.which("node"):
        scripts=re.findall(r'<script[^>]*>(.*?)</script>',generated,flags=re.I|re.S)
        assert scripts
        for js in scripts:
            checked=subprocess.run(["node","--check"],input=js,text=True,capture_output=True)
            assert checked.returncode==0,checked.stderr


def test_missing_report_is_not_falsely_claimed_as_enhanced(tmp_path):
    assert enhance_mass_html(tmp_path,7850) is False


def test_missing_bom_table_raises_an_explicit_error(tmp_path):
    import pytest
    (tmp_path/"RAPORT_MASY.html").write_text("<html><body><h1>Masa</h1></body></html>",encoding="utf-8")
    with pytest.raises(ValueError,match="tabeli BOM"):
        enhance_mass_html(tmp_path,7850)
