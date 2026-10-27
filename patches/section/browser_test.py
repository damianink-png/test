from pathlib import Path
import sys
from playwright.sync_api import sync_playwright
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.compare import Record
from dsac29.preview3d import create_preview
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
part=describe(BRepPrimAPI_MakeBox(10,20,30).Shape(),'Box','root/Box')
page_path=out/'section.html';create_preview(page_path,[Record(None,0,'ADDED','')],[],[part])
with sync_playwright() as p:
 browser=p.chromium.launch(channel='msedge' if sys.platform=='win32' else None,headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1400,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(page_path.as_uri());page.wait_for_timeout(400)
 assert page.locator('#err').inner_text()==''
 page.get_by_text('Przekrój podglądu',exact=True).click()
 assert page.locator('#sectionPosition').is_disabled()
 original=page.screenshot(clip={'x':520,'y':200,'width':600,'height':500})
 for axis in ('0','1','2'):
  page.select_option('#sectionAxis',axis);page.wait_for_timeout(150)
  assert not page.locator('#sectionPosition').is_disabled()
  cut=page.screenshot(clip={'x':520,'y':200,'width':600,'height':500});assert cut!=original
  page.locator('#sectionFlip').check(force=True);page.wait_for_timeout(150)
  flipped=page.screenshot(clip={'x':520,'y':200,'width':600,'height':500});assert flipped!=cut
  page.locator('#sectionFlip').uncheck(force=True)
 page.select_option('#sectionAxis','off');page.wait_for_timeout(150)
 assert page.screenshot(clip={'x':520,'y':200,'width':600,'height':500})==original
 assert page.locator('#treeCount').inner_text()=='1/1'
 assert not errors,errors
 page.screenshot(path=str(out/'section-browser.png'))
 browser.close()
print('Chromium WebGL: X/Y/Z clipping, flip, restoration and scene count PASS')
