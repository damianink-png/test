//! Readiness handshake for the optional portable launcher. No CAD work here.
use std::path::PathBuf;
pub fn readiness_path(token:&str)->Result<PathBuf,String>{if token.is_empty()||token.len()>80||!token.bytes().all(|c|c.is_ascii_alphanumeric()||c==b'_'){return Err("Nieprawidłowy identyfikator startu".into())}Ok(std::env::temp_dir().join(format!("DSCompare_startup_{token}.ready")))}
pub fn ready()->Result<(),String>{if let Ok(token)=std::env::var("DSCOMPARE_STARTUP_TOKEN"){let path=readiness_path(&token)?;std::fs::write(path,b"ready").map_err(|e|e.to_string())?;}Ok(())}
#[cfg(test)]mod tests{use super::*;#[test]fn rejects_path_injection(){for value in ["","../x","x/y","C:x","x\\y"]{assert!(readiness_path(value).is_err());}assert!(readiness_path("123_456").unwrap().ends_with("DSCompare_startup_123_456.ready"));}}
