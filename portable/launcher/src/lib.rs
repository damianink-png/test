use fs2::FileExt;
use serde::{Deserialize,Serialize};
use sha2::{Sha256,Digest};
use std::{collections::HashSet,fs::{self,File,OpenOptions},io::{self,Read,Write,Cursor},path::{Path,PathBuf,Component},sync::atomic::{AtomicBool,Ordering},thread,time::{Duration,SystemTime,UNIX_EPOCH}};
#[derive(Clone,Debug,Serialize,Deserialize)]
pub struct Entry{pub path:String,pub size:u64,pub sha256:String}
#[derive(Clone,Debug,Serialize,Deserialize)]
pub struct Manifest{pub version:String,pub files:Vec<Entry>}
#[derive(Clone,Debug)]
pub struct Progress{pub text:String,pub percent:Option<u32>}
pub type Result<T>=std::result::Result<T,String>;
fn error(e:impl std::fmt::Display)->String{e.to_string()}
pub fn digest(bytes:&[u8])->String{format!("{:x}",Sha256::digest(bytes))}
pub fn relative(value:&str)->Result<PathBuf>{
 if value.is_empty()||value.contains(['\\',':','\0']){return Err("Nieprawidłowa ścieżka pakietu".into())}
 let p=Path::new(value);if p.components().any(|c|!matches!(c,Component::Normal(_))){return Err("Ścieżka poza pakietem".into())}Ok(p.into())
}
impl Manifest{
 pub fn parse(text:&str)->Result<Self>{let m:Self=serde_json::from_str(text).map_err(error)?;let mut seen=HashSet::new();if m.files.is_empty()||m.files.len()>30000{return Err("Nieprawidłowy manifest pakietu".into())}
  for f in &m.files{relative(&f.path)?;if !seen.insert(f.path.to_lowercase())||f.sha256.len()!=64||!f.sha256.bytes().all(|c|c.is_ascii_hexdigit()){return Err("Niespójny manifest pakietu".into())}}
  Ok(m)
 }
 pub fn total(&self)->u64{self.files.iter().map(|f|f.size).sum()}
}
fn cancelled(stop:&AtomicBool)->Result<()>{if stop.load(Ordering::Relaxed){Err("Uruchamianie anulowane".into())}else{Ok(())}}
fn percentage(done:u64,total:u64)->Option<u32>{Some(if total==0{100}else{(done.saturating_mul(100)/total).min(100) as u32})}
fn hash_file(path:&Path,stop:&AtomicBool)->Result<(String,u64)>{let mut file=File::open(path).map_err(error)?;let mut hash=Sha256::new();let mut size=0;let mut buf=vec![0;1024*1024];loop{cancelled(stop)?;let n=file.read(&mut buf).map_err(error)?;if n==0{break}hash.update(&buf[..n]);size+=n as u64;}Ok((format!("{:x}",hash.finalize()),size))}
pub fn verify(root:&Path,m:&Manifest,stop:&AtomicBool,progress:&mut impl FnMut(Progress))->Result<()>{
 let base=root.canonicalize().map_err(error)?;let mut done=0;
 for e in &m.files{cancelled(stop)?;let path=root.join(relative(&e.path)?);let meta=fs::symlink_metadata(&path).map_err(error)?;
  if !meta.is_file()||meta.file_type().is_symlink()||!path.canonicalize().map_err(error)?.starts_with(&base){return Err(format!("Nieprawidłowy plik pakietu: {}",e.path))}
  let (hash,size)=hash_file(&path,stop)?;if size!=e.size||hash!=e.sha256{return Err(format!("Uszkodzony plik pakietu: {}",e.path))}
  done+=size;progress(Progress{text:"Sprawdzanie plików programu…".into(),percent:percentage(done,m.total())});
 }Ok(())
}
pub fn extract(bytes:&[u8],root:&Path,m:&Manifest,stop:&AtomicBool,progress:&mut impl FnMut(Progress))->Result<()>{
 let mut archive=zip::ZipArchive::new(Cursor::new(bytes)).map_err(error)?;if archive.len()!=m.files.len(){return Err("Niepełna zawartość pakietu".into())}
 fs::create_dir_all(root).map_err(error)?;let mut done=0;let mut seen=HashSet::new();let entries:std::collections::HashMap<_,_>=m.files.iter().map(|e|(e.path.as_str(),e)).collect();
 for i in 0..archive.len(){cancelled(stop)?;let mut file=archive.by_index(i).map_err(error)?;let name=file.name().to_owned();let rel=relative(&name)?;
  let e=entries.get(name.as_str()).ok_or("Nieoczekiwany plik w pakiecie")?;
  if !seen.insert(name.clone())||file.is_dir()||file.size()!=e.size||file.unix_mode().map(|v|v&0o170000==0o120000).unwrap_or(false){return Err("Nieprawidłowy element ZIP".into())}
  let path=root.join(rel);fs::create_dir_all(path.parent().unwrap()).map_err(error)?;let mut out=OpenOptions::new().write(true).create_new(true).open(path).map_err(error)?;let mut hash=Sha256::new();let mut count=0;let mut buffer=vec![0;1024*1024];
  loop{cancelled(stop)?;let n=file.read(&mut buffer).map_err(error)?;if n==0{break}out.write_all(&buffer[..n]).map_err(error)?;hash.update(&buffer[..n]);count+=n as u64;done+=n as u64;progress(Progress{text:"Przygotowywanie wersji przenośnej…".into(),percent:percentage(done,m.total())});}
  if count!=e.size||format!("{:x}",hash.finalize())!=e.sha256{return Err(format!("Błąd integralności: {}",e.path))}
 }Ok(())
}
pub fn prepare(bytes:&[u8],manifest_text:&str,cache:&Path,stop:&AtomicBool,progress:&mut impl FnMut(Progress))->Result<PathBuf>{
 let m=Manifest::parse(manifest_text)?;fs::create_dir_all(cache).map_err(error)?;
 let key=digest(manifest_text.as_bytes());let base=cache.join(&key[..24]);fs::create_dir_all(&base).map_err(error)?;
 let lock=OpenOptions::new().read(true).write(true).create(true).truncate(false).open(base.join("cache.lock")).map_err(error)?;
 loop{cancelled(stop)?;match lock.try_lock_exclusive(){Ok(())=>break,Err(e) if (e.kind()==io::ErrorKind::WouldBlock||e.raw_os_error()==fs2::lock_contended_error().raw_os_error())=>{progress(Progress{text:"Oczekiwanie na przygotowanie programu…".into(),percent:None});thread::sleep(Duration::from_millis(50));},Err(e)=>return Err(error(e))}}
 if let Ok(current)=fs::read_to_string(base.join("CURRENT")){if let Ok(rel)=relative(current.trim()){let root=base.join(rel);if verify(&root,&m,stop,progress).is_ok(){return Ok(root)}}}
 cancelled(stop)?;let stamp=SystemTime::now().duration_since(UNIX_EPOCH).map_err(error)?.as_nanos();let name=format!("generation-{}-{stamp}",std::process::id());let draft=base.join(format!(".{name}.partial"));
 if let Err(e)=extract(bytes,&draft,&m,stop,progress){let _=fs::remove_dir_all(&draft);return Err(e)}
 if let Err(e)=cancelled(stop){let _=fs::remove_dir_all(&draft);return Err(e)};let root=base.join(&name);fs::rename(&draft,&root).map_err(error)?;
 let pointer=base.join("CURRENT.partial");fs::write(&pointer,name.as_bytes()).map_err(error)?;fs::rename(pointer,base.join("CURRENT")).map_err(error)?;
 Ok(root)
}
pub fn readiness_path(token:&str)->Result<PathBuf>{if token.is_empty()||token.len()>80||!token.bytes().all(|c|c.is_ascii_alphanumeric()||c==b'_'){return Err("Nieprawidłowy identyfikator startu".into())}Ok(std::env::temp_dir().join(format!("DSCompare_startup_{token}.ready")))}


