"""Custom status colors must affect both generated STEP variants and HTML report."""
from pathlib import Path
from dsac29.gui import _valid_hex, _to_triplet
from dsac29.step_io import COLORS
from dsac29.cli import process


def test_hex_colors():
    assert _valid_hex('#00BBFF')
    assert not _valid_hex('blue')
    assert not _valid_hex('#ABC')
    assert _to_triplet('#0000FF') == (0., 0., 1.)


def test_custom_colors_report_and_diff(tmp_path):
    base = Path(__file__).resolve().parents[1]
    desired = dict(COLORS)
    desired['CHANGED'] = (0., 0.25, 1.)
    desired['REMOVED'] = (1., 0., 0.)
    folder, records, err = process(
        str(base/'samples'/'MODEL_A.step'),
        str(base/'samples'/'MODEL_B.step'),
        str(tmp_path),
        colors=desired, step=True, diff_step=True,
    )
    assert err is None
    html = (folder/'RAPORT.html').read_text(encoding='utf-8')
    assert 'background:#0040ff' in html
    assert 'background:#ff0000' in html
    import json
    data = json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
    assert data['colors_hex']['CHANGED'] == '#0040ff'
    assert data['colors_hex']['REMOVED'] == '#ff0000'
    assert (folder/'ROZNICE_BREP.step').exists()
