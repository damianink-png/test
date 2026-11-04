"""HTML streaming must preserve occurrences, colors, JSON and clean up temp files."""
import json
import re
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.compare import Record
from dsac29.geometry import describe
from dsac29.preview3d import create_preview


def test_streamed_scene_preserves_all_occurrences(tmp_path):
    first=describe(BRepPrimAPI_MakeBox(10,12,14).Shape(),'<same>', 'A/<same>')
    second=describe(BRepPrimAPI_MakeBox(20,10,10).Shape(),'added', 'B/added')
    records=[Record(0,0,'SAME',''),Record(None,1,'ADDED','')]
    file=tmp_path/'PODGLAD_KOLOROW_3D.html'
    stats=create_preview(file,records,[first],[first,second],dual_revisions=True)
    html=file.read_text(encoding='utf-8')
    scene=json.loads(re.search(r'const scene=(\[.*?\]);\s*const stats=',html,re.S).group(1))
    assert stats['elementy']==3 and len(scene)==3
    assert [(x['status'],x['role']) for x in scene]==[('ADDED','B'),('SAME','A'),('SAME','B')]
    assert all(x['pair_id'].startswith('PAIR_') for x in scene)
    assert '<same>' not in html and r'\u003csame>' in html
    assert 'const stats=' in html
    assert not list(tmp_path.glob('*.tmp'))


def test_preview_failure_does_not_leave_unfinished_files(tmp_path,monkeypatch):
    from dsac29 import shared_mesh
    first=describe(BRepPrimAPI_MakeBox(10,10,10).Shape(),'one','one')
    def broken(*args,**kwargs):
        raise RuntimeError('forced mesh failure')
    monkeypatch.setattr(shared_mesh.SharedMesh,'pack',broken)
    file=tmp_path/'PODGLAD_KOLOROW_3D.html'
    import pytest
    with pytest.raises(RuntimeError,match='forced mesh failure'):
        create_preview(file,[Record(0,0,'SAME','')],[first],[first])
    assert not file.exists() and not list(tmp_path.glob('*.tmp'))
