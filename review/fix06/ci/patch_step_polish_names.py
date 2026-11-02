"""Give material regions Polish ASCII-safe PRODUCT and subassembly names in STEP.

The semantic keys CHANGED_COMMON/ADDED/REMOVED remain unchanged internally
for color, transparency and geometric proof. Only exported labels change.
"""
from pathlib import Path
import sys

p=Path(sys.argv[1])/"dsac29"/"step_io.py"
s=p.read_text(encoding="utf-8")
def change(old,new):
    global s
    if s.count(old)!=1:
        raise RuntimeError(f"Polish STEP name anchor mismatch: {old!r}, count={s.count(old)}")
    s=s.replace(old,new)

change(
    "                for component,piece in enumerate(delta_solids(shape),1):",
    """                kind_pl={'CHANGED_COMMON':'WSPOLNA_GEOMETRIA',
                         'CHANGED_ADDED':'MATERIAL_DODANY',
                         'CHANGED_REMOVED':'MATERIAL_USUNIETY'}[kind]
                for component,piece in enumerate(delta_solids(shape),1):"""
)
change("key_name=cad_product_name(name,number,kind,role)+f'__S{component:03d}'",
       "key_name=cad_product_name(name,number,kind_pl,role)+f'__S{component:03d}'")
change("'podzlozenie':['02_ZMIENIONE',f'PARA_{number:06d}',kind],",
       "'podzlozenie':['02_ZMIENIONE',f'PARA_{number:06d}',kind_pl],")
p.write_text(s,encoding="utf-8")
print("DSCOMPARE_STEP_POLISH_NAMES_PATCH_PASS",p,flush=True)
