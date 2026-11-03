"""Editable offline mass/material report for DS Compare."""
import html
import json

MATERIALS = {
    "Stal konstrukcyjna S235/S355/S690": 7850,
    "Stal nierdzewna 304": 7930,
    "Stal nierdzewna 316": 8000,
    "Aluminium 6061": 2700,
    "Aluminium 7075": 2810,
    "Miedź": 8960,
    "Mosiądz": 8500,
    "Żeliwo szare": 7200,
    "Tytan Grade 5": 4430,
    "POM": 1410,
    "PA6": 1140,
}

def render_mass_report(bom_a, bom_b, density=7850):
    rows = []
    for side, bom in (("A", bom_a), ("B", bom_b)):
        for name, count, volume, _unit, _total, path in bom:
            rows.append(dict(side=side, name=name, count=int(count),
                             volume=float(volume), path=path,
                             material="Stal konstrukcyjna S235/S355/S690",
                             density=float(density)))
    payload=json.dumps(rows,ensure_ascii=False).replace("<","\\u003c")
    library=json.dumps(MATERIALS,ensure_ascii=False).replace("<","\\u003c")
    return """<!doctype html><html lang="pl"><meta charset="utf-8"><title>DS Compare — Masa części</title>
<style>body{font:14px system-ui;background:#141a22;color:#e9edf4;margin:30px}h1{font-size:23px}
button,input,select{background:#242e3c;color:#fff;border:1px solid #536070;border-radius:6px;padding:7px}
button{cursor:pointer}table{border-collapse:collapse;width:100%;margin-top:20px}
td,th{border-bottom:1px solid #394454;padding:9px;text-align:left}td input{width:95px}
aside{display:flex;gap:12px;align-items:center;flex-wrap:wrap}small{color:#b7c2d0}</style>
<h1>Masa części — biblioteka materiałów</h1>
<small>Zmiany przeliczają masę w tym raporcie; nie zmieniają geometrii STEP ani pierwotnego BOM.</small>
<aside><label>Materiał domyślny <select id="defaultMaterial"></select></label>
<label>Gęstość [kg/m³] <input id="defaultDensity" type="number" min="0.001" step="any"></label>
<button onclick="applyDefault()">Zastosuj do wszystkich</button>
<button onclick="addMaterial()">Dodaj materiał</button>
<button onclick="exportCsv()">Eksportuj CSV</button></aside>
<table><thead><tr><th>Model</th><th>Część</th><th>Ilość</th><th>Objętość [mm³]</th>
<th>Materiał</th><th>Gęstość [kg/m³]</th><th>Masa 1 szt. [kg]</th><th>Masa łączna [kg]</th></tr></thead>
<tbody id="parts"></tbody></table><h2 id="total"></h2>
<script>
const rows=__ROWS__;
const materials=__MATERIALS__;
const defaultMaterial=document.getElementById('defaultMaterial');
const defaultDensity=document.getElementById('defaultDensity');
function options(selected){return Object.keys(materials).map(k=>'<option '+(k===selected?'selected':'')+'>'+escapeHtml(k)+'</option>').join('');}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function render(){
defaultMaterial.innerHTML=options(defaultMaterial.value||Object.keys(materials)[0]);
defaultDensity.value=materials[defaultMaterial.value];
document.getElementById('parts').innerHTML=rows.map((r,i)=>'<tr><td>'+r.side+'</td><td>'+escapeHtml(r.name)+'</td><td>'+r.count+'</td><td>'+r.volume+'</td><td><select data-i="'+i+'" data-k="material">'+options(r.material)+'</select></td><td><input type="number" min="0.001" step="any" data-i="'+i+'" data-k="density" value="'+r.density+'"></td><td class="unit"></td><td class="sum"></td></tr>').join('');
recalc();}
function recalc(){
let total=0;
document.querySelectorAll('#parts tr').forEach((tr,i)=>{const r=rows[i],unit=r.volume*1e-9*r.density,sum=unit*r.count;total+=sum;tr.querySelector('.unit').textContent=unit.toFixed(5);tr.querySelector('.sum').textContent=sum.toFixed(5);});
document.getElementById('total').textContent='Łączna masa A + B: '+total.toFixed(5)+' kg';}
document.getElementById('parts').addEventListener('change',e=>{
const i=Number(e.target.dataset.i),key=e.target.dataset.k;if(!key)return;
if(key==='material'){rows[i].material=e.target.value;rows[i].density=materials[e.target.value];e.target.closest('tr').querySelector('input').value=rows[i].density;}
else {const v=Number(e.target.value);if(!(v>0&&Number.isFinite(v))){e.target.value=rows[i].density;return;}rows[i].density=v;}
recalc();});
defaultMaterial.addEventListener('change',()=>defaultDensity.value=materials[defaultMaterial.value]);
function applyDefault(){const d=Number(defaultDensity.value);if(!(d>0&&Number.isFinite(d)))return alert('Nieprawidłowa gęstość');rows.forEach(r=>{r.material=defaultMaterial.value;r.density=d;});render();}
function addMaterial(){const name=prompt('Nazwa nowego materiału:');if(!name||!name.trim())return;const d=Number(prompt('Gęstość [kg/m³]:'));if(!(d>0&&Number.isFinite(d)))return alert('Nieprawidłowa gęstość');materials[name.trim()]=d;defaultMaterial.innerHTML=options(name.trim());defaultMaterial.value=name.trim();defaultDensity.value=d;render();}
function exportCsv(){const lines=[['Model','Nazwa','Ilość','Objętość mm3','Materiał','Gęstość kg/m3','Masa 1 szt kg','Masa łączna kg'],...rows.map(r=>[r.side,r.name,r.count,r.volume,r.material,r.density,r.volume*1e-9*r.density,r.volume*1e-9*r.density*r.count])];const csv=lines.map(a=>a.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(';')).join('\\r\\n');const link=document.createElement('a');link.href=URL.createObjectURL(new Blob(['\\ufeff'+csv],{type:'text/csv;charset=utf-8'}));link.download='MASA_MATERIALY.csv';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),500);}
render();
</script></html>""".replace("__ROWS__",payload).replace("__MATERIALS__",library)
