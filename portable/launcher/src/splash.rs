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

    const ARTWORK_BMP: &[u8] =
        include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"), "/assets/splash-frame.bmp"));
    unsafe fn draw_approved_background(dc: HDC) {
        // A validated 1120x620, bottom-up, 24-bit uncompressed BMP.
        // Source dimensions and provenance are checked by render_splash.py.
        let offset = u32::from_le_bytes(ARTWORK_BMP[10..14].try_into().unwrap()) as usize;
        let mut bmi: BITMAPINFO = std::mem::zeroed();
        bmi.bmiHeader.biSize = std::mem::size_of::<BITMAPINFOHEADER>() as u32;
        bmi.bmiHeader.biWidth = 1120;
        bmi.bmiHeader.biHeight = 620;
        bmi.bmiHeader.biPlanes = 1;
        bmi.bmiHeader.biBitCount = 24;
        bmi.bmiHeader.biCompression = BI_RGB;
        StretchDIBits(dc, 0, 0, 1120, 620, 0, 0, 1120, 620,
            ARTWORK_BMP[offset..].as_ptr() as *const _,
            &bmi, DIB_RGB_COLORS, SRCCOPY);
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
        SetWindowExtEx(dc, 1120, 620, null_mut());
        SetViewportExtEx(dc, w, h, null_mut());

        // The exact approved 10 November 2026 HTML prototype is rendered
        // offline during the Windows build. This bitmap is embedded in BOTH
        // portable launchers and requires no browser, network or external file
        // while the single EXE unpacks its payload.
        draw_approved_background(dc);
        let elapsed = START.get().unwrap().elapsed().as_secs_f64();
        let mut motion = 1i32;
        SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0,
            &mut motion as *mut _ as *mut _, 0);
        let animated = motion != 0;
        // Native animated scan: a material-to-wireframe visual metaphor,
        // not a geometry verification claim or a fabricated progress value.
        let phase = if animated {
            0.5 - 0.5 * (elapsed * std::f64::consts::TAU / 6.2).cos()
        } else { 0.6 };
        let scan = 455 + (phase * 604.0) as i32;
        for (offset, green) in [(-20, 63), (-11, 84), (-5, 125), (4, 70), (12, 45)] {
            stroke(dc, scan+offset, 32, scan+offset, 553, rgb(12,green,110), 1);
        }
        stroke(dc, scan, 23, scan, 556, rgb(119, 232, 244), 2);
        let state = STATE.get().unwrap();
        let progress = state.status.lock().unwrap().clone();
        text(dc, &progress.text, 68, 536, 485, 16, rgb(224, 242, 252), true);
        // Actual known progress is determinate; otherwise animate a
        // scanner without inventing any completion percentage.
        rect(dc, 67, 571, 453, 3, rgb(48, 75, 91));
        if let Some(percent) = progress.percent {
            rect(dc, 67, 571, 453 * percent.min(100) as i32 / 100,
                 3, rgb(58, 216, 231));
        } else {
            let position = if animated {
                ((elapsed / 2.6).fract() * 553.0) as i32 - 100
            } else { 170 };
            let left = (67 + position).max(67);
            let right = (67 + position + 100).min(520);
            if right > left {
                rect(dc, left, 571, right-left, 3, rgb(90, 231, 244));
            }
        }
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
            // Preserve the approved 1120:620 aspect ratio while fitting small
            // displays and enlarged Windows DPI without off-screen cropping.
            let avail_w = GetSystemMetrics(SM_CXSCREEN).max(1) as f64;
            let avail_h = GetSystemMetrics(SM_CYSCREEN).max(1) as f64;
            let scale = factor.min(avail_w * 0.90 / 900.0)
                              .min(avail_h * 0.86 / (900.0 * 620.0 / 1120.0));
            let width = (900.0 * scale).round() as i32;
            let height = (width as f64 * 620.0 / 1120.0).round() as i32;
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
