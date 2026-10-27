from pathlib import Path
import sys
p=Path(sys.argv[1])/'preview_template.html';s=p.read_text(encoding='utf-8')
def replace(old,new):
 global s
 if s.count(old)!=1:raise RuntimeError('Unexpected viewer: '+old[:80])
 s=s.replace(old,new)
replace('<button id="isolate">Izoluj</button>', '<button id="isolate">Izoluj</button><button id="pair">Pokaż parę A/B</button>')
a=s.index("for(const [id,changes] of [['all',false],['changes',true]])")
b=s.index("document.getElementById('focus').onclick",a)
s=s[:a]+"for(const mode of ['all','changes','removed'])document.getElementById(mode).onclick=()=>selectPreviewMode(mode);\n"+s[b:]
replace('makeTree();',Path(__file__).with_name('preview_controls.js').read_text()+'\nmakeTree();')
p.write_text(s,encoding='utf-8')
