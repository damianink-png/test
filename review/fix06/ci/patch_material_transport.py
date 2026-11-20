"""Use binary transport for material results in both worker and parent."""
from pathlib import Path
import sys

root = Path(sys.argv[1]) / 'dsac29'
for module, replacements in {
    'native_guard.py': [
        ("from .brep_transport import write_brep\n        write_brep(common,req['common_shape'])",
         "from .material_transport import write_result\n        write_result(common,req['common_shape'])"),
        ('result=_load_brep(common)', 'from .material_transport import read_result\n            result=read_result(common)')],
    'material_guard.py': [
        ("from .brep_transport import write_brep\n        write_brep(shape,root/(name+'.brep'))",
         "from .material_transport import write_result\n        write_result(shape,root/(name+'.brep'))"),
        ('shapes=[_load_brep(root/', 'from .material_transport import read_result\n            shapes=[read_result(root/')]
}.items():
    path = root / module
    source = path.read_text()
    for old, new in replacements:
        assert source.count(old) == 1, (module, old)
        source = source.replace(old, new)
    path.write_text(source)
