"""Evidence-backed presentation: stable IDs, uncertainty and dual-revision scene."""
import json
import re
from types import SimpleNamespace
from dsac29.result_insights import enriched_records, overview_html
from dsac29.compare import Record
from dsac29.progress_events import ProgressEvents
from dsac29.palette import semantic_overrides


def test_uncertainty_is_not_a_topology_verdict_and_ids_survive_filtering():
    a=[SimpleNamespace(name='<cover>',path='root/cover'),SimpleNamespace(name='bolt',path='root/bolt')]
    rows=enriched_records([Record(0,None,'UNCERTAIN','unknown'),Record(1,None,'UNCERTAIN','unknown')],a,[],{'reason':'Common failed','failed_pair':{'a_index':0,'b_index':3}})
    assert [r['record_index'] for r in rows]==[0,1]
    assert rows[0]['blocked_operation_operand'] and not rows[1]['blocked_operation_operand']
    assert all(r['verification']=='unverified' and r['distance_mm'] is None for r in rows)
    page=overview_html(rows,{},.01,False)
    assert '&lt;cover&gt;' in page and '<cover>' not in page
    assert '#pair=PAIR_000001' in page and 'Analiza: Częściowa' in page


def test_semantic_custom_colors_propagate_without_overriding_explicit_old_colors():
    p=semantic_overrides({'CHANGED':(.1,.2,.3),'ADDED':(.2,.3,.4),'CHANGED_OLD':(.8,.7,.6)})
    assert p['CHANGED_NEW']==(.1,.2,.3) and p['CHANGED_ADDED']==(.2,.3,.4)
    assert p['CHANGED_OLD']==(.8,.7,.6)


def test_progress_emits_timestamp_and_only_explicit_stage_denominators(tmp_path):
    path=tmp_path/'events.jsonl';emit=ProgressEvents(path)
    emit('Etap zgodności: 5/20; B-Rep: 12; pamięć: 1')
    emit('Zmiany materiału: Common A[1] ↔ B[2], test 7; limit 90 s')
    a,b=[json.loads(line) for line in path.read_text().splitlines()]
    assert a['completed']==5 and a['total']==20 and a['checks']==12 and a['timestamp_ms']>0
    assert b['phase']=='Weryfikacja materiału' and b['checks']==7
    assert 'total' not in b and 'completed' not in b
    emit('Weryfikacja przesunięcia B-Rep: 25/1682; potwierdzono 25')
    frame=json.loads(path.read_text().splitlines()[-1])
    assert frame['completed']==25 and frame['total']==1682
    assert frame['phase']=='Weryfikacja wyrównania B-Rep' and 'checks' not in frame


def test_dual_preview_contains_actual_a_even_when_same_and_keeps_registration(tmp_path):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.geometry import describe
    from dsac29.preview3d import create_preview
    a=[describe(BRepPrimAPI_MakeBox(10,10,10).Shape(),'Original A','root/A')]
    b=[describe(BRepPrimAPI_MakeBox(10,10,10).Shape(),'Original B','root/B')]
    alignment={'applied':True,'translation_B_to_A_mm':[-507.4569,249.1752,-524.], 'rotation_B_to_A':[[1,0,0],[0,1,0],[0,0,1]]}
    path=tmp_path/'preview.html';info=create_preview(path,[Record(0,0,'SAME','verified')],a,b,dual_revisions=True,alignment=alignment)
    text=path.read_text();scene=json.loads(re.search(r'^const scene=(.*);$',text,re.M)[1])
    assert {(r['role'],r['name']) for r in scene}=={('A','Original A'),('B','Original B')}
    assert info['dual_revisions'] and info['alignment']==alignment and len(info['world_origin'])==3
    from sys import path as syspath
    from pathlib import Path
    syspath.insert(0,str(Path(__file__).resolve().parents[1]/'ci'))
    from audit_preview import audit_preview
    summary={'records':[vars(Record(0,0,'SAME','verified'))],'old_alpha':.4,'preview_3d':info}
    assert audit_preview(text,summary)==2
    broken=text.replace('"role":"A"','"role":"B"',1)
    import pytest
    with pytest.raises(AssertionError):audit_preview(broken,summary)


def test_split_changed_revision_a_keeps_common_and_removed_material(tmp_path):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.geometry import describe
    from dsac29.material_deltas import calculate
    from dsac29.preview3d import create_preview
    a=[describe(BRepPrimAPI_MakeBox(20,10,10).Shape(),'Old','A')]
    b=[describe(BRepPrimAPI_MakeBox(15,10,10).Shape(),'New','B')]
    regions=calculate(a[0],b[0]);path=tmp_path/'preview.html'
    info=create_preview(path,[Record(0,0,'CHANGED','verified')],a,b,material_regions={0:regions},dual_revisions=True)
    text=path.read_text();scene=json.loads(re.search(r'^const scene=(.*);$',text,re.M)[1])
    assert {(r['role'],r['status']) for r in scene}=={('A','CHANGED_COMMON'),('A','CHANGED_REMOVED'),('B','CHANGED_COMMON')}
    assert info['pominiete']==0


def test_streamed_scene_preserves_unicode_and_escapes_supplier_script_labels(tmp_path):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.geometry import describe
    from dsac29.preview3d import create_preview
    label='Osłona </script><script>window.injected=1</script>'
    part=describe(BRepPrimAPI_MakeBox(1,2,3).Shape(),label,'root/'+label)
    path=tmp_path/'scene.html';create_preview(path,[Record(None,0,'ADDED','')],[],[part])
    text=path.read_text();scene=json.loads(re.search(r'^const scene=(.*);$',text,re.M)[1])
    assert scene[0]['name']==label and '\\u003c/script>' in text
    assert '<script>window.injected=1</script>' not in text and not path.with_suffix('.html.tmp').exists()
