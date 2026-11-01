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
fn startup_ready(app:AppHandle)->Result<(),String>{core::startup::ready()?;if std::env::var("DSCOMPARE_PORTABLE_SMOKE").as_deref()==Ok("1"){std::thread::spawn(move||{std::thread::sleep(std::time::Duration::from_millis(300));app.exit(0);});}Ok(())}
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
#[tauri::command]
fn artifact_path(app:AppHandle,state:State<Runtime>,folder:String,name:String)->Result<String,String>{let p=core::artifact(&state,Path::new(&folder),&name)?;app.asset_protocol_scope().allow_directory(&folder,true).map_err(|e|e.to_string())?;Ok(p.to_string_lossy().into_owned())}
#[tauri::command]
fn open_artifact(app:AppHandle,state:State<Runtime>,folder:String,name:String)->Result<(),String>{let path=core::artifact(&state,Path::new(&folder),&name)?;app.opener().open_path(path.to_string_lossy().into_owned(),None::<&str>).map_err(|e|e.to_string())}
fn main(){tauri::Builder::default().manage(Runtime::default()).plugin(tauri_plugin_dialog::init()).plugin(tauri_plugin_opener::init()).invoke_handler(tauri::generate_handler![environment,startup_ready,start_job,poll_job,cancel_job,answer_question,load_settings,save_settings,load_result,artifact_path,open_artifact]).build(tauri::generate_context!()).expect("DS Compare desktop startup").run(|app,event|{if let tauri::RunEvent::ExitRequested{..}=event{let state=app.state::<Runtime>();if let Ok(mut g)=state.job.lock(){if let Some(j)=g.as_mut(){let _=core::cancel(j);}};}});}
