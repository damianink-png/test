use dscompare_portable::{Progress, Result};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
pub struct Shared {
    pub status: Mutex<Progress>,
    pub done: AtomicBool,
    pub cancel: AtomicBool,
    pub error: Mutex<Option<String>>,
}
impl Shared {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            status: Mutex::new(Progress {
                text: "Uruchamianie DS Compare…".into(),
                percent: None,
            }),
            done: AtomicBool::new(false),
            cancel: AtomicBool::new(false),
            error: Mutex::new(None),
        })
    }
}
#[cfg(not(windows))]
pub fn run(work: impl FnOnce(Arc<Shared>) -> Result<()> + Send + 'static) -> Result<()> {
    work(Shared::new())
}
#[cfg(windows)]
mod win {
    use super::*;
    use std::{
        ptr::{null, null_mut},
        sync::OnceLock,
        time::Instant,
    };
    use windows_sys::Win32::{
        Foundation::*,
        Graphics::Gdi::*,
        System::LibraryLoader::GetModuleHandleW,
        UI::{HiDpi::*, WindowsAndMessaging::*},
    };
    static STATE: OnceLock<Arc<Shared>> = OnceLock::new();
    static START: OnceLock<Instant> = OnceLock::new();
    fn wide(s: &str) -> Vec<u16> {
        s.encode_utf16().chain(Some(0)).collect()
    }
    fn rgb(r: u32, g: u32, b: u32) -> u32 {
        r | (g << 8) | (b << 16)
    }
    unsafe fn rect(dc: HDC, x: i32, y: i32, w: i32, h: i32, color: u32) {
        let brush = CreateSolidBrush(color);
        let r = RECT {
            left: x,
            top: y,
            right: x + w,
            bottom: y + h,
        };
        FillRect(dc, &r, brush);
        DeleteObject(brush);
    }
    unsafe fn text(
        dc: HDC,
        s: &str,
        x: i32,
        y: i32,
        width: i32,
        size: i32,
        color: u32,
        bold: bool,
    ) {
        let f = CreateFontW(
            -size,
            0,
            0,
            0,
            if bold { 600 } else { 400 },
            0,
            0,
            0,
            DEFAULT_CHARSET as u32,
            OUT_DEFAULT_PRECIS as u32,
            CLIP_DEFAULT_PRECIS as u32,
            CLEARTYPE_QUALITY as u32,
            DEFAULT_PITCH as u32,
            wide("Segoe UI").as_ptr(),
        );
        let old = SelectObject(dc, f);
        SetTextColor(dc, color);
        SetBkMode(dc, TRANSPARENT as i32);
        let mut r = RECT {
            left: x,
            top: y,
            right: x + width,
            bottom: y + size + 12,
        };
        let v = wide(s);
        DrawTextW(
            dc,
            v.as_ptr(),
            (v.len() - 1) as i32,
            &mut r,
            DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX,
        );
        SelectObject(dc, old);
        DeleteObject(f);
    }
    unsafe fn poly(dc: HDC, pts: &[(i32, i32)], color: u32) {
        let brush = CreateSolidBrush(color);
        let pen = CreatePen(PS_SOLID, 1, rgb(24, 37, 52));
        let ob = SelectObject(dc, brush);
        let op = SelectObject(dc, pen);
        let points: Vec<POINT> = pts.iter().map(|&(x, y)| POINT { x, y }).collect();
        Polygon(dc, points.as_ptr(), points.len() as i32);
        SelectObject(dc, op);
        SelectObject(dc, ob);
        DeleteObject(pen);
        DeleteObject(brush);
    }
    unsafe fn cube(dc: HDC, x: i32, y: i32, teal: bool, label: &str) {
        let (top, left, right) = if teal {
            (rgb(80, 204, 185), rgb(25, 117, 108), rgb(40, 166, 149))
        } else {
            (rgb(255, 199, 99), rgb(172, 108, 39), rgb(225, 155, 62))
        };
        poly(
            dc,
            &[(x, y - 28), (x + 34, y - 12), (x, y + 5), (x - 34, y - 12)],
            top,
        );
        poly(
            dc,
            &[(x - 34, y - 12), (x, y + 5), (x, y + 42), (x - 34, y + 24)],
            left,
        );
        poly(
            dc,
            &[(x, y + 5), (x + 34, y - 12), (x + 34, y + 24), (x, y + 42)],
            right,
        );
        text(dc, label, x + 6, y + 6, 22, 19, rgb(245, 250, 255), true);
    }
    unsafe fn paint(hwnd: HWND) {
        let mut ps: PAINTSTRUCT = std::mem::zeroed();
        let target = BeginPaint(hwnd, &mut ps);
        let mut bounds: RECT = std::mem::zeroed();
        GetClientRect(hwnd, &mut bounds);
        let w = bounds.right;
        let h = bounds.bottom;
        let dc = CreateCompatibleDC(target);
        let bmp = CreateCompatibleBitmap(target, w, h);
        let old = SelectObject(dc, bmp);
        SetMapMode(dc, MM_ANISOTROPIC);
        SetWindowExtEx(dc, 660, 360, null_mut());
        SetViewportExtEx(dc, w, h, null_mut());
        rect(dc, 0, 0, 660, 360, rgb(12, 18, 28));
        rect(dc, 0, 0, 660, 2, rgb(68, 174, 154));
        let t = START.get().unwrap().elapsed().as_secs_f64();
        let mut motion = 1i32;
        SystemParametersInfoW(
            SPI_GETCLIENTAREAANIMATION,
            0,
            &mut motion as *mut _ as *mut _,
            0,
        );
        let t = if motion != 0 { t } else { 2.0 };
        let ease = (t / 1.1).min(1.0);
        let offset = (65.0 * (1.0 - ease).powi(3)) as i32;
        text(dc, "DS Compare", 28, 22, 520, 28, rgb(232, 240, 250), true);
        text(
            dc,
            "PORÓWNANIE REWIZJI CAD",
            30,
            60,
            520,
            11,
            rgb(147, 167, 190),
            false,
        );
        cube(dc, 293 - offset, 135, false, "A");
        cube(dc, 367 + offset, 135, true, "B");
        let state = STATE.get().unwrap();
        let p = state.status.lock().unwrap().clone();
        text(
            dc,
            "Twoje modele. Każda zmiana pod kontrolą.",
            30,
            219,
            600,
            19,
            rgb(220, 231, 244),
            true,
        );
        text(dc, &p.text, 30, 263, 548, 14, rgb(157, 178, 200), false);
        rect(dc, 30, 307, 600, 4, rgb(36, 52, 71));
        if let Some(n) = p.percent {
            rect(
                dc,
                30,
                307,
                (600 * n.min(100) / 100) as i32,
                4,
                rgb(78, 188, 165),
            );
            text(
                dc,
                &format!("{n}%"),
                580,
                263,
                60,
                14,
                rgb(100, 212, 185),
                true,
            );
        } else {
            let position = if motion != 0 {
                ((t * 0.55).fract() * 420.0) as i32
            } else {
                210
            };
            rect(dc, 30 + position, 307, 180, 4, rgb(78, 188, 165));
        }
        text(
            dc,
            "LOKALNE PORÓWNYWANIE MODELI STEP",
            30,
            331,
            400,
            11,
            rgb(107, 129, 153),
            false,
        );
        text(
            dc,
            "PORTABLE 0.5.2",
            526,
            331,
            120,
            11,
            rgb(107, 129, 153),
            false,
        );
        SetMapMode(dc, MM_TEXT);
        BitBlt(target, 0, 0, w, h, dc, 0, 0, SRCCOPY);
        SelectObject(dc, old);
        DeleteObject(bmp);
        DeleteDC(dc);
        EndPaint(hwnd, &ps);
    }
    unsafe extern "system" fn procedure(hwnd: HWND, msg: u32, w: WPARAM, l: LPARAM) -> LRESULT {
        match msg {
            WM_PAINT => {
                paint(hwnd);
                0
            }
            WM_ERASEBKGND => 1,
            WM_TIMER => {
                if STATE.get().unwrap().done.load(Ordering::Acquire) {
                    DestroyWindow(hwnd);
                } else {
                    InvalidateRect(hwnd, null(), 0);
                }
                0
            }
            WM_CLOSE => {
                STATE.get().unwrap().cancel.store(true, Ordering::Relaxed);
                DestroyWindow(hwnd);
                0
            }
            WM_DESTROY => {
                PostQuitMessage(0);
                0
            }
            _ => DefWindowProcW(hwnd, msg, w, l),
        }
    }
    pub fn run(work: impl FnOnce(Arc<Shared>) -> Result<()> + Send + 'static) -> Result<()> {
        unsafe {
            let state = Shared::new();
            STATE
                .set(state.clone())
                .map_err(|_| "Ekran startowy już działa")?;
            START.set(Instant::now()).ok();
            SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_SYSTEM_AWARE);
            let instance = GetModuleHandleW(null());
            let class = wide("DSComparePortableSplash");
            let wc = WNDCLASSW {
                lpfnWndProc: Some(procedure),
                hInstance: instance,
                lpszClassName: class.as_ptr(),
                hCursor: LoadCursorW(null_mut(), IDC_ARROW),
                ..std::mem::zeroed()
            };
            RegisterClassW(&wc);
            let factor = GetDpiForSystem() as f64 / 96.;
            let (width, height) = ((660. * factor) as i32, (360. * factor) as i32);
            let x = (GetSystemMetrics(SM_CXSCREEN) - width) / 2;
            let y = (GetSystemMetrics(SM_CYSCREEN) - height) / 2;
            let hwnd = CreateWindowExW(
                WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
                class.as_ptr(),
                wide("DS Compare · uruchamianie").as_ptr(),
                WS_POPUP | WS_VISIBLE | WS_BORDER,
                x,
                y,
                width,
                height,
                null_mut(),
                null_mut(),
                instance,
                null(),
            );
            if hwnd.is_null() {
                return Err("Nie można otworzyć ekranu startowego".into());
            }
            SetTimer(hwnd, 1, 33, None);
            UpdateWindow(hwnd);
            let shared = state.clone();
            let worker = std::thread::spawn(move || {
                let result =
                    std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| work(shared.clone())))
                        .unwrap_or_else(|_| Err("Nieoczekiwany błąd uruchamiania".into()));
                if let Err(e) = result {
                    *shared.error.lock().unwrap() = Some(e);
                }
                shared.done.store(true, Ordering::Release);
            });
            let mut msg: MSG = std::mem::zeroed();
            while GetMessageW(&mut msg, null_mut(), 0, 0) > 0 {
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
            let _ = worker.join();
            let failure = state.error.lock().unwrap().clone();
            if state.cancel.load(Ordering::Relaxed) {
                return Err("Uruchamianie anulowane".into());
            }
            if let Some(e) = failure {
                MessageBoxW(
                    null_mut(),
                    wide(&e).as_ptr(),
                    wide("DS Compare · problem z uruchomieniem").as_ptr(),
                    MB_OK | MB_ICONERROR,
                );
                return Err(e);
            }
            Ok(())
        }
    }
}
#[cfg(windows)]
pub use win::run;
