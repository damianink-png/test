"""Add a working material editor to the standalone mass report (offline HTML).

The geometry/BOM is computed once from STEP. Editing materials only updates
derived masses in the report, never STEP or the original BOM source.
"""
from __future__ import annotations

import json
import re
from html import escape, unescape
from pathlib import Path

from .name_encoding import repair_polish_name

MATERIALS = {
    "Stal S235 / S355 / S690": 7850,
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

# Preserve mm³, quoted attributes, JavaScript and stylesheet. Repair only
# existing visible cell text from older mass writers (e.g. "P³yta" -> "Płyta").
def _repair_table_text(markup: str) -> str:
    def fix_body(match):
        body = match.group(0)
        return re.sub(
            r">([^<>]+)<",
            lambda fragment: ">" + escape(
                repair_polish_name(unescape(fragment.group(1))), quote=False
            ) + "<",
            body,
        )
    return re.sub(r"(?is)<tbody\b[^>]*>.*?</tbody\s*>", fix_body, markup)


def enhance_mass_html(folder, density=7850):
    path = Path(folder) / "RAPORT_MASY.html"
    if not path.is_file():
        return False
    initial = path.read_text(encoding="utf-8")
    if 'id="ds-material-enhancement"' in initial:
        return True
    base_density = float(density)
    if not 0 < base_density <= 100000:
        raise ValueError("Nieprawidłowa gęstość do raportu masy")
    if not re.search(r"(?is)<table\b", initial):
        raise ValueError("Raport masy nie zawiera tabeli BOM")
    if not all(re.search(pattern, initial, re.I) for pattern in
               (r"objętość|objetosc", r"ilość|ilosc", r"masa")):
        raise ValueError("Raport masy nie ma wymaganych kolumn BOM")
    html = _repair_table_text(initial)
    # A meta charset is mandatory; writing UTF-8 bytes alone is insufficient
    # for browsers that open the file directly from disk.
    if not re.search(r"(?is)<meta\b[^>]*charset\s*=", html):
        if re.search(r"(?i)<head\b[^>]*>", html):
            html = re.sub(r"(?i)<head\b[^>]*>",
                          lambda m: m.group(0) + '<meta charset="utf-8">',
                          html, count=1)
        elif re.search(r"(?i)<html\b[^>]*>", html):
            html = re.sub(r"(?i)<html\b[^>]*>",
                          lambda m: m.group(0) + '<head><meta charset="utf-8"></head>',
                          html, count=1)
        else:
            html = '<meta charset="utf-8">\n' + html

    enhancement = r"""
<style id="ds-material-enhancement">
.ds-material-tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:18px 0;padding:12px;
  background:#f1f5fa;border:1px solid #cbd5e1;border-radius:8px;color:#1e293b}
.ds-material-tools select,.ds-material-tools button,.ds-material-tools input,
.ds-material-select,.ds-density-input{box-sizing:border-box;padding:6px 8px;border:1px solid #94a3b8;
  border-radius:5px;background:#fff;color:#111827;font:inherit;min-width:100px}
.ds-material-select{width:100%;min-width:155px;max-width:260px}
.ds-density-input{width:110px;min-width:95px}
.ds-material-tools label{display:flex;gap:5px;align-items:center;flex-wrap:wrap}
.ds-material-tools button{cursor:pointer}
.ds-material-tools button:hover{background:#e2e8f0}
.ds-material-totals{font-weight:700;font-size:17px;margin:12px 0;color:#0f172a}
.ds-material-note{font-size:12px;color:#475569;margin:4px 0 14px}
.ds-material-error{color:#b91c1c;font-weight:600;margin:12px 0}
@media(prefers-color-scheme:dark){
  body[data-theme="dark"] .ds-material-tools{background:#1d293a;color:#f1f5f9;border-color:#475569}
  body[data-theme="dark"] .ds-material-tools select,
  body[data-theme="dark"] .ds-material-tools button,
  body[data-theme="dark"] .ds-material-tools input,
  body[data-theme="dark"] .ds-material-select,
  body[data-theme="dark"] .ds-density-input{background:#263448;color:#fff;border-color:#65758a}
  body[data-theme="dark"] .ds-material-totals{color:#f1f5f9}
  body[data-theme="dark"] .ds-material-note{color:#cbd5e1}
}
@media print{.ds-material-tools{display:none}}
</style>
<script id="ds-materials-script">
(function(){
"use strict";
const library=__MATERIALS__;
const baseDensity=__DENSITY__;
function fail(message){
  const node=document.createElement("p");
  node.className="ds-material-error";
  node.textContent="Nie udało się włączyć edycji materiałów: "+message;
  document.body.prepend(node);
}
function run(){
  const tables=Array.from(document.querySelectorAll("table"));
  const table=tables.find(t=>/obj[eę]to[sś][cć]/i.test(t.querySelector("thead")?.textContent||""));
  if(!table){fail("nie znaleziono tabeli objętości BOM");return;}
  const header=Array.from(table.querySelectorAll("thead th"));
  const index=pattern=>header.findIndex(th=>pattern.test(th.textContent.trim()));
  const volumeI=index(/obj[eę]to[sś][cć]/i),qtyI=index(/ilo[sś][cć]/i);
  const unitI=index(/masa (jednej|1|jednostk)/i);
  const totalI=index(/masa (łą|l[aą]cz|całkow|razem)/i);
  const nameI=index(/nazwa|cz[eę][sś][cć]/i);
  if([volumeI,qtyI,unitI,totalI].some(v=>v<0)){
    fail("brakuje kolumn Ilość / Objętość / Masa jednostkowa / Masa łączna");
    return;
  }
  const num=text=>{
    const raw=String(text).replace(/\s|\u00a0/g,"").replace(",",".")
       .replace(/[^\d.eE+\-]/g,"");
    return Number(raw);
  };
  const fmt=value=>Number(value).toLocaleString("pl-PL",
     {minimumFractionDigits:4,maximumFractionDigits:4});
  const validDensity=v=>Number.isFinite(v)&&v>0&&v<=100000;
  let baseMaterial=Object.keys(library).find(k=>library[k]===baseDensity);
  if(!baseMaterial){
    baseMaterial="Gęstość z analizy ("+fmt(baseDensity)+" kg/m³)";
    library[baseMaterial]=baseDensity;
  }
  const thMaterial=document.createElement("th");
  thMaterial.textContent="Materiał";
  const thDensity=document.createElement("th");
  thDensity.textContent="Gęstość [kg/m³]";
  header[volumeI].after(thMaterial);
  thMaterial.after(thDensity);
  const rows=[];
  function fillOptions(select,selected){
    select.replaceChildren();
    for(const name of Object.keys(library)){
      const option=document.createElement("option");
      option.value=name;option.textContent=name;
      select.append(option);
    }
    select.value=library[selected] ? selected : baseMaterial;
  }
  for(const tr of table.querySelectorAll("tbody tr")){
    const cells=Array.from(tr.cells);
    if(cells.length<=Math.max(qtyI,volumeI,unitI,totalI))continue;
    const qty=num(cells[qtyI].textContent),vol=num(cells[volumeI].textContent);
    if(!Number.isInteger(qty)||qty<=0||!Number.isFinite(vol)||vol<0)continue;
    const tdMaterial=document.createElement("td"),tdDensity=document.createElement("td");
    const select=document.createElement("select");
    const input=document.createElement("input");
    select.className="ds-material-select";input.className="ds-density-input";
    select.setAttribute("aria-label","Materiał: "+cells[nameI>=0?nameI:0].textContent.trim());
    input.type="number";input.min="0.001";input.max="100000";input.step="any";
    input.setAttribute("aria-label","Gęstość: "+cells[nameI>=0?nameI:0].textContent.trim());
    fillOptions(select,baseMaterial);input.value=String(baseDensity);
    tdMaterial.append(select);tdDensity.append(input);
    cells[volumeI].after(tdMaterial);tdMaterial.after(tdDensity);
    const row={name:cells[nameI>=0?nameI:0].textContent.trim(),qty,vol,select,input,
               unit:cells[unitI],total:cells[totalI]};
    rows.push(row);
  }
  if(!rows.length){fail("nie znaleziono pozycji z objętością i ilością");return;}
  const toolbar=document.createElement("section");toolbar.className="ds-material-tools";
  toolbar.setAttribute("aria-label","Edytor materiałów BOM");
  const materialAll=document.createElement("select");
  materialAll.setAttribute("aria-label","Materiał dla wszystkich pozycji");
  fillOptions(materialAll,baseMaterial);
  const allLabel=document.createElement("label");
  allLabel.append("Materiał dla wszystkich: ",materialAll);
  const apply=document.createElement("button");apply.textContent="Zastosuj do wszystkich";
  const custom=document.createElement("button");custom.textContent="Dodaj materiał";
  const save=document.createElement("button");save.textContent="Zapisz przypisania JSON";
  const upload=document.createElement("input");upload.type="file";upload.accept=".json";
  upload.setAttribute("aria-label","Wczytaj przypisania materiałów");
  const csv=document.createElement("button");csv.textContent="Eksportuj CSV";
  toolbar.append(allLabel,apply,custom,save,upload,csv);
  const summary=document.createElement("div");summary.className="ds-material-totals";
  summary.setAttribute("aria-live","polite");
  const hint=document.createElement("p");hint.className="ds-material-note";
  hint.textContent="Zmiana materiału lub gęstości przelicza masę od razu. "+
    "Nie zmienia modelu STEP ani pierwotnego BOM. "+
    "Masa w nagłówku oryginalnego raportu odpowiada gęstości początkowej.";
  table.before(toolbar,summary,hint);
  function densityOf(row){
    const value=Number(row.input.value);
    return validDensity(value)?value:baseDensity;
  }
  function update(){
    let sum=0;
    for(const row of rows){
      const density=densityOf(row);
      const mass=row.vol*1e-9*density;
      const full=mass*row.qty;
      row.unit.textContent=fmt(mass);
      row.total.textContent=fmt(full);
      sum+=full;
    }
    summary.textContent="Masa całkowita po wyborze materiałów: "+fmt(sum)+" kg";
  }
  for(const row of rows){
    row.select.addEventListener("change",()=>{
      row.input.value=String(library[row.select.value]);update();
    });
    row.input.addEventListener("input",update);
    row.input.addEventListener("change",()=>{
      if(!validDensity(Number(row.input.value))){
        alert("Gęstość musi być dodatnia i nie większa niż 100000 kg/m³.");
        row.input.value=String(library[row.select.value]||baseDensity);
      }
      update();
    });
  }
  apply.addEventListener("click",()=>{
    for(const row of rows){
      row.select.value=materialAll.value;
      row.input.value=String(library[materialAll.value]);
    }
    update();
  });
  custom.addEventListener("click",()=>{
    const name=prompt("Nazwa materiału:");
    if(!name||!name.trim())return;
    const density=Number(prompt("Gęstość [kg/m³]:"));
    if(!validDensity(density)){alert("Nieprawidłowa gęstość.");return;}
    library[name.trim()]=density;
    for(const row of rows)fillOptions(row.select,row.select.value);
    fillOptions(materialAll,name.trim());
  });
  function download(filename,contents,mime){
    const url=URL.createObjectURL(new Blob([contents],{type:mime}));
    const link=document.createElement("a");link.href=url;link.download=filename;
    link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  save.addEventListener("click",()=>{
    const data={version:2,rows:rows.map(row=>({
       name:row.name,qty:row.qty,volume_mm3:row.vol,
       material:row.select.value,density_kg_m3:densityOf(row)})),materials:library};
    download("MASA_MATERIALY_ZMIANY.json",JSON.stringify(data,null,2),
             "application/json;charset=utf-8");
  });
  upload.addEventListener("change",async()=>{
    const file=upload.files&&upload.files[0];if(!file)return;
    try{
      const data=JSON.parse(await file.text());
      if(data.version!==2||!Array.isArray(data.rows)||data.rows.length!==rows.length)
        throw Error("Inne zestawienie części");
      for(let i=0;i<rows.length;i++){
        const old=rows[i],item=data.rows[i];
        if(!item||old.name!==item.name||old.qty!==item.qty||
           Math.abs(old.vol-item.volume_mm3)>1e-7||
           !validDensity(item.density_kg_m3)||typeof item.material!=="string")
          throw Error("Niepasujący wiersz BOM: "+(i+1));
      }
      if(data.materials&&typeof data.materials==="object"){
        for(const [name,value] of Object.entries(data.materials)){
          if(name!=="__proto__"&&validDensity(value))library[name]=value;
        }
      }
      for(let i=0;i<rows.length;i++){
        const item=data.rows[i],row=rows[i];
        if(!library[item.material])library[item.material]=item.density_kg_m3;
        fillOptions(row.select,item.material);
        row.input.value=String(item.density_kg_m3);
      }
      fillOptions(materialAll,materialAll.value);
      update();
    }catch(error){alert("Nie udało się wczytać przypisań: "+error.message);}
    finally{upload.value="";}
  });
  csv.addEventListener("click",()=>{
    const heading=["Nazwa części","Ilość","Objętość 1 szt [mm³]",
                   "Materiał","Gęstość [kg/m³]","Masa 1 szt [kg]","Masa razem [kg]"];
    const data=[heading,...rows.map(r=>{
      const density=densityOf(r),one=r.vol*1e-9*density;
      return [r.name,r.qty,r.vol,r.select.value,density,one,one*r.qty];
    })];
    const quote=v=>'"'+String(v).replace(/"/g,'""')+'"';
    const text="\uFEFF"+data.map(values=>values.map(quote).join(";")).join("\r\n");
    download("MASA_MATERIALY.csv",text,"text/csv;charset=utf-8");
  });
  update();
}
if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",run,{once:true});
}else run();
})();
</script>
"""
    enhancement = enhancement.replace(
        "__MATERIALS__", json.dumps(MATERIALS, ensure_ascii=False).replace("<", "\\u003c")
    ).replace("__DENSITY__", json.dumps(base_density))
    if re.search(r"(?i)</body\s*>", html):
        html = re.sub(r"(?i)</body\s*>", lambda _: enhancement+"\n</body>",
                      html, count=1)
    elif re.search(r"(?i)</html\s*>", html):
        html = re.sub(r"(?i)</html\s*>", lambda _: enhancement+"\n</html>",
                      html, count=1)
    else:
        html += enhancement
    # Atomic overwrite: never leave behind a half-written report.
    tmp=path.with_suffix(".html.partial")
    try:
        tmp.write_text(html,encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return True
