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


def test_viewer_shares_webgl_buffers_between_mesh_occurrences():
    """Do not allocate vertex/normal GPU buffers for every repeated part."""
    from pathlib import Path
    from dsac29 import preview3d
    script=Path(preview3d.__file__).with_name('preview_template.html').read_text(encoding='utf8')
    assert 'uniform mat4 instance;' in script
    assert 'gl.uniformMatrix4fv(instanceLoc,false,c.instance)' in script
    assert 'for(const mesh of meshDefinitions.values())' in script
    assert 'mesh.buf=buffer(local);mesh.nbuf=buffer(normals)' in script
    # Retain individual transform and independent selection for each occurrence.
    assert 'c.instance=new Float32Array' in script
    assert 'c.buf=c.mesh.buf;c.nbuf=c.mesh.nbuf' in script
    assert 'const pts=new Float32Array(local.length)' not in script


def test_viewer_instance_matrix_preserves_old_cpu_coordinates():
    """A single shared local mesh plus instance matrix must preserve world pose."""
    import numpy as np
    rng=np.random.default_rng(20261104)
    for _ in range(30):
        angle=rng.uniform(-3.,3.)
        c,s=np.cos(angle),np.sin(angle)
        rotation=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
        translation=rng.uniform(-400.,400.,size=3)
        origin=rng.uniform(-200.,200.,size=3)
        span=rng.uniform(1.,1000.)
        local=rng.uniform(-20.,20.,size=(60,3))
        # shared_mesh exports a 12-number row-major transform.
        matrix=np.concatenate((rotation,translation[:,None]),axis=1).ravel()
        old=(local @ rotation.T+translation-origin)*2/span
        # WebGL uses column-major 4x4 and performs normalization in the shader.
        instance=np.eye(4)
        instance[:3,:3]=rotation*2/span
        instance[:3,3]=(translation-origin)*2/span
        transformed=(np.c_[local,np.ones(len(local))]@instance.T)[:,:3]
        assert np.allclose(transformed,old,rtol=0,atol=1e-11)
        # The expected JavaScript matrix has the same column-major encoding.
        as_float32=np.array([matrix[0],matrix[4],matrix[8],0.,
                            matrix[1],matrix[5],matrix[9],0.,
                            matrix[2],matrix[6],matrix[10],0.,
                            matrix[3]-origin[0],matrix[7]-origin[1],
                            matrix[11]-origin[2],span/2],dtype=float)*2/span
        assert np.allclose(as_float32.reshape(4,4).T,instance,rtol=0,atol=1e-11)