pub fn payload_range(bytes:&[u8])->Result<std::ops::Range<usize>>{
 if bytes.len()<32{return Err("Niepełny plik EXE".into())}
 let footer=&bytes[bytes.len()-32..];if &footer[..16]!=b"DSCPORTABLE01ZIP"{return Err("Brak danych wersji jednoplikowej".into())}
 let offset=u64::from_le_bytes(footer[16..24].try_into().unwrap());let size=u64::from_le_bytes(footer[24..32].try_into().unwrap());
 if offset==0||size<4||offset.checked_add(size)!=Some((bytes.len()-32)as u64){return Err("Uszkodzony pakiet wersji jednoplikowej".into())}
 let range=offset as usize..(offset+size)as usize;if &bytes[range.start..range.start+4]!=b"PK\x03\x04"{return Err("Nieprawidłowy pakiet ZIP w EXE".into())}Ok(range)
}

#[cfg(test)]mod tests{
 use super::*;use zip::write::SimpleFileOptions;
 fn fixture()->(Vec<u8>,String){let files=[("DSCompareDesktop.exe",b"native-ui".as_slice()),("engine/DSCompare/DSCompare.exe",b"tested-engine".as_slice())];let mut z=zip::ZipWriter::new(Cursor::new(Vec::new()));let mut manifest=Manifest{version:"test".into(),files:vec![]};for(name,bytes)in files{z.start_file(name,SimpleFileOptions::default()).unwrap();z.write_all(bytes).unwrap();manifest.files.push(Entry{path:name.into(),size:bytes.len()as u64,sha256:digest(bytes)});}let bytes=z.finish().unwrap().into_inner();(bytes,serde_json::to_string(&manifest).unwrap())}
 fn temp()->PathBuf{let path=std::env::temp_dir().join(format!("dsc-portable-test-{}-{}",std::process::id(),SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()));fs::create_dir(&path).unwrap();path}
 #[test]fn cache_reuse_and_repair_never_overwrite_active_generation(){let (zip,manifest)=fixture();let base=temp();let stop=AtomicBool::new(false);let mut log=|_:Progress|{};let first=prepare(&zip,&manifest,&base,&stop,&mut log).unwrap();let second=prepare(&zip,&manifest,&base,&stop,&mut log).unwrap();assert_eq!(first,second);fs::write(first.join("DSCompareDesktop.exe"),b"tampered").unwrap();let repaired=prepare(&zip,&manifest,&base,&stop,&mut log).unwrap();assert_ne!(first,repaired);assert_eq!(fs::read(first.join("DSCompareDesktop.exe")).unwrap(),b"tampered");assert_eq!(fs::read(repaired.join("DSCompareDesktop.exe")).unwrap(),b"native-ui");assert_eq!(prepare(&zip,&manifest,&base,&stop,&mut log).unwrap(),repaired);fs::remove_dir_all(base).unwrap();}
 #[test]fn cancelled_extraction_is_not_published(){let(zip,manifest)=fixture();let base=temp();let stop=AtomicBool::new(false);let mut update=|_:Progress|{stop.store(true,Ordering::Relaxed);};assert!(prepare(&zip,&manifest,&base,&stop,&mut update).is_err());assert!(!fs::read_dir(&base).unwrap().next().unwrap().unwrap().path().join("CURRENT").exists());fs::remove_dir_all(base).unwrap();}
 #[test]fn traversal_and_extra_files_are_rejected(){for path in ["../evil","/absolute","C:/drive","a\\b",""]{assert!(relative(path).is_err());}let(zip,mut manifest)=fixture();manifest=manifest.replace("DSCompareDesktop.exe","../DSCompareDesktop.exe");let base=temp();assert!(prepare(&zip,&manifest,&base,&AtomicBool::new(false),&mut|_|{}).is_err());let mut m=Manifest::parse(&fixture().1).unwrap();m.files.pop();let target=base.join("bad");assert!(extract(&zip,&target,&m,&AtomicBool::new(false),&mut|_|{}).is_err());fs::remove_dir_all(base).unwrap();}
 #[test]fn bad_hash_is_rejected(){let(zip,manifest)=fixture();let mut m=Manifest::parse(&manifest).unwrap();m.files[0].sha256="0".repeat(64);let base=temp();assert!(extract(&zip,&base,&m,&AtomicBool::new(false),&mut|_|{}).is_err());fs::remove_dir_all(base).unwrap();}
 #[test]fn concurrent_launches_share_one_committed_cache(){let(zip,manifest)=fixture();let base=temp();let handles:Vec<_>=(0..2).map(|_|{let z=zip.clone();let m=manifest.clone();let b=base.clone();std::thread::spawn(move||prepare(&z,&m,&b,&AtomicBool::new(false),&mut|_|{}).unwrap())}).collect();let paths:Vec<_>=handles.into_iter().map(|h|h.join().unwrap()).collect();assert_eq!(paths[0],paths[1]);fs::remove_dir_all(base).unwrap();}
 #[test]fn overlay_bounds_are_checked(){let mut data=b"MZ-stubPK\x03\x04-payload".to_vec();let offset=7u64;let size=data.len()as u64-offset;data.extend_from_slice(b"DSCPORTABLE01ZIP");data.extend_from_slice(&offset.to_le_bytes());data.extend_from_slice(&size.to_le_bytes());let range=payload_range(&data).unwrap();assert_eq!(&data[range],b"PK\x03\x04-payload");let n=data.len();data[n-1]=255;assert!(payload_range(&data).is_err());}
 #[test]fn startup_token_is_a_basename_only(){assert!(readiness_path("123_456").unwrap().ends_with("DSCompare_startup_123_456.ready"));for token in ["../x","a/b","a\\b","C:x",""]{assert!(readiness_path(token).is_err());}}
}
