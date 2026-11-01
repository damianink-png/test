use std::{env,fs,path::PathBuf};
fn main(){
 for key in ["DSCOMPARE_PORTABLE_MANIFEST","DSCOMPARE_PORTABLE_PAYLOAD","DSCOMPARE_ICON"]{println!("cargo:rerun-if-env-changed={key}");}
 let out=PathBuf::from(env::var("OUT_DIR").unwrap());
 let manifest=env::var("DSCOMPARE_PORTABLE_MANIFEST").ok();
 if let Some(path)=manifest{println!("cargo:rerun-if-changed={path}");fs::copy(path,out.join("manifest.json")).unwrap();}
 else{fs::write(out.join("manifest.json"),r#"{"version":"test","files":[]}"#).unwrap();}
 if env::var("CARGO_CFG_TARGET_OS").as_deref()==Ok("windows"){
  if let Ok(path)=env::var("DSCOMPARE_ICON"){let mut res=winres::WindowsResource::new();res.set_icon(&path);res.set("ProductName","DS Compare Portable");res.set("FileDescription","DS Compare · portable launcher");res.compile().unwrap();}
 }
}
