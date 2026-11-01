#![cfg_attr(windows, windows_subsystem = "windows")]
mod splash;
use dscompare_portable::{readiness_path, Progress, Result};
use std::{
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::{atomic::Ordering, Arc},
    thread,
    time::{Duration, SystemTime, UNIX_EPOCH},
};
const MANIFEST: &str = include_str!(concat!(env!("OUT_DIR"), "/manifest.json"));

fn command(exe: &Path) -> Command {
    let mut c = Command::new(exe);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x08000000);
    }
    c
}
fn work(state: Arc<splash::Shared>) -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut update = |p: Progress| {
        *state.status.lock().unwrap() = p;
    };
    if let Some(i) = args.iter().position(|s| s == "--splash-demo-ms") {
        let ms: u64 = args
            .get(i + 1)
            .ok_or("Brak czasu demonstracji")?
            .parse()
            .map_err(|_| "Niepoprawny czas")?;
        let start = std::time::Instant::now();
        while start.elapsed() < Duration::from_millis(ms) {
            if state.cancel.load(Ordering::Relaxed) {
                return Err("Anulowano".into());
            }
            update(Progress {
                text: "Podgląd animacji startowej…".into(),
                percent: None,
            });
            thread::sleep(Duration::from_millis(30));
        }
        return Ok(());
    }
    #[cfg(not(feature = "onefile"))]
    let manifest = dscompare_portable::Manifest::parse(MANIFEST)?;
    #[cfg(feature = "onefile")]
    let root = {
        let path = std::env::current_exe().map_err(|e| e.to_string())?;
        let mut options = std::fs::OpenOptions::new();
        options.read(true);
        #[cfg(windows)]
        {
            use std::os::windows::fs::OpenOptionsExt;
            options.share_mode(1);
        }
        let file = options.open(path).map_err(|e| e.to_string())?;
        // Windows denies concurrent writes/deletion while this read-only mapping lives.
        let mapped =
            unsafe { memmap2::MmapOptions::new().map(&file) }.map_err(|e| e.to_string())?;
        let range = dscompare_portable::payload_range(&mapped)?;
        let base = std::env::var_os("LOCALAPPDATA")
            .map(PathBuf::from)
            .ok_or("Brak folderu LOCALAPPDATA użytkownika")?
            .join("DSCompare/portable");
        dscompare_portable::prepare(&mapped[range], MANIFEST, &base, &state.cancel, &mut update)?
    };
    #[cfg(not(feature = "onefile"))]
    let root = {
        let path = std::env::current_exe()
            .map_err(|e| e.to_string())?
            .parent()
            .ok_or("Brak folderu programu")?
            .join("app");
        dscompare_portable::verify(&path, &manifest, &state.cancel, &mut update)?;
        path
    };
    if args.iter().any(|s| s == "--verify-only") {
        return Ok(());
    }
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_nanos();
    let token = format!("{}_{stamp}", std::process::id());
    let ready = readiness_path(&token)?;
    let webview = root.join("WebView2");
    if !webview.join("msedgewebview2.exe").is_file() {
        return Err("Nie znaleziono dołączonego środowiska WebView2".into());
    }
    #[cfg(windows)]
    {
        update(Progress {
            text: "Przygotowywanie środowiska podglądu…".into(),
            percent: None,
        });
        for sid in ["*S-1-15-2-2:(OI)(CI)(RX)", "*S-1-15-2-1:(OI)(CI)(RX)"] {
            let output = command(Path::new("icacls.exe"))
                .arg(&webview)
                .args(["/grant", sid, "/Q"])
                .output()
                .map_err(|e| e.to_string())?;
            if !output.status.success() {
                return Err(
                    "Nie można przygotować uprawnień środowiska WebView2 w folderze użytkownika"
                        .into(),
                );
            }
        }
    }
    update(Progress {
        text: "Uruchamianie interfejsu CAD…".into(),
        percent: None,
    });
    let mut c = command(&root.join("DSCompareDesktop.exe"));
    c.current_dir(&root)
        .env("WEBVIEW2_BROWSER_EXECUTABLE_FOLDER", &webview)
        .env("DSCOMPARE_STARTUP_TOKEN", &token);
    if args.iter().any(|s| s == "--gui-smoke") {
        c.env("DSCOMPARE_PORTABLE_SMOKE", "1");
    }
    let profile = std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .ok_or("Brak folderu użytkownika")?
        .join("DSCompare/portable-webview")
        .join(&dscompare_portable::digest(webview.to_string_lossy().as_bytes())[..20]);
    std::fs::create_dir_all(&profile).map_err(|e| e.to_string())?;
    c.env("WEBVIEW2_USER_DATA_FOLDER", &profile);
    let log_path = profile.join("startup.log");
    let log = std::fs::File::create(&log_path).map_err(|e| e.to_string())?;
    c.stdout(Stdio::from(log.try_clone().map_err(|e| e.to_string())?))
        .stderr(Stdio::from(log));
    let mut child = c
        .spawn()
        .map_err(|e| format!("Nie można uruchomić DS Compare: {e}"))?;
    let start = std::time::Instant::now();
    loop {
        if ready.is_file() {
            let _ = std::fs::remove_file(&ready);
            return Ok(());
        }
        if state.cancel.load(Ordering::Relaxed) {
            let _ = child.kill();
            let _ = child.wait();
            return Err("Uruchamianie anulowane".into());
        }
        if let Some(status) = child.try_wait().map_err(|e| e.to_string())? {
            return Err(format!("Interfejs zakończył uruchamianie przed osiągnięciem gotowości ({status}). Dziennik: {}",log_path.display()));
        }
        if start.elapsed() > Duration::from_secs(90) {
            let _ = child.kill();
            let _ = child.wait();
            return Err("Przekroczono czas uruchamiania interfejsu. Spróbuj ponownie.".into());
        }
        thread::sleep(Duration::from_millis(50));
    }
}
fn main() {
    let verify_only = std::env::args().any(|s| s == "--verify-only");
    let result = if verify_only {
        work(splash::Shared::new())
    } else {
        splash::run(work)
    };
    if let Err(e) = result {
        eprintln!("{e}");
        std::process::exit(1)
    }
}
