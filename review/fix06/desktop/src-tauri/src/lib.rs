//! Native process boundary. No CAD operation runs on the UI thread.
use serde::{Deserialize,Serialize};
use serde_json::{Value,json};
use std::{fs,path::{Path,PathBuf},process::{Child,Command,Stdio},sync::Mutex,time::{SystemTime,UNIX_EPOCH}};
#[derive(Deserialize)]
pub struct Request { pub mode:String,pub files:Vec<String>,pub settings:Value }
pub struct Job { pub id:String,pub folder:PathBuf,pub child:Child,pub cancelled:bool,pub answered:Option<String> }
#[derive(Default)]
pub struct Runtime { pub job:Mutex<Option<Job>>,pub roots:Mutex<Vec<PathBuf>> }
#[derive(Serialize)]
pub struct Snapshot { pub id:String,pub folder:String,pub running:bool,pub cancelled:bool,pub events:Vec<String>,pub progress:Option<Value>,pub question:Option<Value>,pub result:Option<Value>,pub summary:Option<Value>,pub error:Option<String> }
pub fn read_json(p:&Path)->Option<Value>{fs::read(p).ok().and_then(|b|serde_json::from_slice(&b).ok())}
pub fn number(v:&Value,k:&str,default:f64)->f64{v.get(k).and_then(Value::as_f64).unwrap_or(default)}
fn flag(v:&Value,k:&str,default:bool)->bool{v.get(k).and_then(Value::as_bool).unwrap_or(default)}
pub fn validate_settings(s:&Value)->Result<(),String>{
 let tol=number(s,"tolerance",0.01);let density=number(s,"density",7850.);let alpha=number(s,"oldAlpha",0.4);let max=number(s,"maxSolids",20000.);
 if !tol.is_finite()||tol<=0.||tol>10.{return Err("Tolerancja poza zakresem (0, 10] mm".into())}
 if !density.is_finite()||density<=0.||density>1e9{return Err("Nieprawidłowa gęstość".into())}
 if !alpha.is_finite()||!(0.0..=1.0).contains(&alpha){return Err("Nieprawidłowa przezroczystość".into())}
 if max.fract()!=0.||!(1.0..=1000000.0).contains(&max){return Err("Nieprawidłowy limit brył".into())}
 Ok(())
}
pub fn worker_args(r:&Request,out:&Path)->Result<Vec<String>,String>{
 validate_settings(&r.settings)?;
 if !["compare","mass","diagnostic"].contains(&r.mode.as_str()){return Err("Nieznany rodzaj analizy".into())}
 if r.mode=="compare"&&r.files.len()!=2{return Err("Wybierz dwa pliki STEP".into())}
 if r.mode=="mass"&&r.files.is_empty(){return Err("Wybierz modele do obliczenia masy".into())}
 for file in &r.files{let path=Path::new(file);let ext=path.extension().and_then(|x|x.to_str()).unwrap_or("").to_lowercase();if !path.is_file()||!["step","stp"].contains(&ext.as_str()){return Err(format!("Nieprawidłowy plik STEP: {file}"))}}
 let s=&r.settings;
 let mut a=vec!["--worker".into(),r.mode.clone(),"--output".into(),out.to_string_lossy().into_owned(),"--tolerance".into(),number(s,"tolerance",0.01).to_string(),"--density".into(),number(s,"density",7850.).to_string(),"--max-solids".into(),number(s,"maxSolids",20000.).to_string()];
 if r.mode=="compare"{
  a.extend(["--a".into(),r.files[0].clone(),"--b".into(),r.files[1].clone(),"--revision-style".into(),"--allow-review-decision".into(),"--old-alpha".into(),number(s,"oldAlpha",0.4).to_string()]);
  for (k,arg,default) in [("step","--generate-step",true),("preview","--preview3d",true),("align","--align-auto",true),("fastBom","--fast-bom",false),("flat","--flat-zw3d",false),("bodyColors","--body-colors",false),("diffStep","--diff-step",false)]{if flag(s,k,default){a.push(arg.into())}}
  if !flag(s,"bom",true){a.push("--no-bom".into())}if !flag(s,"bomCsv",true){a.push("--no-bom-csv".into())}
  let schema=s["schema"].as_str().unwrap_or("AP214IS");let verify=s["verify"].as_str().unwrap_or("auto");
  if !["AP214IS","AP242DIS"].contains(&schema)||!["auto","full","fast"].contains(&verify){return Err("Nieprawidłowe ustawienia STEP".into())}
  a.extend(["--schema".into(),schema.into(),"--step-verify".into(),verify.into()]);
  let mut palette=serde_json::Map::new();if let Some(colors)=s["palette"].as_object(){for (key,val) in colors{if let Some(h)=val.as_str(){if h.len()!=7||!h.starts_with('#')||!h[1..].bytes().all(|b|b.is_ascii_hexdigit()){return Err("Nieprawidłowy kolor".into())}let rgb:Vec<f64>=(1..7).step_by(2).map(|i|u8::from_str_radix(&h[i..i+2],16).unwrap() as f64/255.).collect();palette.insert(key.to_uppercase(),json!(rgb));}}}
  a.extend(["--palette".into(),Value::Object(palette).to_string()]);
 }else if r.mode=="mass"{let list=out.join("inputs.json");fs::write(&list,serde_json::to_vec(&r.files).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;a.extend(["--inputs-file".into(),list.to_string_lossy().into_owned()]);}
 Ok(a)
}
pub fn unique_folder(root:&Path)->Result<PathBuf,String>{fs::create_dir_all(root).map_err(|e|e.to_string())?;let stamp=SystemTime::now().duration_since(UNIX_EPOCH).map_err(|e|e.to_string())?.as_nanos();let folder=root.join(format!("DSCompare_{stamp}"));fs::create_dir(&folder).map_err(|e|e.to_string())?;folder.canonicalize().map_err(|e|e.to_string())}
pub fn start(runtime:&Runtime,r:Request,engine:Vec<String>,default_out:&Path)->Result<Snapshot,String>{
 let mut guard=runtime.job.lock().map_err(|e|e.to_string())?;
 if let Some(job)=guard.as_mut(){if job.child.try_wait().map_err(|e|e.to_string())?.is_none(){return Err("Analiza już trwa".into())}}
 let root=r.settings["output"].as_str().filter(|x|!x.is_empty()).map(PathBuf::from).unwrap_or_else(||default_out.into());
 let folder=unique_folder(&root)?;let args=worker_args(&r,&folder)?;
 let first=engine.first().ok_or("Brak silnika CAD")?;let mut cmd=Command::new(first);cmd.args(&engine[1..]).args(args).env("PYTHONUTF8","1").env("QT_QPA_PLATFORM","offscreen");
 cmd.stdout(Stdio::from(fs::File::create(folder.join("ENGINE_STDOUT.log")).map_err(|e|e.to_string())?));cmd.stderr(Stdio::from(fs::File::create(folder.join("ENGINE_STDERR.log")).map_err(|e|e.to_string())?));
 #[cfg(windows)] {use std::os::windows::process::CommandExt;cmd.creation_flags(0x08000000);}
 #[cfg(unix)] {use std::os::unix::process::CommandExt;cmd.process_group(0);}
 let child=cmd.spawn().map_err(|e|format!("Nie można uruchomić silnika: {e}"))?;
 let id=folder.file_name().unwrap().to_string_lossy().into_owned();runtime.roots.lock().map_err(|e|e.to_string())?.push(folder.clone());
 *guard=Some(Job{id,folder,child,cancelled:false,answered:None});snapshot(guard.as_mut().unwrap())
}
pub fn snapshot(job:&mut Job)->Result<Snapshot,String>{
 let status=job.child.try_wait().map_err(|e|e.to_string())?;let running=status.is_none();
 let result=read_json(&job.folder.join("_WYNIK_V37.json"));
 // Do not consume a report before the worker has committed its result.
 let summary=if !running&&result.as_ref().and_then(|r|r["ok"].as_bool())==Some(true){read_json(&job.folder.join("PODSUMOWANIE.json"))}else{None};
 let mut question=if running{read_json(&job.folder.join("_WYROWNANIE_PYTANIE.json"))}else{None};
 if question.as_ref().and_then(|q|q["token"].as_str())==job.answered.as_deref(){question=None;}
 let history=fs::read_to_string(job.folder.join("_POSTEP_V37.jsonl")).unwrap_or_default();
 let values=history.lines().rev().filter_map(|line|serde_json::from_str::<Value>(line).ok()).take(100).collect::<Vec<_>>();
 let progress=values.first().cloned();
 let events=values.iter().rev().filter_map(|v|v["tekst"].as_str().map(str::to_owned)).collect();
 let error=if !running&&!job.cancelled&&result.as_ref().and_then(|r|r["ok"].as_bool())!=Some(true){Some(result.as_ref().and_then(|r|r["error"].as_str()).map(str::to_owned).unwrap_or_else(||format!("Proces zakończył się bez poprawnego wyniku ({status:?}). Sprawdź ENGINE_STDERR.log.")))}else{None};
 Ok(Snapshot{id:job.id.clone(),folder:job.folder.to_string_lossy().into_owned(),running,cancelled:job.cancelled,events,progress,question,result,summary,error})
}
pub fn answer(job:&mut Job,token:&str,decision:&str)->Result<(),String>{
 if job.child.try_wait().map_err(|e|e.to_string())?.is_some(){return Err("Analiza już zakończona".into())}
 let q=read_json(&job.folder.join("_WYROWNANIE_PYTANIE.json")).ok_or("Brak oczekującego pytania")?;
 if q["token"].as_str()!=Some(token){return Err("Nieaktualne pytanie".into())}
 let allowed=if q["material_unverified"].as_bool()==Some(true){vec!["review","cancel"]}else{vec!["align","original","search","cancel"]};if !allowed.contains(&decision){return Err("Nieprawidłowa decyzja".into())}
 let tmp=job.folder.join("_ANSWER.tmp");let target=job.folder.join("_WYROWNANIE_ODPOWIEDZ.json");fs::write(&tmp,json!({"token":token,"decision":decision}).to_string()).map_err(|e|e.to_string())?;
 if target.exists(){fs::remove_file(&target).map_err(|e|e.to_string())?;}fs::rename(tmp,target).map_err(|e|e.to_string())?;job.answered=Some(token.into());Ok(())
}
pub fn cancel(job:&mut Job)->Result<(),String>{
 if job.child.try_wait().map_err(|e|e.to_string())?.is_none(){
  #[cfg(windows)] {let result=Command::new("taskkill").args(["/F","/T","/PID",&job.child.id().to_string()]).output().map_err(|e|e.to_string())?;if !result.status.success(){job.child.kill().map_err(|e|e.to_string())?;}}
  #[cfg(unix)] {unsafe{libc::kill(-(job.child.id() as i32),libc::SIGKILL);}}
  let _=job.child.wait();job.cancelled=true;
 }Ok(())
}
pub fn artifact(runtime:&Runtime,folder:&Path,name:&str)->Result<PathBuf,String>{
 let root=folder.canonicalize().map_err(|e|e.to_string())?;
 if !runtime.roots.lock().map_err(|e|e.to_string())?.contains(&root){return Err("Folder nie jest otwartym wynikiem".into())}
 if name=="folder"{return Ok(root)}
 let valid=["RAPORT.html","PODGLAD_KOLOROW_3D.html","POROWNANIE_KOLORY.step","ZMIANY.csv","BOM_A.csv","BOM_B.csv","PODSUMOWANIE.json","DIAGNOSTYKA_BLEDU.txt","ENGINE_STDERR.log","ANALIZA_NIEKOMPLETNA.txt","RAPORT_MASY.html","RAPORT_TESTOW.html"];
 if !valid.contains(&name){return Err("Nieobsługiwany plik wyniku".into())}
 let file=root.join(name).canonicalize().map_err(|_|format!("Brak pliku {name}. Sprawdź ustawienia eksportu."))?;
 if !file.starts_with(&root)||!file.is_file(){return Err("Plik poza folderem wyników".into())}Ok(file)
}
impl Drop for Runtime{fn drop(&mut self){if let Ok(g)=self.job.get_mut(){if let Some(j)=g.as_mut(){let _=cancel(j);}}}}
#[cfg(test)] mod tests {
 use super::*;
 #[test] fn invalid_tolerance(){assert!(validate_settings(&json!({"tolerance":0})).is_err());assert!(validate_settings(&json!({"oldAlpha":2})).is_err());}
 #[test] fn traversal_and_foreign_folders_are_rejected(){let runtime=Runtime::default();assert!(artifact(&runtime,Path::new("."),"../Cargo.toml").is_err());}
 #[test] fn exact_worker_flags_and_palette(){let out=std::env::temp_dir().join(format!("dscompare-test-{}",std::process::id()));fs::create_dir_all(&out).unwrap();let f=out.join("model.stp");fs::write(&f,"test").unwrap();let r=Request{mode:"compare".into(),files:vec![f.to_string_lossy().into(),f.to_string_lossy().into()],settings:json!({"tolerance":0.01,"oldAlpha":0.6,"palette":{"added":"#009e73"},"bomCsv":false})};let a=worker_args(&r,&out).unwrap();assert!(a.contains(&"--allow-review-decision".into()));assert!(a.contains(&"--no-bom-csv".into()));assert!(!a.contains(&"--align".into()));let p=a.iter().position(|x|x=="--palette").unwrap();let c:Value=serde_json::from_str(&a[p+1]).unwrap();assert_eq!(c["ADDED"][0],0.);fs::remove_dir_all(out).unwrap();}
}
