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
    // Lightweight vector drawing: no webview, images, or installed fonts.
    // Win32/GDI renders the splash immediately even on a cold portable start.
    unsafe fn stroke(dc: HDC, x1: i32, y1: i32, x2: i32, y2: i32, color: u32, width: i32) {
        let pen = CreatePen(PS_SOLID, width, color);
        let old = SelectObject(dc, pen);
        MoveToEx(dc, x1, y1, null_mut());
        LineTo(dc, x2, y2);
        SelectObject(dc, old);
        DeleteObject(pen);
    }
    unsafe fn panel(dc: HDC, x: i32, y: i32, w: i32, h: i32, border: u32) {
        stroke(dc, x, y, x+w, y, border, 1);
        stroke(dc, x+w, y, x+w, y+h, border, 1);
        stroke(dc, x+w, y+h, x, y+h, border, 1);
        stroke(dc, x, y+h, x, y, border, 1);
    }
    unsafe fn outline_cube(dc: HDC, x: i32, y: i32, color: u32) {
        // 12 visible isometric edges / blueprint-like highlight.
        let p=(x,y-28);
        let left=(x-34,y-12);
        let right=(x+34,y-12);
        let core=(x,y+5);
        let bottom=(x,y+42);
        let low_l=(x-34,y+24);
        let low_r=(x+34,y+24);
        for (a,b) in [(p,left),(p,right),(left,core),(right,core),
                      (left,low_l),(right,low_r),(core,bottom),
                      (low_l,bottom),(low_r,bottom)] {
            stroke(dc,a.0,a.1,b.0,b.1,color,1);
        }
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
        // Quiet dark geometry-workspace palette: readable at 100-200% DPI.
        rect(dc, 0, 0, 660, 360, rgb(10, 16, 26));
        rect(dc, 0, 0, 660, 3, rgb(25, 151, 142));
        let elapsed = START.get().unwrap().elapsed().as_secs_f64();
        let mut motion = 1i32;
        SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0,
            &mut motion as *mut _ as *mut _, 0);
        let animated = motion != 0;
        let elapsed = if animated { elapsed } else { 3.0 };
        let cycle = (elapsed / 2.4).fract();
        let approach = (elapsed / 1.0).min(1.0);
        let ease = 1.0 - (1.0-approach).powi(3);
        let spread = (62.0 * (1.0-ease)) as i32;

        text(dc, "DS COMPARE", 30, 19, 490, 29, rgb(237, 245, 253), true);
        text(dc, "GEOMETRY  /  REVISION ENGINE", 31, 61, 490, 11,
             rgb(123, 153, 175), false);
        rect(dc, 29, 98, 602, 155, rgb(15, 25, 39));
        panel(dc, 29, 98, 602, 155, rgb(38, 56, 75));

        // Fine drafting grid, fixed and cheap to draw.
        for x in (51..625).step_by(32) {
            rect(dc, x, 109, 1, 132, rgb(20, 34, 49));
        }
        for y in (115..246).step_by(32) {
            rect(dc, 40, y, 579, 1, rgb(20, 34, 49));
        }
        text(dc, "REWIZJA A", 50, 112, 170, 11, rgb(175, 161, 132), true);
        text(dc, "REWIZJA B", 475, 112, 160, 11, rgb(130, 200, 191), true);
        let ax = 264-spread;
        let bx = 396+spread;
        let y = 171;
        // Ghost positions and a connecting comparison axis.
        stroke(dc, 303, 170, 357, 170, rgb(55, 76, 90), 1);
        stroke(dc, 309, 164, 303, 170, rgb(69, 110, 115), 1);
        stroke(dc, 309, 176, 303, 170, rgb(69, 110, 115), 1);
        stroke(dc, 351, 164, 357, 170, rgb(69, 110, 115), 1);
        stroke(dc, 351, 176, 357, 170, rgb(69, 110, 115), 1);
        cube(dc, ax, y, false, "A");
        cube(dc, bx, y, true, "B");
        outline_cube(dc, ax, y, rgb(238, 195, 121));
        outline_cube(dc, bx, y, rgb(96, 222, 196));

        // Moving CAD section plane: scans both bodies and reconnects.
        let scanner = if animated {
            221 + (cycle * 219.0).round() as i32
        } else { 330 };
        stroke(dc, scanner-5, 136, scanner-5, 215,
               rgb(29, 73, 81), 1);
        stroke(dc, scanner, 132, scanner, 219,
               rgb(91, 211, 193), 2);
        stroke(dc, scanner+5, 136, scanner+5, 215,
               rgb(29, 73, 81), 1);
        let pulse = if animated {
            0.5+0.5*(elapsed*4.2).sin()
        } else { 0.65 };
        let glow = (26.0 + pulse*45.0) as u32;
        rect(dc, 322, 209, 16, 3, rgb(glow, 141, 142));
        text(dc, "PORÓWNYWANIE GEOMETRII", 231, 230, 240, 10,
             rgb(127, 168, 183), false);

        let state = STATE.get().unwrap();
        let p = state.status.lock().unwrap().clone();
        text(dc, &p.text, 30, 269, 535, 15, rgb(203, 217, 231), true);
        text(dc, "Przygotowywanie bezpiecznego środowiska CAD", 31, 294, 530, 11,
             rgb(122, 148, 171), false);

        // Monotonic percentage when known, otherwise an honest scanner.
        rect(dc, 30, 319, 600, 5, rgb(35, 51, 69));
        if let Some(n) = p.percent {
            let n = n.min(100);
            rect(dc, 30, 319, (600*n/100) as i32, 5, rgb(59, 200, 173));
            text(dc, &format!("{n}%"), 579, 271, 55, 13,
                 rgb(113, 223, 194), true);
        } else {
            let position = if animated { (cycle*425.0).round() as i32 } else { 212 };
            rect(dc, 30+position, 319, 174, 5, rgb(59, 200, 173));
        }
        text(dc, "LOKALNIE  ·  TWOJE DANE POZOSTAJĄ NA KOMPUTERZE", 30, 336,
             465, 10, rgb(102, 126, 149), false);
        text(dc, concat!("v", env!("CARGO_PKG_VERSION")), 555, 335, 90, 11,
             rgb(102, 126, 149), false);
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
                WS_POPUP | WS_VISIBLE,
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
