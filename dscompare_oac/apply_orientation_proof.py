"""Reject false unchanged for 180-degree in-place rotations of asymmetric parts."""
from pathlib import Path
import ast
import sys

def apply(root):
    model=Path(root)/'openassembly'/'model.py'
    code=model.read_text(encoding='utf8')
    before='''    if (a.extents and b.extents and not (a.virtual_transform or b.virtual_transform)
            and any(abs(x-y)>tol for x,y in zip(a.extents,b.extents))):'''
    after='''    # Local mass, center, area and AABB cannot prove an asymmetric part
    # unchanged after a 180-degree rotation. Confirm real world-space faces.
    if (a.shape is not None and b.shape is not None
            and a.fingerprint == b.fingerprint
            and not a.shape.IsSame(b.shape)
            and not _same_world_faces(a,b)):
        return False
    if (a.extents and b.extents and not (a.virtual_transform or b.virtual_transform)
            and any(abs(x-y)>tol for x,y in zip(a.extents,b.extents))):'''
    assert code.count(before)==1,'Unexpected OpenAssembly placement logic'
    code=code.replace(before,after,1)
    ast.parse(code,filename=str(model))
    model.write_text(code,encoding='utf8')
    tests=Path(root)/'integration'/'test_bridge.py'
    code=tests.read_text(encoding='utf8')
    assert 'test_asymmetric_three_hole_plate_rotation_is_moved' not in code
    code+='''

def test_asymmetric_three_hole_plate_rotation_is_moved(tmp_path):
    """Equal volume, centroid, fingerprint, pose and AABB do NOT imply SAME."""
    from openassembly.model import compare
    from openassembly.solidio import load_step as load_solids
    a,b=tmp_path/'plate_a.step',tmp_path/'plate_b.step'
    shape=(cq.Workplane('XY').box(40,24,3).faces('>Z').workplane()
           .pushPoints([(-13,-5),(4,8),(12,-3)]).hole(3)).val()
    center=shape.Center()
    rotated=shape.rotate((center.x,center.y,center.z),
                        (center.x,center.y,center.z+1),180)
    for file,body in [(a,shape),(b,rotated)]:
        model=cq.Assembly(name='Fixture')
        model.add(body,name='asymmetric_three_holes')
        model.save(str(file))
    aa=load_solids(a,'A');bb=load_solids(b,'B')
    assert len(aa)==len(bb)==1
    assert aa[0].fingerprint==bb[0].fingerprint
    assert abs(aa[0].centroid[0]-bb[0].centroid[0])<.01
    assert all(abs(x-y)<.01 for x,y in zip(aa[0].extents,bb[0].extents))
    match=compare(aa,bb,auto_align=False)
    assert match.counts=={'moved':1},match.counts
'''
    ast.parse(code,filename=str(tests))
    tests.write_text(code,encoding='utf8')
    print('Applied asymmetric in-place rotation proof')

if __name__=='__main__':
    apply(sys.argv[1])
