"""Independent BOM browser enhancement, no geometry matcher modifications."""
from pathlib import Path
import sys

def apply(root):
    p=Path(root)/'src/openassembly/report.py'
    s=p.read_text(encoding='utf-8')
    anchor="    return {'mass_A_kg':round(mass(comp.a),6),'mass_B_kg':round(mass(comp.b),6),"
    assert s.count(anchor)==1, 'BOM return anchor missing'
    enhancement='''    # Read directly from the in-memory BOM, not from CSV. Collapsed sections
    # keep the changes visible even for assemblies with thousands of parts.
    from html import escape as esc
    def bom_section(label, table):
        rows=[]
        for _,group in sorted(table.items(),key=lambda e:(e[1][0].name,e[1][0].uid)):
            item=group[0]
            rows.append('<tr><td>'+esc(item.name)+'</td><td>'+str(len(group))+
                        '</td><td>'+f"{mass(group):.6f}"+'</td></tr>')
        return ('<details><summary>BOM '+label+' — '+str(len(rows))+
                ' pozycji</summary><div class="scroll"><table><thead><tr>'+
                '<th>Część</th><th>Ilość</th><th>Masa [kg]</th></tr></thead><tbody>'+
                ''.join(rows)+'</tbody></table></div></details>')
    changes=[]
    for key in sorted(tables[0].keys() | tables[1].keys(),key=lambda k:str(k[0])):
        old=tables[0].get(key,[]);new=tables[1].get(key,[])
        if len(old)==len(new) and abs(mass(old)-mass(new))<1e-8:
            continue
        changes.append('<tr><td>'+esc((old or new)[0].name)+'</td><td>'+
                       str(len(old))+'</td><td>'+str(len(new))+'</td><td>'+
                       str(len(new)-len(old))+'</td></tr>')
    css=('body{font:14px Segoe UI,Arial,sans-serif;background:#15171b;color:#e8ecf2;'
         'margin:30px;max-width:1200px}h1{font-size:24px}details{margin:12px 0;'
         'background:#222831;border:1px solid #394454;border-radius:9px;padding:14px}'
         'summary{cursor:pointer;font-weight:600}table{width:100%;border-collapse:collapse;'
         'margin-top:12px}td,th{padding:9px;text-align:left;border-bottom:1px solid #394454}'
         '.scroll{max-height:420px;overflow:auto}th{position:sticky;top:0;background:#293442}'
         'p{color:#b3bfcc}')
    html_page=('<!doctype html><html lang="pl"><meta charset="utf-8"><title>'+
               'OpenAssembly — BOM</title><style>'+css+'</style><h1>Zestawienie materiałowe</h1>'+
               '<p>Rewizja A: '+f"{mass(comp.a):.3f}"+' kg · Rewizja B: '+
               f"{mass(comp.b):.3f}"+' kg</p>'+
               '<details open><summary>Zmiany ilości i masy — '+str(len(changes))+
               ' pozycji</summary><div class="scroll"><table><thead><tr><th>Część</th>'+
               '<th>Ilość A</th><th>Ilość B</th><th>Różnica</th></tr></thead><tbody>'+
               ''.join(changes)+'</tbody></table></div></details>'+
               bom_section('A',tables[0])+bom_section('B',tables[1])+'</html>')
    (out/'BOM_PRZEGLAD.html').write_text(html_page,encoding='utf-8')
'''
    s=s.replace(anchor,enhancement+anchor,1)
    p.write_text(s,encoding='utf-8')
    print('OpenAssembly independent collapsible BOM HTML installed')

if __name__=='__main__':
    apply(sys.argv[1])
