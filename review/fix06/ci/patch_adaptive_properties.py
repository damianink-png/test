"""Use the same adaptive integrator throughout the assembled CAD engine."""
import ast
import re
from pathlib import Path
import sys
root=Path(sys.argv[1])/'dsac29'
files=('geometry step_reexport_tolerance closed_shell_import step_io same_domain '
       'import_validation model_diagnostic surface_witness brep_safety '
       'boundary_descriptor common_exclusion material_deltas analytic_bore_delta '
       'cad_pose_search surface_registration').split()
for name in files:
    p=root/(name+'.py');s=p.read_text()
    names=[]
    for old,new in (('VolumeProperties_s','volume_properties'),('SurfaceProperties_s','surface_properties')):
        token='BRepGProp.'+old
        if token in s:
            s=s.replace(token,new);names.append(new)
    assert names, 'Missing integration calls: '+name
    s=re.sub(r'(?m)^[ \t]*from OCP.BRepGProp import BRepGProp\n','',s)
    tree=ast.parse(s);line=0
    for node in tree.body:
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):line=node.end_lineno
        elif isinstance(node,ast.ImportFrom) and node.module=='__future__':line=node.end_lineno
        else:break
    lines=s.splitlines(True)
    lines.insert(line,'from .cad_properties import '+', '.join(names)+'\n')
    s=''.join(lines);compile(s,str(p),'exec');p.write_text(s)
print('ADAPTIVE_CAD_PROPERTIES_PASS')
