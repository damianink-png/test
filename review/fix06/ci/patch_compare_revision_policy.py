"""Keep native failures distinguishable from inconclusive heuristic pairs."""
from pathlib import Path
import sys

path=Path(sys.argv[1])
source=path.read_text(encoding='utf-8')
old='*map(float,d),float(b[j].volume-a[i].volume),None,"Heurystyka — sprawdź parę"))'
new='''*map(float,d),float(b[j].volume-a[i].volume),None,
                          "Błąd testu B-Rep — sprawdź parę" if i in failed_a or j in failed_b else "Heurystyka — sprawdź parę"))'''
if source.count(old)==1:
    source=source.replace(old,new)
elif source.count(new)!=1:
    raise SystemExit('Unexpected comparator revision confidence; refusing patch')
compile(source,str(path),'exec')
path.write_text(source,encoding='utf-8')
print('COMPARATOR_NATIVE_FAILURE_CONFIDENCE_PASS')
