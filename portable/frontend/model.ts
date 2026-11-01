export type Settings={tolerance:number;density:number;output:string;preview:boolean;step:boolean;bom:boolean;bomCsv:boolean;fastBom:boolean;align:boolean;oldAlpha:number;schema:string;verify:string;flat:boolean;bodyColors:boolean;diffStep:boolean;maxSolids:number;palette:Record<string,string>;theme:'dark'|'light'};
export const defaults:Settings={tolerance:.01,density:7850,output:'',preview:true,step:true,bom:true,bomCsv:false,fastBom:false,align:true,oldAlpha:.4,schema:'AP214IS',verify:'auto',flat:false,bodyColors:false,diffStep:false,maxSolids:20000,palette:{same:'#249b60',moved:'#a855f7',changed:'#f5b82e',added:'#168bff',removed:'#ff4050',changed_common:'#7d899a',uncertain:'#e879c3'},theme:'dark'};
export type Decision={token:string;material_unverified:boolean;unresolved?:boolean;unrelated?:boolean;reason:string;translation_mm:number[];unverified_A:number;unverified_B:number};
export type Job={id:string;folder:string;running:boolean;cancelled:boolean;events:string[];progress?:{timestamp_ms?:number;phase?:string;completed?:number;total?:number;checks?:number};question:Decision|null;result:Record<string,unknown>|null;summary:Summary|null;error:string|null};
export type Row={a_index:number|null;b_index:number|null;status:string;name_a?:string;name_b?:string;note?:string;[key:string]:unknown};
export type Summary={analysis_complete?:boolean;solids_A?:number;solids_B?:number;statuses?:Record<string,number>;records?:Row[];[key:string]:unknown};
export const statuses:Record<string,string>={SAME:'Bez zmian',RENAMED:'Zmieniona nazwa',MOVED:'Przesunięte',CHANGED:'Zmieniona geometria',ADDED:'Dodane',REMOVED:'Usunięte',UNCERTAIN:'Do sprawdzenia'};
export const paletteLabels:Record<string,string>={same:'Bez zmian',moved:'Przesunięte',changed:'Zmieniona geometria',added:'Dodane',removed:'Usunięte',changed_common:'Wspólna',uncertain:'Do sprawdzenia'};

// Separate "Wspólna" is sent as CHANGED_COMMON, keeping the OCCT Common operation unchanged.
// Migrate only untouched legacy default colors; preserve users' custom selections.
const legacyPalette:Record<string,string>={same:'#94a3b8',moved:'#0072b2',changed:'#e69f00',added:'#009e73',removed:'#d55e00',uncertain:'#cc79a7'};
export function restorePalette(stored?:Record<string,string>):Record<string,string>{
 const palette={...defaults.palette};
 if(!stored)return palette;
 const common=stored.changed_common??stored.CHANGED_COMMON??stored.common;
 for(const [key,value] of Object.entries(stored)){
  if(key==='common'||key==='CHANGED_COMMON')continue;
  if(legacyPalette[key]&&value.toLowerCase()===legacyPalette[key])palette[key]=defaults.palette[key];
  else palette[key]=value;
 }
 if(common&&!stored.changed_common)palette.changed_common=common;
 return palette;
}
export function needsReview(r:Row){return r.status==='UNCERTAIN'||r.verification==='unverified';}
export function indexedRows(summary:Summary):Array<Row & {record_index:number}>{return (summary.records||[]).map((r,i)=>({...r,record_index:i}));}
export function visibleRows(rows:Row[],query:string,status:string){const q=query.trim().toLocaleLowerCase('pl');return rows.filter(r=>(!status||r.status===status||(status==='SAME'&&r.status==='RENAMED')||(status==='CHANGES'&&!['SAME','RENAMED'].includes(r.status))||(status==='DIAGNOSTIC'&&needsReview(r)))&&(!q||JSON.stringify(r).toLocaleLowerCase('pl').includes(q)));}
export function validate(s:Settings){if(!Number.isFinite(s.tolerance)||s.tolerance<=0||s.tolerance>10)return 'Tolerancja musi być większa od 0 i nie większa niż 10 mm.';if(!Number.isFinite(s.density)||s.density<=0)return 'Podaj dodatnią gęstość.';if(!Number.isInteger(s.maxSolids)||s.maxSolids<1)return 'Limit brył musi być dodatnią liczbą całkowitą.';return '';}
export function fileName(path:string){return path.split(/[\\/]/).pop()||path;}

export function stepPaths(paths:string[]){if(!paths.length||paths.some(p=>!/^.+\.(step|stp)$/i.test(p)))throw Error('Wybierz wyłącznie pliki STEP (.step lub .stp).');return [...new Set(paths)];}
export function massSummary(value:unknown){if(!value||typeof value!=='object')return null;const s=value as Record<string,unknown>;const mass=s.masa_calosci_kg;if(typeof mass!=='number'||!Number.isFinite(mass))return null;return {mass,models:Number(s.liczba_plikow??1),solids:Number(s.liczba_bryl??0),density:Number(s.gestosc_kg_m3??0)};}
export function hasTranslation(q:Decision){return !q.unresolved&&!q.unrelated&&Array.isArray(q.translation_mm)&&q.translation_mm.length===3&&q.translation_mm.every(Number.isFinite)&&q.translation_mm.some(n=>Math.abs(n)>=0.00005);}
