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

APPROVED_SHA256 = "415767d3e70c2c62565dd49497f4ee23a6132aa562864f72c87dd4f6e74de40c"
source = Path(sys.argv[1])
output = Path(sys.argv[2])
raw = source.read_bytes()
if hashlib.sha256(raw).hexdigest() != APPROVED_SHA256:
    raise SystemExit("Approved splash HTML differs from the original Library artifact")
if b'data:image/webp;base64,' not in raw:
    raise SystemExit("Missing original CAD hero artwork")
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1200, "height": 770},
                            device_scale_factor=1, reduced_motion="reduce")
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
    if image.width != 1120 or image.height not in (620, 621):
        raise SystemExit(f"Unexpected splash dimensions: {image.size}")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").crop((0, 0, 1120, 620)).save(output, "BMP")
bmp = output.read_bytes()
if bmp[:2] != b"BM" or len(bmp) < 1120 * 620 * 3:
    raise SystemExit("Invalid rasterized startup artwork")
print(f"APPROVED_SPLASH_RENDER_PASS: {output} ({len(bmp)} bytes)", flush=True)
