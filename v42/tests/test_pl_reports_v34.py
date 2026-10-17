"""Regresje: polski Excel, nienazwane referencje STEP, raport i GUI."""
import csv
from pathlib import Path
from dsac29.report import _csv_value, visible_name, visible_path, produce
from dsac29.step_io import load_step
from dsac29.cli import process


def test_comma_decimal_and_no_excel_date(tmp_path):
    from dsac29.report import write_csv
    file=tmp_path/'BOM_A.csv'
    write_csv(file,['Nazwa','Masa jednej sztuki [kg]'],[
        ('04244036',0.79),('A-01',0.02626),('04244037',21.20315)])
    txt=file.read_text(encoding='utf-8-sig')
    assert '0,79' in txt and '0.79' not in txt
    assert '0,02626' in txt
    with file.open(encoding='utf-8-sig',newline='') as f:
        data=list(csv.DictReader(f,delimiter=';'))
    assert len(data)==3 and data[0]['Masa jednej sztuki [kg]']=='0,79'


def test_technical_step_references_are_hidden():
    assert visible_name('=>[0:1:1:102]', '04244050_ASM/0244557/=>[0:1:1:102]')=='0244557'
    assert visible_name('[0:1:1:71]', '04244050_ASM/0312345/[0:1:1:71]')=='0312345'
    assert '=>[' not in visible_path('04244050_ASM/03304457/=>[0:1:1:102]')
    assert visible_name('04244036', 'ROOT/04244036')=='04244036'


def test_polish_reports_no_version_or_author(tmp_path):
    base=Path(__file__).resolve().parents[1]
    folder, records, error=process(str(base/'samples'/'MODEL_A.step'),
                                  str(base/'samples'/'MODEL_B.step'),str(tmp_path),
                                  step=False,diff_step=False,progress=None)
    assert error is None
    html=(folder/'RAPORT.html').read_text('utf-8')
    assert 'raport porównania modeli' in html
    assert 'Designed &amp;' not in html and 'Szymczyk Damian' not in html
    assert 'V3.3' not in html
    with (folder/'ZMIANY.csv').open(encoding='utf-8-sig',newline='') as f:
        lines=list(csv.DictReader(f,delimiter=';'))
    assert lines and 'Rodzaj zmiany' in lines[0]
    assert 'Status PL' not in lines[0]
    assert any(l['Rodzaj zmiany']=='Zmieniona geometria' for l in lines)


def test_gui_about_and_no_page_scroll():
    from dsac29.gui import GUI
    import inspect
    code=inspect.getsource(GUI._build)
    assert '_scrolling_page(self.views' not in code
    assert hasattr(GUI,'show_about')
