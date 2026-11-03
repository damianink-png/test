"""Enhance the existing standalone RAPORT_MASY.html without replacing its layout."""
from pathlib import Path
import json

MATERIALS={"Stal S235 / S355 / S690":7850,"Stal nierdzewna 304":7930,"Stal nierdzewna 316":8000,"Aluminium 6061":2700,"Aluminium 7075":2810,"Miedź":8960,"Mosiądz":8500,"Żeliwo szare":7200,"Tytan Grade 5":4430,"POM":1410,"PA6":1140}

def enhance_mass_html(folder, density=7850):
    path=Path(folder)/"RAPORT_MASY.html"
    if not path.is_file(): return False
    html=path.read_text(encoding="utf-8")
    if 'id="ds-material-enhancement"' in html: return True
    script=r"""
<style id="ds-material-enhancement">
.ds-material-select,.ds-density-input{max-width:175px;width:100%;padding:5px;background:#1b2634;color:#edf2f8;border:1px solid #708198;border-radius:5px;color-scheme:dark}
.ds-density-input{max-width:105px}
.ds-material-actions{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
.ds-material-actions button{padding:8px 12px;cursor:pointer}
@media print{.ds-material-actions{display:none}}
</style>
<script>
(function(){
const library=__MATERIALS__;
const baseDensity=__DENSITY__;
const table=[...document.querySelectorAll('table')].find(t=>/objętość/i.test(t.querySelector('thead')?.textContent||''));
if(!table)return;
const headers=[...table.querySelectorAll('thead th')];
const find=(pattern)=>headers.findIndex(h=>pattern.test(h.textContent.trim()));
const volIndex=find(/objętość/i),qtyIndex=find(/ilość/i),unitIndex=find(/masa jednej|masa 1|masa jednostk/i),sumIndex=find(/masa łącz|masa całkow|masa razem/i);
if(volIndex<0||qtyIndex<0||unitIndex<0||sumIndex<0)return;
const rows=[];
const parse=s=>Number(String(s).replace(/\s/g,'').replace(',','.').replace(/[^\d.\-]/g,''));
const fmt=n=>n.toLocaleString('pl-PL',{minimumFractionDigits:4,maximumFractionDigits:4});
const opt=(name)=>Object.keys(library).map(k=>'<option value="'+k.replace(/&/g,'&amp;').replace(/"/g,'&quot;')+'"'+(k===name?' selected':'')+'>'+k.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</option>').join('');
const head=document.createElement('th');head.textContent='Materiał';headers[volIndex].after(head);
const densHead=document.createElement('th');densHead.textContent='Gęstość [kg/m³]';head.after(densHead);
for(const tr of table.querySelectorAll('tbody tr')){
 const cells=[...tr.cells];if(cells.length<=Math.max(volIndex,qtyIndex,unitIndex,sumIndex))continue;
 const qty=parse(cells[qtyIndex].textContent),vol=parse(cells[volIndex].textContent);
 if(!(qty>0&&vol>=0))continue;
 const material=document.createElement('td'),density=document.createElement('td');
 const select=document.createElement('select');select.className='ds-material-select';select.innerHTML=opt(Object.keys(library)[0]);
 const input=document.createElement('input');input.className='ds-density-input';input.type='number';input.min='0.001';input.step='any';input.value=baseDensity;
 material.append(select);density.append(input);cells[volIndex].after(material);material.after(density);
 const record={tr,qty,vol,select,input,unit:cells[unitIndex],sum:cells[sumIndex]};
 select.addEventListener('change',()=>{input.value=library[select.value];update()});
 input.addEventListener('change',update);rows.push(record);
}
if(!rows.length)return;
const bar=document.createElement('div');bar.className='ds-material-actions';
const total=document.createElement('strong');total.style.margin='10px 0';total.style.display='block';
const save=document.createElement('button');save.textContent='Zapisz materiały JSON';
const load=document.createElement('input');load.type='file';load.accept='.json';
const csv=document.createElement('button');csv.textContent='Eksport mas z materiałami CSV';
bar.append(save,load,csv);table.before(bar,total);
function update(){
 let sum=0;for(const r of rows){let d=Number(r.input.value);if(!(d>0&&Number.isFinite(d))){r.input.value=baseDensity;d=baseDensity}
 const unit=r.vol*1e-9*d,all=unit*r.qty;r.unit.textContent=fmt(unit);r.sum.textContent=fmt(all);sum+=all}
 total.textContent='Masa całkowita po zmianie materiałów: '+fmt(sum)+' kg';
}
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
save.onclick=()=>download('MATERIALY_MASY.json',JSON.stringify(rows.map(r=>({qty:r.qty,vol:r.vol,material:r.select.value,density:Number(r.input.value)})),null,2),'application/json');
load.onchange=async()=>{try{const data=JSON.parse(await load.files[0].text());if(!Array.isArray(data)||data.length!==rows.length||data.some((v,i)=>v.qty!==rows[i].qty||v.vol!==rows[i].vol||!(v.density>0)))throw Error('Niezgodny BOM');
 data.forEach((v,i)=>{if(library[v.material])rows[i].select.value=v.material;rows[i].input.value=v.density});update()}catch(e){alert('Nie udało się wczytać materiałów: '+e.message)}load.value=''};
csv.onclick=()=>{const data=[['Pozycja','Ilość','Objętość mm3','Materiał','Gęstość kg/m3','Masa 1 szt kg','Masa razem kg'],...rows.map((r,i)=>[i+1,r.qty,r.vol,r.select.value,r.input.value,r.vol*1e-9*Number(r.input.value),r.vol*1e-9*Number(r.input.value)*r.qty])];download('MASY_MATERIALY.csv','\ufeff'+data.map(a=>a.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(';')).join('\r\n'),'text/csv;charset=utf-8')};
update();
})();
</script>
"""
    script=script.replace("__MATERIALS__",json.dumps(MATERIALS,ensure_ascii=False)).replace("__DENSITY__",json.dumps(float(density)))
    if "</body>" in html: html=html.replace("</body>",script+"</body>",1)
    else: html+=script
    path.write_text(html,encoding="utf-8")
    return True
