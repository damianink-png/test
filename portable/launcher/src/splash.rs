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
    unsafe fn oval(dc: HDC, cx: i32, cy: i32, rx: i32, ry: i32, fill: u32, edge: u32, width: i32) {
        let brush = CreateSolidBrush(fill);
        let pen = CreatePen(PS_SOLID, width, edge);
        let old_brush = SelectObject(dc, brush);
        let old_pen = SelectObject(dc, pen);
        Ellipse(dc, cx-rx, cy-ry, cx+rx, cy+ry);
        SelectObject(dc, old_pen);
        SelectObject(dc, old_brush);
        DeleteObject(pen);
        DeleteObject(brush);
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
        let spread = (34.0 * (1.0-ease)) as i32;
        text(dc, "DS Compare", 28, 18, 500, 30, rgb(242, 249, 255), true);
        text(dc, "PORÓWNYWANIE REWIZJI CAD", 30, 59, 500, 12, rgb(148, 176, 199), false);
        rect(dc, 28, 90, 603, 164, rgb(11, 26, 42));
        panel(dc, 28, 90, 603, 164, rgb(32, 66, 87));
        // Diagonal technical grid under the model, much quieter than a checkerboard.
        for x in (40..632).step_by(34) {
            stroke(dc, x, 94, x, 250, rgb(18, 42, 61), 1);
        }
        for y in (104..250).step_by(34) {
            stroke(dc, 40, y, 619, y, rgb(18, 42, 61), 1);
        }
        text(dc, "CAD / STEP", 48, 113, 270, 12, rgb(94, 203, 229), true);
        text(dc, "ANALIZA 3D", 48, 143, 276, 23, rgb(226, 241, 252), true);
        text(dc, "Wykrywanie zmian geometrii", 50, 178, 296, 12,
             rgb(143, 174, 196), false);
        text(dc, "Bryły · położenie · rewizje", 50, 203, 278, 12,
             rgb(112, 147, 171), false);
        stroke(dc, 49, 230, 156, 230, rgb(38, 165, 203), 2);

        // Fully vector, illuminated mechanical CAD assembly instead of two cubes.
        // Metallic bed with raised thickness and a different world-revision layer.
        poly(dc, &[(358,218),(460,166),(626,202),(526,264)], rgb(103, 125, 145));
        poly(dc, &[(358,218),(526,264),(526,284),(358,241)], rgb(31, 53, 75));
        poly(dc, &[(526,264),(626,202),(626,226),(526,284)], rgb(24, 48, 70));
        poly(dc, &[(378,217),(458,177),(602,207),(523,253)], rgb(27, 51, 70));
        stroke(dc, 358, 218, 526, 264, rgb(192, 218, 233), 2);
        stroke(dc, 526, 264, 626, 202, rgb(161, 195, 217), 2);
        // Rear machine shaft and stepped motor housing.
        poly(dc, &[(516,131),(596,150),(598,206),(516,186)], rgb(62, 83, 102));
        poly(dc, &[(598,150),(615,159),(616,214),(598,206)], rgb(23, 44, 65));
        poly(dc, &[(516,131),(537,119),(614,137),(596,150)], rgb(139, 158, 175));
        poly(dc, &[(543,117),(553,104),(591,112),(578,123)], rgb(167, 183, 194));
        stroke(dc, 516, 132, 596, 150, rgb(214, 233, 242), 2);
        stroke(dc, 516, 186, 598, 206, rgb(115, 166, 188), 2);
        // Angular ribs and supporting bearing yoke.
        poly(dc, &[(409,215),(439,133),(462,140),(494,225),(472,227),(450,173),(433,225)],
             rgb(99, 119, 136));
        poly(dc, &[(440,133),(456,118),(478,129),(462,140)], rgb(194, 212, 222));
        poly(dc, &[(483,221),(526,145),(543,152),(528,233)], rgb(66, 89, 107));
        poly(dc, &[(526,145),(541,138),(558,145),(543,152)], rgb(193, 210, 219));
        stroke(dc, 410, 215, 439, 133, rgb(201, 220, 231), 2);
        stroke(dc, 483, 221, 526, 145, rgb(191, 212, 225), 2);
        // Rectangular front bearing, rotated plates and concentric precision rings.
        poly(dc, &[(432,148),(467,132),(495,147),(459,168)], rgb(183, 199, 208));
        poly(dc, &[(459,168),(495,147),(495,211),(459,229)], rgb(49, 72, 91));
        poly(dc, &[(421,146),(459,168),(459,228),(421,206)], rgb(123, 140, 154));
        oval(dc, 431, 180, 32, 41, rgb(78, 101, 119), rgb(219, 231, 237), 4);
        oval(dc, 428, 180, 27, 34, rgb(142, 160, 175), rgb(217, 236, 248), 2);
        oval(dc, 428, 180, 19, 25, rgb(16, 30, 46), rgb(81, 118, 143), 4);
        oval(dc, 428, 180, 12, 16, rgb(7, 18, 30), rgb(20, 38, 58), 3);
        // Distinctive revision highlight; blue machined support and orange addition.
        poly(dc, &[(491,234),(527,174),(544,187),(559,244)], rgb(24, 118, 189));
        poly(dc, &[(527,174),(539,169),(556,181),(544,187)], rgb(91, 197, 248));
        poly(dc, &[(544,187),(556,181),(571,238),(559,244)], rgb(16, 66, 115));
        stroke(dc, 492, 234, 527, 174, rgb(116, 214, 250), 2);
        poly(dc, &[(565,228),(590,217),(613,223),(587,237)], rgb(255, 177, 67));
        poly(dc, &[(565,228),(587,237),(587,251),(565,243)], rgb(151, 75, 25));
        poly(dc, &[(587,237),(613,223),(613,236),(587,251)], rgb(175, 93, 29));
        stroke(dc, 565, 228, 587, 237, rgb(255, 227, 145), 2);
        poly(dc, &[(555,139),(581,129),(605,137),(579,149)], rgb(249, 163, 48));
        stroke(dc, 555, 139, 579, 149, rgb(255, 228, 147), 2);
        // Fasteners and optical edge detail.
        for (x,y) in [(395,226),(522,250),(594,213),(483,222),(544,134)] {
            oval(dc,x,y,6,3,rgb(185, 207, 221),rgb(27, 53, 72),1);
            stroke(dc,x-3,y,x+3,y,rgb(34, 56, 72),1);
        }
        // Independent CAD-revision overlay and moving section plane.
        let scan = if animated { 386 + ((cycle*225.0).round() as i32) } else { 511 };
        for o in [-9,-4,4,9] {
            stroke(dc,scan+o,110,scan+o,248,rgb(18, 71, 85),1);
        }
        stroke(dc,scan,103,scan,252,rgb(91, 229, 242),2);
        for (a,b) in [((356,220),(529,266)),((529,266),(627,206)),
                      ((518,132),(596,151)),((438,135),(460,171)),
                      ((492,234),(528,174)),((567,229),(612,224))] {
            // Cyan ghost of the verified revision, not a fake geometry verdict.
            if scan >= a.0 && scan >= b.0 {
                stroke(dc,a.0+spread/4,a.1,b.0+spread/4,b.1,rgb(35, 206, 226),1);
            }
        }
        let pulse = if animated { 0.5+0.5*(elapsed*4.2).sin() } else { 0.65 };
        let gl = (60.0+pulse*110.0) as u32;
        stroke(dc, 520, 249, 612, 244, rgb(23,gl,171),1);
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
