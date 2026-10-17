import csv, json
from pathlib import Path
from dsac29.single_mass import analyze_single
from dsac29.step_io import load_step, export_colored_step, inspect_step_colors
from dsac29.compare import compare
from dsac29.gui import GUI

SAMPLES=Path(__file__).resolve().parents[1]/'samples'

def test_single_mass(tmp_path):
    dst, summary=analyze_single(SAMPLES/'MODEL_A.step',tmp_path,7850.)
    with (dst/'MASY_CZESCI.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f,delimiter=';'))
    assert summary['liczba_bryl']==4
    assert sum(int(r['Ilość']) for r in rows)==4
    assert sum(float(r['Masa łączna [kg]'].replace(',','.')) for r in rows)>0
    assert (dst/'RAPORT_MASY.html').exists()
    assert 'kg/m³' in (dst/'RAPORT_MASY.html').read_text(encoding='utf-8')

def test_step_roundtrip_colors_v35(tmp_path):
    a=load_step(str(SAMPLES/'MODEL_A.step'))
    b=load_step(str(SAMPLES/'MODEL_B.step'))
    result=compare(a,b)
    path=tmp_path/'result.step'
    export_colored_step(str(path),result,a,b)
    audit=inspect_step_colors(str(path))
    assert audit['pokolorowane_etykiety']>=3
    assert audit['pokolorowane_powierzchnie']>=5
    assert audit['rekordy_stylow_step']>=10
    assert len(audit['kolory_wczytane_rgb'])>=2

def test_csv_display_name():
    assert GUI._display_csv_name('="04244005"')=='04244005'
    assert GUI._display_csv_name('Element')=='Element'
