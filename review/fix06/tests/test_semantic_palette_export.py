"""Check semantic color consistency in real STEP, HTML 3D and report output.

Only the presentation layer changes: classification and Boolean proof are not mocked.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt

from dsac29.compare import Record
from dsac29.geometry import describe
from dsac29.palette import HEX, COLORS, MATERIAL_COLORS, REVISION_COLORS, EXPORT_COLOR_CHOICES, semantic_overrides
from dsac29.report import produce
from dsac29.step_io import inspect_step_colors


EXPECTED = {
    'SAME': '#249B60', 'RENAMED': '#249B60',
    'ADDED': '#168BFF', 'REMOVED': '#F28C28',
    'MOVED': '#A855F7', 'CHANGED_COMMON': '#7D899A',
    'CHANGED_ADDED': '#168BFF', 'CHANGED_REMOVED': '#FF4050',
}


def test_palette_semantics_and_custom_overrides():
    for key, color in EXPECTED.items():
        assert HEX[key] == color
        assert REVISION_COLORS[key] == tuple(int(color[n:n+2], 16)/255 for n in (1, 3, 5))
    assert COLORS['SAME'] == COLORS['RENAMED']
    assert MATERIAL_COLORS['CHANGED_ADDED'] == COLORS['ADDED']
    assert MATERIAL_COLORS['CHANGED_REMOVED'] != COLORS['REMOVED']
    assert MATERIAL_COLORS['CHANGED_COMMON'] != MATERIAL_COLORS['CHANGED_ADDED']
    assert MATERIAL_COLORS['CHANGED_COMMON'] != MATERIAL_COLORS['CHANGED_REMOVED']
    custom = semantic_overrides({'ADDED': (.1, .2, .3), 'REMOVED': (.4, .5, .6)})
    assert custom['CHANGED_ADDED'] == (.1, .2, .3)
    assert custom['CHANGED_REMOVED'] == (.4, .5, .6)
    assert semantic_overrides({'CHANGED_REMOVED': (.9, .8, .7), 'REMOVED': (.4, .5, .6)})['CHANGED_REMOVED'] == (.9, .8, .7)


def test_ten_visual_categories_are_five_related_pairs():
    expected = ('SAME', 'CHANGED_COMMON', 'CHANGED_ADDED', 'CHANGED_REMOVED',
                'ADDED', 'REMOVED', 'MOVED_OLD', 'MOVED',
                'UNCERTAIN_OLD', 'UNCERTAIN_NEW')
    assert tuple(key for key, _, _ in EXPORT_COLOR_CHOICES) == expected
    assert len({key for key, _, _ in EXPORT_COLOR_CHOICES}) == 10
    overrides = semantic_overrides({'SAME': (.1, .2, .3),
                                    'CHANGED_COMMON': (.4, .5, .6),
                                    'CHANGED_ADDED': (.2, .3, .4),
                                    'CHANGED_REMOVED': (.6, .5, .4)})
    assert overrides['CHANGED_COMMON'] == (.4, .5, .6)
    assert overrides['CHANGED_ADDED'] == (.2, .3, .4)
    assert overrides['CHANGED_REMOVED'] == (.6, .5, .4)


def _box(name, x, length):
    shape = BRepPrimAPI_MakeBox(gp_Pnt(x, 0, 0), length, 10, 10).Shape()
    return describe(shape, name, 'ASSEMBLY/' + name)


def _scene(path):
    html = path.read_text(encoding='utf-8')
    return json.loads(re.search(r'const scene=(\[.*?\]);\s*const stats=', html, re.S).group(1))


def test_verified_changed_regions_match_step_html_table_and_transparency(tmp_path):
    # Common = [2,30], added = [30,34], removed = [0,2].
    a = [_box('FRAME', 0, 30), _box('SAME', 100, 20), _box('REMOVED', 200, 10)]
    b = [_box('FRAME', 2, 32), _box('SAME', 100, 20), _box('ADDED', 300, 10)]
    records = [Record(0, 0, 'CHANGED', 'verified'), Record(1, 1, 'SAME', 'verified'),
               Record(2, None, 'REMOVED', 'verified'), Record(None, 2, 'ADDED', 'verified')]
    produce(tmp_path, a, b, records, generate_step=True, revision_style=True,
            preview3d=True, diff_step=False, full_bom=False, bom_csv=False, old_alpha=0.4)
    summary = json.loads((tmp_path/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
    assert summary['main_step_ready'], summary.get('step_export_error')
    assert summary['material_errors'] == {}, summary['material_errors']
    assert len(summary['material_regions']) == 1
    for key, value in EXPECTED.items():
        assert summary['colors_hex'][key].upper() == value
    scene = _scene(tmp_path/'PODGLAD_KOLOROW_3D.html')
    observed = {(item['status'], item['role']): item for item in scene}
    for key, role in [('CHANGED_COMMON', 'B'), ('CHANGED_ADDED', 'B'),
                      ('CHANGED_REMOVED', 'A'), ('REMOVED', 'A'), ('ADDED', 'B'), ('SAME', 'B')]:
        item = observed[key, role]
        assert item['rgb'] == list(REVISION_COLORS[key])
        assert item['alpha'] == (0.4 if role == 'A' else 1.0)
    report = (tmp_path/'RAPORT.html').read_text(encoding='utf-8')
    assert 'Materiał dodany' in report and 'Materiał usunięty' in report
    assert 'background:#168bff' in report and 'background:#ff4050' in report
    step = inspect_step_colors(str(tmp_path/'POROWNANIE_KOLORY.step'))
    step_products=(tmp_path/'POROWNANIE_KOLORY.step').read_text(encoding='latin-1')
    for polish_name in ('WSPOLNA_GEOMETRIA','MATERIAL_DODANY','MATERIAL_USUNIETY'):
        assert polish_name in step_products, polish_name
    assert 0.4 in step['alfy_powierzchni']
    for key in ('CHANGED_COMMON', 'CHANGED_ADDED', 'CHANGED_REMOVED', 'REMOVED', 'ADDED', 'SAME'):
        rgb = tuple(round(x, 4) for x in REVISION_COLORS[key])
        assert rgb in step['kolory_wczytane_rgb'], (key, rgb, step['kolory_wczytane_rgb'])


def test_verified_material_only_preview_is_available_and_focuses_small_deltas(tmp_path):
    # UI mode may show only proven material regions; uncertain geometry must
    # never be presented as a certified Common/Cut difference.
    a = [_box('FRAME', 0, 30)]
    b = [_box('FRAME', 2, 32)]
    produce(tmp_path, a, b, [Record(0, 0, 'CHANGED', 'verified')],
            generate_step=False, revision_style=True, preview3d=True,
            diff_step=False, full_bom=False, bom_csv=False)
    page = (tmp_path/'PODGLAD_KOLOROW_3D.html').read_text(encoding='utf-8')
    assert 'id="material"' in page
    assert "mode==='material'&&['CHANGED_ADDED','CHANGED_REMOVED'].includes(status)" in page
    assert "function focusVisible()" in page
    assert "disabled=!chunks.some(c=>['CHANGED_ADDED','CHANGED_REMOVED'].includes(c.status))" in page
    assert "['all','changes','removed','material']" in page
    assert 'id="fitVisible"' in page
    assert "if(mode!=='all')focusVisible()" in page
    assert "checks.some(c=>!c.checked)" in page
    assert "document.getElementById('fitVisible').onclick=focusVisible" in page


def test_old_revision_transparency_in_split_and_overlay():
    """Split A/B must not turn verified removed material into opaque red."""
    template = (Path(__file__).parents[1] / 'dsac29' / 'preview_template.html').read_text(encoding='utf-8')
    assert "if(c.role!=='A'||oldAlpha>=1){draw(c,1,color(i),picking);}" in template
    assert "seen.filter(([i,c])=>c.role==='A'&&oldAlpha<1)" in template
    assert "if(layoutMode==='split'||c.role!=='A'||oldAlpha>=1)" not in template
    assert "layoutMode!=='split'&&c.role==='A'" not in template


def test_pair_view_isolation_and_focus():
    """The A/B pair action must zoom to the pair, never all unpaired items."""
    template = (Path(__file__).parents[1] / 'dsac29' / 'preview_template.html').read_text(encoding='utf-8')
    match = re.search(r'function showRevisionPair\(\)\{.*?^\}', template, re.S | re.M)
    assert match, 'Missing A/B pair-view handler'
    if not shutil.which('node'):
        pytest.skip('Node.js not installed for JavaScript behavior test')
    script = '''
const assert=require('node:assert/strict');
let selectedId=0,chunks=[],itemVisible=[],focusCalls=0;
function selectPreviewMode(mode){assert.equal(mode,'all');itemVisible=chunks.map(()=>true);}
function focusVisible(){focusCalls++;}
function syncTree(){} function schedule(){}
''' + match.group(0) + '''
function check(pairs,selected,expected){
 chunks=pairs.map(pair_id=>({pair_id}));selectedId=selected;
 const before=focusCalls;showRevisionPair();
 assert.deepEqual(itemVisible,expected);assert.equal(focusCalls,before+1);
}
check(['A','A','B'],0,[true,true,false]);
check([null,null,'A'],0,[true,false,false]);
check([0,0,1],1,[true,true,false]);
check(['','',null],0,[true,false,false]);
selectedId=-1;const before=focusCalls;showRevisionPair();assert.equal(focusCalls,before);
console.log('PAIR_VIEW_TEST_PASS');
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + '\n' + result.stderr
    assert 'PAIR_VIEW_TEST_PASS' in result.stdout


def test_xray_picking_keeps_depth_for_new_revision():
    """X-ray A must not steal every click from visible B in the A/B overlay."""
    template = (Path(__file__).parents[1] / 'dsac29' / 'preview_template.html').read_text(encoding='utf-8')
    assert "if(xray.checked&&!picking)gl.disable(gl.DEPTH_TEST);" in template
    assert "if(xray.checked)gl.disable(gl.DEPTH_TEST);" not in template
    if not shutil.which('node'):
        pytest.skip('Node.js not installed')
    script = """
