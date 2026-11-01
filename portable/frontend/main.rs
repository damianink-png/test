#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use dscompare_core::{self as core,Runtime,Request,Snapshot};
use serde_json::Value;
use std::{fs,path::{Path,PathBuf}};
use tauri::{Manager,State,AppHandle};
use tauri_plugin_opener::OpenerExt;
fn engine(app:&AppHandle)->Result<Vec<String>,String>{
 if cfg!(debug_assertions){if let Ok(raw)=std::env::var("DSCOMPARE_ENGINE_COMMAND"){let args:Vec<String>=serde_json::from_str(&raw).map_err(|e|format!("DSCOMPARE_ENGINE_COMMAND: {e}"))?;if !args.is_empty(){return Ok(args)}}}
 let path=app.path().resource_dir().map_err(|e|e.to_string())?.join("engine/DSCompare/DSCompare.exe");
 if !path.is_file(){return Err("Nie znaleziono pakietu silnika CAD. Zainstaluj pełny pakiet DS Compare; sam plik EXE interfejsu nie wystarcza.".into())}Ok(vec![path.to_string_lossy().into_owned()])
}
#[tauri::command]
fn environment(app:AppHandle)->Value{serde_json::json!({"engine_ready":engine(&app).is_ok(),"build":format!("Desktop {} · RC9",env!("CARGO_PKG_VERSION")),"platform":std::env::consts::OS})}
#[tauri::command]
fn startup_ready(app:AppHandle,drag_drop_ready:bool)->Result<(),String>{
 engine(&app)?;let smoke=std::env::var("DSCOMPARE_PORTABLE_SMOKE").as_deref()==Ok("1");
 if smoke {
  if !drag_drop_ready{return Err("Test: brak aktywnej obsługi przeciągania plików".into())}
  let window=app.get_webview_window("main").ok_or("Brak okna")?;
  if let Some(monitor)=window.current_monitor().map_err(|e|e.to_string())?{let size=window.outer_size().map_err(|e|e.to_string())?;let area=monitor.work_area();if size.width>area.size.width||size.height>area.size.height{return Err("Test: okno przekracza obszar roboczy ekranu".into())}}
  let folder=std::env::temp_dir().join(format!("DSCompare_bom_smoke_{}",std::process::id()));fs::create_dir_all(&folder).map_err(|e|e.to_string())?;
  fs::write(folder.join("RAPORT.html"),"<details class=\"panel bom-panel\"><summary>BOM A</summary><table><tr><td>Only-A</td></tr></table></details><details class=\"panel bom-panel\"><summary>BOM B</summary><table><tr><td>Only-B</td></tr></table></details>").map_err(|e|e.to_string())?;
  let root=folder.canonicalize().map_err(|e|e.to_string())?;let state=app.state::<Runtime>();state.roots.lock().map_err(|e|e.to_string())?.push(root.clone());
  for (name,want,absent) in [("BOM_A.html","Only-A","Only-B"),("BOM_B.html","Only-B","Only-A")]{let path=result_artifact(&state,&root,name)?;let html=fs::read_to_string(path).map_err(|e|e.to_string())?;if !html.contains(want)||html.contains(absent){return Err("Test: niewłaściwa zawartość BOM HTML".into())}}
  state.roots.lock().map_err(|e|e.to_string())?.retain(|p|p!=&root);let _=fs::remove_dir_all(&root);
  eprintln!("NATIVE_LAYOUT_DROPS_AND_HTML_BOM_PASS");
 }
 core::startup::ready()?;
 if smoke{std::thread::spawn(move||{std::thread::sleep(std::time::Duration::from_millis(300));app.exit(0);});}Ok(())
}
#[tauri::command]
fn start_job(app:AppHandle,state:State<Runtime>,request:Request)->Result<Snapshot,String>{let out=app.path().document_dir().map_err(|e|e.to_string())?.join("DSCompare");core::start(&state,request,engine(&app)?,&out)}
#[tauri::command]
fn poll_job(state:State<Runtime>)->Result<Option<Snapshot>,String>{let mut g=state.job.lock().map_err(|e|e.to_string())?;g.as_mut().map(core::snapshot).transpose()}
#[tauri::command]
fn cancel_job(state:State<Runtime>)->Result<(),String>{let mut g=state.job.lock().map_err(|e|e.to_string())?;if let Some(j)=g.as_mut(){core::cancel(j)?;}Ok(())}
#[tauri::command]
fn answer_question(state:State<Runtime>,token:String,decision:String)->Result<(),String>{let mut g=state.job.lock().map_err(|e|e.to_string())?;core::answer(g.as_mut().ok_or("Brak analizy")?,&token,&decision)}
#[tauri::command]
fn load_settings(app:AppHandle)->Result<Option<Value>,String>{let p=app.path().app_config_dir().map_err(|e|e.to_string())?.join("settings.json");Ok(core::read_json(&p))}
#[tauri::command]
fn save_settings(app:AppHandle,settings:Value)->Result<(),String>{core::validate_settings(&settings)?;let dir=app.path().app_config_dir().map_err(|e|e.to_string())?;fs::create_dir_all(&dir).map_err(|e|e.to_string())?;let tmp=dir.join("settings.tmp");let path=dir.join("settings.json");fs::write(&tmp,serde_json::to_vec_pretty(&settings).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;fs::rename(tmp,path).map_err(|e|e.to_string())}
#[tauri::command]
fn load_result(app:AppHandle,state:State<Runtime>,folder:String)->Result<Value,String>{let path=PathBuf::from(folder).canonicalize().map_err(|e|e.to_string())?;let result=core::read_json(&path.join("PODSUMOWANIE.json")).ok_or("Brak poprawnego PODSUMOWANIE.json")?;state.roots.lock().map_err(|e|e.to_string())?.push(path.clone());app.asset_protocol_scope().allow_directory(&path,true).map_err(|e|e.to_string())?;Ok(result)}
fn result_artifact(state:&Runtime,folder:&Path,name:&str)->Result<PathBuf,String>{
 if matches!(name,"BOM_A.html"|"BOM_B.html"){
  let report=core::artifact(state,folder,"RAPORT.html")?;
  let metadata=fs::metadata(&report).map_err(|e|e.to_string())?;if metadata.len()>64*1024*1024{return Err("Raport jest zbyt duży do wydzielenia BOM".into())}
  let source=fs::read_to_string(&report).map_err(|e|e.to_string())?;let html=core::reports::bom_document(&source,if name=="BOM_A.html"{0}else{1})?;
  // core::artifact checks the destination before accepting existing links.
  let path=report.parent().ok_or("Brak folderu raportu")?.join(name);
  if let Ok(metadata)=path.symlink_metadata(){if metadata.file_type().is_symlink(){return Err("BOM nie może być dowiązaniem".into())}core::artifact(state,folder,name)?;}
  fs::write(&path,html).map_err(|e|e.to_string())?;
 }
 core::artifact(state,folder,name)
}
#[tauri::command]
fn artifact_path(app:AppHandle,state:State<Runtime>,folder:String,name:String)->Result<String,String>{let p=result_artifact(&state,Path::new(&folder),&name)?;app.asset_protocol_scope().allow_directory(&folder,true).map_err(|e|e.to_string())?;Ok(p.to_string_lossy().into_owned())}
#[tauri::command]
fn open_artifact(app:AppHandle,state:State<Runtime>,folder:String,name:String)->Result<(),String>{let path=result_artifact(&state,Path::new(&folder),&name)?;app.opener().open_path(path.to_string_lossy().into_owned(),None::<&str>).map_err(|e|e.to_string())}
fn main(){tauri::Builder::default().manage(Runtime::default()).plugin(tauri_plugin_dialog::init()).plugin(tauri_plugin_opener::init()).invoke_handler(tauri::generate_handler![environment,startup_ready,start_job,poll_job,cancel_job,answer_question,load_settings,save_settings,load_result,artifact_path,open_artifact]).setup(|app|{if let Some(window)=app.get_webview_window("main"){if let Some(monitor)=window.current_monitor()?{let scale=monitor.scale_factor();let area=monitor.work_area();let width=(area.size.width as f64/scale*0.92).min(1440.0);let height=(area.size.height as f64/scale*0.92).min(960.0);window.set_min_size(Some(tauri::LogicalSize::new(480.0_f64.min(width),360.0_f64.min(height))))?;window.set_size(tauri::LogicalSize::new(width,height))?;window.center()?;}}Ok(())}).build(tauri::generate_context!()).expect("DS Compare desktop startup").run(|app,event|{if let tauri::RunEvent::ExitRequested{..}=event{let state=app.state::<Runtime>();if let Ok(mut g)=state.job.lock(){if let Some(j)=g.as_mut(){let _=core::cancel(j);}};}});}
