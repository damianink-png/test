"""Render the approved HTML artwork to an embedded, browser-free Win32 bitmap.

The browser runs only on GitHub Actions during the build. The delivered
launcher never creates a WebView for the splash, never accesses the network,
and continues to show real native progress while unpacking OneEXE.
"""
import hashlib
from io import BytesIO
from pathlib import Path
import sys
from PIL import Image
from playwright.sync_api import sync_playwright

# Git object SHA of the exact committed library prototype. We pin the
# committed bytes (including normalized line endings), not a prior copy.
APPROVED_GIT_BLOB = "8672bfea98580f6fc4fcd429f9900cdfa6684a78"
source = Path(sys.argv[1])
output = Path(sys.argv[2])
raw = source.read_bytes()
# Windows Git checkout may use CRLF; Git blob digest is over canonical LF.
# Preserve the exact original bytes semantically rather than weakening the
# provenance check for the approved HTML/image.
raw = raw.replace(bytes([13, 10]), bytes([10]))
blob_header=b"blob "+str(len(raw)).encode("ascii")+bytes([0])
actual=hashlib.sha1(blob_header+raw).hexdigest()
if actual != APPROVED_GIT_BLOB:
    raise SystemExit(f"Approved splash HTML differs from pinned Git blob: got={actual}, bytes={len(raw)}")
if b'data:image/webp;base64,' not in raw:
    raise SystemExit("Missing original CAD hero artwork")
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    # Preserve browser-rendered vector typography and CSS at native 3x
    # pixel density. The old 1120x620 raster was visibly blurry on
    # 125-200% Windows DPI monitors (and shrank further in a 900 px window).
    resolution_scale = 3
    page = browser.new_page(viewport={"width": 1200, "height": 770},
                            device_scale_factor=resolution_scale,
                            reduced_motion="reduce")
    # set_content keeps this self-contained data-URL design fully offline.
    page.set_content(raw.decode("utf-8"), wait_until="load")
    page.locator(".hero").evaluate("(image) => image.decode()")
    page.add_style_tag(content="""
      .light-sweep, .scan-halo { display:none!important }
      .loading-text { visibility:hidden!important }
      .track::before { display:none!important }
    """)
    frame = page.locator("#splash").screenshot(animations="disabled")
    browser.close()
with Image.open(BytesIO(frame)) as image:
    expected_width = 1120 * resolution_scale
    expected_height = 620 * resolution_scale
    # Fractional CSS geometry can add one physical pixel in Chromium.
    if image.width != expected_width or image.height not in (expected_height, expected_height + 1):
        raise SystemExit(f"Unexpected 3x startup frame: {image.size}")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").crop((0, 0, expected_width, expected_height)).save(output, "BMP")
with Image.open(output) as bmp:
    if bmp.size != (3360, 1860) or bmp.mode != "RGB":
        raise SystemExit(f"Startup artwork must be 3360x1860, RGB; got {bmp.size} {bmp.mode}")
    if bmp.getbbox() is None:
        raise SystemExit("Rendered startup artwork is empty")
print(f"APPROVED_SPLASH_HIDPI_RENDER_PASS: {output} (3360x1860, 3x; {output.stat().st_size} bytes)", flush=True)