const assert=require('node:assert/strict');
let picking=false, xray={checked:true}, calls=[];
const gl={DEPTH_TEST:1,disable:(x)=>calls.push(x)};
function test(){if(xray.checked&&!picking)gl.disable(gl.DEPTH_TEST);}
test();assert.deepEqual(calls,[gl.DEPTH_TEST]);
calls=[];picking=true;test();assert.deepEqual(calls,[]);
console.log('XRAY_PICK_DEPTH_PASS');
"""
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + '\\n' + result.stderr
    assert 'XRAY_PICK_DEPTH_PASS' in result.stdout

def test_exact_brep_definition_reuse_for_independent_instances(tmp_path):
    """Exact geometry only: preserve location, color and dissimilar namesakes."""
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.TopLoc import TopLoc_Location
    from dsac29.step_io import ColoredDocument
    first=BRepPrimAPI_MakeBox(10,10,10).Shape()
    independent=BRepPrimAPI_MakeBox(10,10,10).Shape()
    translation=gp_Trsf()
    translation.SetTranslation(gp_Vec(100,0,0))
    moved=independent.Moved(TopLoc_Location(translation))
    doc=ColoredDocument(group_by_status=True)
    doc.add(first,'bolt-1',(0.2,0.7,0.3),group='SAME',source_name='bolt')
    doc.add(moved,'bolt-2',(0.2,0.7,0.3),group='SAME',source_name='bolt')
    doc.add(BRepPrimAPI_MakeBox(11,10,10).Shape(),'bolt-3',
            (0.2,0.7,0.3),group='SAME',source_name='bolt')
    doc.add(BRepPrimAPI_MakeBox(10,10,10).Shape(),'bolt-4',
            (0.2,0.3,0.9),group='ADDED',source_name='bolt')
    assert doc.count==4
    assert doc.definitions_created==3
    assert doc.definitions_reused==1
    diagnostics=doc.write(tmp_path/'repeated.step')
    assert diagnostics['definicje_unikalne']==3
    assert diagnostics['ponownie_uzyte_definicje']==1
    assert diagnostics['rzeczywiste_bryly_step']==4
    assert diagnostics['dokladne_porownania_brep']>=2


def test_exact_brep_fingerprint_index_only_matches_exact_styles(tmp_path):
    """Independently constructed solids use the exact serialized fingerprint index."""
    from dsac29.step_io import ColoredDocument
    doc=ColoredDocument(group_by_status=True)
    for i in range(8):
        doc.add(BRepPrimAPI_MakeBox(10,10,10).Shape(),f'part-{i}',
                (0.2,0.7,0.3),group='SAME',source_name='same-definition')
    doc.add(BRepPrimAPI_MakeBox(11,10,10).Shape(),'different-shape',
            (0.2,0.7,0.3),group='SAME',source_name='same-definition')
    doc.add(BRepPrimAPI_MakeBox(10,10,10).Shape(),'different-color',
            (0.3,0.7,0.3),group='SAME',source_name='same-definition')
    assert doc.count==10 and doc.definitions_created==3
    assert doc.definitions_reused==7
    assert doc._exact_index_hits>=6
    audit=doc.write(tmp_path/'indexed.step')
    assert audit['rzeczywiste_bryly_step']==10
    assert audit['definicje_unikalne']==3
