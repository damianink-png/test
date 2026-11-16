"""Opt-in physical UV orientation proof for the isolated NURBS path."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'dsac29/parametric_identity.py';s=p.read_text()
s=s.replace('allow_micro_cylinders=False):','allow_micro_cylinders=False,allow_parametric_orientation=False):',1)
s=s.replace('  if (strict_repair or not (allow_strip_orientation or allow_micro_cylinders)) and any(', '  if not allow_parametric_orientation and (strict_repair or not (allow_strip_orientation or allow_micro_cylinders)) and any(',1)
old='''   if int(fa[i].Orientation())!=int(fb[j].Orientation()):
    if (strict_repair or not allow_strip_orientation or
        not collapsed_strip_orientation(fa[i],fb[j],tolerance)):return False
   if not surface_equal(fa[i],fb[j],face_data[i][4],tol):return False'''
new='''   if allow_parametric_orientation:
    from .nurbs_orientation import oriented_surface_equal
    if not oriented_surface_equal(fa[i],fb[j],tol):return False
   else:
    if int(fa[i].Orientation())!=int(fb[j].Orientation()):
     if (strict_repair or not allow_strip_orientation or
         not collapsed_strip_orientation(fa[i],fb[j],tolerance)):return False
    if not surface_equal(fa[i],fb[j],face_data[i][4],tol):return False'''
assert s.count(old)==1;s=s.replace(old,new);compile(s,str(p),'exec');p.write_text(s)
p=root/'dsac29/step_reexport_tolerance.py';s=p.read_text()
s=s.replace('_original_boundary_only=False):','_original_boundary_only=False,_nurbs_orientation=False):',1)
old='            if ori!=other_ori and not (strip_candidate or micro_candidate):continue'
new='            if ori!=other_ori and not (strip_candidate or micro_candidate or (_nurbs_orientation and "BSpline" in typ)):continue'
assert s.count(old)==1;s=s.replace(old,new)
old='allow_original_micro_degenerate=True,allow_micro_cylinders=True))'
new='allow_original_micro_degenerate=True,allow_micro_cylinders=True,allow_parametric_orientation=_nurbs_orientation))'
assert s.count(old)>=1;s=s.replace(old,new,1);compile(s,str(p),'exec');p.write_text(s)
print('NURBS_PHYSICAL_ORIENTATION_PATCH_PASS')
