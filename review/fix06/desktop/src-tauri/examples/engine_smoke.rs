//! Run against real STEP files; CAD executes in the configured worker process.
use dscompare_core::{Runtime,Request,start,snapshot,artifact};
use serde_json::{Value,json};
use std::{path::Path,time::{Instant,Duration},thread};
fn main(){
 let args:Vec<String>=std::env::args().collect();assert_eq!(args.len(),4,"usage: engine_smoke A.step B.step output");
 let engine:Vec<String>=serde_json::from_str(&std::env::var("DSCOMPARE_ENGINE_COMMAND").expect("engine command JSON")).unwrap();
 let runtime=Runtime::default();let request=Request{mode:"compare".into(),files:vec![args[1].clone(),args[2].clone()],settings:json!({"align":false,"preview":true,"step":true})};
 start(&runtime,request,engine,Path::new(&args[3])).unwrap();let deadline=Instant::now()+Duration::from_secs(120);
 loop{let mut g=runtime.job.lock().unwrap();let s=snapshot(g.as_mut().unwrap()).unwrap();
  if !s.running{assert!(s.error.is_none(),"{:?}",s.error);assert_eq!(s.result.as_ref().unwrap()["ok"],true);
   let summary=s.summary.unwrap();assert_eq!(summary["analysis_complete"],true);assert_eq!(summary["preview_3d"]["dual_revisions"],true);
   assert!(summary["records"].as_array().unwrap().iter().all(|r|r["record_index"].is_number()&&r["name_a"].is_string()&&r["verification"]=="confirmed"));
   let progress:Value=s.progress.unwrap();assert!(progress["timestamp_ms"].as_u64().unwrap()>0);assert!(progress["phase"].is_string());
   for name in ["RAPORT.html","PODGLAD_KOLOROW_3D.html","POROWNANIE_KOLORY.step"]{assert!(artifact(&runtime,Path::new(&s.folder),name).unwrap().is_file());}
   println!("REAL_NATIVE_REVIEW_PASS: actual Rust -> Python/OCCT comparison, timestamped progress, enriched complete summary, STEP/report/dual preview");break;
  }
  assert!(Instant::now()<deadline,"native smoke timed out");drop(g);thread::sleep(Duration::from_millis(150));
 }
}
