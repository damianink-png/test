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
            checked=subprocess.run(["node","--check"],input=js,text=True,encoding="utf-8",capture_output=True)
            assert checked.returncode==0,checked.stderr


def test_missing_report_is_not_falsely_claimed_as_enhanced(tmp_path):
    assert enhance_mass_html(tmp_path,7850) is False


def test_missing_bom_table_raises_an_explicit_error(tmp_path):
    import pytest
    (tmp_path/"RAPORT_MASY.html").write_text("<html><body><h1>Masa</h1></body></html>",encoding="utf-8")
    with pytest.raises(ValueError,match="tabeli BOM"):
        enhance_mass_html(tmp_path,7850)


def test_legacy_mass_html_without_tbody_and_declared_windows_charset(tmp_path):
    # Some previous reports omitted TBODY and declared a legacy charset.
    # The generated file is always UTF-8 with no stale Windows meta tag.
    sample=HTML.replace("<head>","<head><meta charset='windows-1250'>")
    sample=sample.replace("<tbody>","").replace("</tbody>","")
    p=tmp_path/"RAPORT_MASY.html"
    p.write_text(sample,encoding="utf-8")
    assert enhance_mass_html(tmp_path,8000)
    fixed=p.read_text(encoding="utf-8")
    assert "Płyta dolna wspornika" in fixed
    assert "koła linowego" in fixed
    assert "<meta charset=\"utf-8\">" in fixed
    assert "windows-1250" not in fixed


CSV_SAMPLE = """Nazwa części;Ilość;Objętość jednej sztuki [mm³];Masa jednej sztuki [kg];Masa łączna [kg];Ścieżka w złożeniu
04244050_G_RELEASED;2;125000,5;0,981254;1,962508;Złożenie/Element
Płyta wspornika;1;100000;0,785;0,785;Złożenie/Podzespół
"""


def test_report_with_legacy_headers_restored_from_computed_csv(tmp_path):
    report = tmp_path / "RAPORT_MASY.html"
    original = ('<!doctype html><html lang="pl"><head><meta charset="utf-8"></head><body>'
                '<h1>Masa części i złożeń</h1><table><thead><tr><th>Element</th><th>Waga</th></tr></thead>'
                '<tbody><tr><td>04244050_G_RELEASED</td><td>2,7475</td></tr></tbody></table></body></html>')
    report.write_text(original, encoding='utf8')
    (tmp_path / 'MASY_CZESCI.csv').write_text(CSV_SAMPLE, encoding='utf-8-sig')
    assert enhance_mass_html(tmp_path, 7850)
    result = report.read_text(encoding='utf8')
    assert 'id="ds-restored-bom"' in result
    assert '04244050_G_RELEASED' in result
    assert 'Płyta wspornika' in result
    assert '125000,5' in result
    assert 'Materiał dla wszystkich' in result
    assert result.count('id="ds-restored-bom"') == 1
    assert enhance_mass_html(tmp_path, 7850)
    assert report.read_text(encoding='utf8') == result


def test_multi_model_summary_restores_all_bom_rows(tmp_path):
    report = tmp_path / 'RAPORT_MASY.html'
    report.write_text('<html><body><table><thead><tr><th>Plik</th><th>Masa [kg]</th></tr></thead>'
                      '<tbody><tr><td>A</td><td>2</td></tr></tbody></table></body></html>', encoding='utf8')
    (tmp_path / 'MASY_CZESCI.csv').write_text(CSV_SAMPLE, encoding='utf8')
    assert enhance_mass_html(tmp_path, 7850)
    html=report.read_text(encoding='utf8')
    assert '<th>Ilość</th>' in html
    assert '<th>Objętość jednej sztuki [mm³]</th>' in html
    assert 'id="ds-materials-script"' in html


def test_missing_csv_does_not_destroy_original_report(tmp_path):
    import pytest
    from dsac29.standalone_mass_materials import MassReportFormatError
    report=tmp_path/'RAPORT_MASY.html'
    original='<html><body><table><tr><td>Waga</td></tr></table></body></html>'
    report.write_text(original,encoding='utf8')
    with pytest.raises(MassReportFormatError,match='brak MASY_CZESCI.csv'):
        enhance_mass_html(tmp_path,7850)
    assert report.read_text(encoding='utf8')==original


def test_malformed_csv_does_not_fabricate_mass_or_modify_html(tmp_path):
    import pytest
    from dsac29.standalone_mass_materials import MassReportFormatError
    original='<html><body><h1>Raport</h1></body></html>'
    report=tmp_path/'RAPORT_MASY.html'
    report.write_text(original,encoding='utf8')
    (tmp_path/'MASY_CZESCI.csv').write_text(CSV_SAMPLE.replace('125000,5','NaN'),encoding='utf8')
    with pytest.raises(MassReportFormatError):
        enhance_mass_html(tmp_path,7850)
    assert report.read_text(encoding='utf8')==original


def test_mass_worker_preserves_calculated_summary_when_optional_html_fails(tmp_path,monkeypatch):
    import json
    import pytest
    # The standalone HTML workflow intentionally ships no OCCT/worker engine.
    # Run this integration test in the full portable/Windows CAD suite only.
    pytest.importorskip('dsac29.process_lifetime')
    pytest.importorskip('OCP')
    from dsac29 import worker_v37,process_lifetime,single_mass,standalone_mass_materials
    monkeypatch.setattr(process_lifetime,'contain_children',lambda:None)
    folder=tmp_path/'out';folder.mkdir()
    def analyze(*args,**kwargs):
        (folder/'MASY_CZESCI.csv').write_text('valid mass data',encoding='utf8')
        (folder/'PODSUMOWANIE_MASY.json').write_text('{"masa_calosci_kg":12.3}',encoding='utf8')
        (folder/'RAPORT_MASY.html').write_text('<html>incompatible</html>',encoding='utf8')
        return folder,{'masa_calosci_kg':12.3}
    monkeypatch.setattr(single_mass,'analyze_single',analyze)
    def fail(*args,**kwargs):
        raise standalone_mass_materials.MassReportFormatError('Legacy columns')
    monkeypatch.setattr(standalone_mass_materials,'enhance_mass_html',fail)
    code=worker_v37.main(['--worker','mass','--input',str(tmp_path/'dummy.stp'),'--output',str(folder)])
    assert code==0
    result=json.loads((folder/'_WYNIK_V37.json').read_text(encoding='utf8'))
    assert result['ok'] is True and result['podsumowanie']['masa_calosci_kg']==12.3
    assert result['materials_editable'] is False
    assert (folder/'MASY_CZESCI.csv').exists()
    assert (folder/'UWAGI_RAPORT_MASY.txt').exists()
