"""Real WebGL + Svelte browser contracts. Native IPC is explicitly mocked here."""
import json,sys,os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'diagnostics/review06';demo=root/'demo';checks=[]
summary=json.loads((demo/'PODSUMOWANIE.json').read_text())
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1800,'height':1100},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto((demo/'PODGLAD_KOLOROW_3D.html').resolve().as_uri());page.wait_for_timeout(600)
 assert not page.locator('#err').is_visible(),page.locator('#err').text_content()
 # Known 90-degree B -> A registration must be inverted, including centered coordinates.
 matrix=page.evaluate("Array.from(originalPlacement({applied:true,rotation_B_to_A:[[0,-1,0],[1,0,0],[0,0,1]],translation_B_to_A_mm:[10,20,30]},[100,200,300],[1,2,3],10))")
 # Registered world point (102,204,306) => original (184,-92,276).
 local=[.2,.4,.6]
 transformed=[sum(matrix[col*4+row]*local[col] for col in range(3))+matrix[12+row] for row in range(3)]
 expected=[(184-101)*.2,(-92-202)*.2,(276-303)*.2]
 assert all(abs(a-b)<1e-5 for a,b in zip(transformed,expected)),(transformed,expected)
 initial=page.locator('#cad').screenshot()
 page.select_option('#layout','split');page.wait_for_timeout(100)
 assert page.locator('#cad').screenshot()!=initial
 page.check('#original');page.wait_for_timeout(150)
 original=page.locator('#cad').screenshot();assert original!=initial
 page.select_option('#sectionAxis','0');page.fill('#sectionPosition','35');page.dispatch_event('#sectionPosition','input');page.wait_for_timeout(100)
 assert page.locator('#cad').screenshot()!=original
 page.select_option('#sectionAxis','off');page.uncheck('#original');page.select_option('#layout','overlay')
 page.fill('#treeSearch','Uchwyt');assert page.locator('.tree-leaf:visible').count()==2
 page.locator('.tree-leaf:visible').last.click();assert 'Uchwyt' in page.locator('#selection').text_content()
 page.click('#pair');assert page.locator('#treeCount').text_content().startswith('2/')
 page.click('#focus');page.click('#all');page.fill('#treeSearch','');page.click('#reset');
 page.screenshot(path=str(root/'preview06.png'))
 checks.append('Real WebGL: shared-camera split A/B, original B coordinates, section clipping, search, selection, pair, focus/reset')
 page.route('**/artifacts/*',lambda route:route.fulfill(path=str(demo/route.request.url.rsplit('/',1)[-1].split('#')[0]),content_type='text/html'))
 page.add_init_script('''window.isTauri=true;window.__fixture='''+json.dumps(summary)+''';window.__calls=[];window.__running=false;
 window.__TAURI_INTERNALS__={convertFileSrc:p=>'http://127.0.0.1:8766/artifacts/'+p.split(/[\\\\/]/).pop(),invoke:async(cmd,args)=>{window.__calls.push({cmd,args});
 if(cmd==='load_settings')return null;if(cmd==='environment')return {engine_ready:true};if(cmd==='plugin:dialog|open')return '/test/results';
 if(cmd==='load_result')return window.__fixture;if(cmd==='artifact_path')return '/test/results/'+args.name;
 if(cmd==='poll_job')return window.__running?{id:'test',folder:'/test/results',running:true,cancelled:false,events:['Common A[5] ↔ B[5]'],progress:{phase:'Weryfikacja materiału',timestamp_ms:Date.now()-70000,checks:7},question:null,result:null,summary:null,error:null}:null;
 if(cmd==='cancel_job'){window.__running=false;return null;}return null;}};''')
 page.goto('http://127.0.0.1:8766');page.get_by_role('button',name='Otwórz wyniki',exact=True).click()
 page.wait_for_selector('.review-workspace');page.wait_for_timeout(600)
 assert page.locator('.analysis-badge').text_content().strip()=='Analiza częściowa'
 assert page.locator('.part-list>button').count()==7
 frame=page.frame_locator('iframe');frame.locator('#treeCount').wait_for(state='attached')
 page.get_by_role('button',name='Raport HTML / PDF',exact=True).click()
 frame.locator('#table').wait_for()
 frame.locator('#table .preview-link').nth(2).click();page.wait_for_timeout(500)
 assert 'Podgląd 3D' in page.locator('.viewer-bar').first.text_content()
 assert page.locator('.part-details').get_by_text('POZYCJA 3').count()==1
 page.get_by_role('button',name='Diagnostyka części (1)',exact=True).click();assert page.locator('.part-list>button').count()==1
 page.locator('.part-list>button').click();assert page.locator('.part-details').get_by_text('POZYCJA 7').count()==1
 page.get_by_role('button',name='Pokaż część w 3D',exact=True).click();page.wait_for_timeout(150)
 assert 'Do kontroli' in frame.locator('#selection').text_content()
 # Geometry/tree -> parent must clear incompatible filter and keep original index.
 frame.locator('#legend').locator('..').locator('summary').click()
 frame.locator('#all').click();frame.locator('#reset').click();page.wait_for_timeout(100)
 import io
 from PIL import Image
 canvas=frame.locator('#cad');im=Image.open(io.BytesIO(canvas.screenshot())).convert('RGB')
 points=[]
 for y in range(100,min(im.height,650)):
  for x in range(20,max(21,im.width-265)):
   red,green,blue=im.getpixel((x,y))
   if red<30 and green>45 and blue>green*1.15 and blue>90:points.append((x,y))
 assert len(points)>20,'No actual blue movement geometry rendered'
 x,y=points[len(points)//2];bounds=canvas.bounding_box();page.mouse.click(bounds['x']+x,bounds['y']+y);page.wait_for_timeout(150)
 assert page.locator('.part-details').get_by_text('POZYCJA 3').count()==1
 assert '25' in page.locator('.part-details').text_content()
 frame.locator('#legend').locator('..').locator('summary').click()
 frame.locator('#reset').click();page.evaluate('window.scrollTo(0,0)')
 page.screenshot(path=str(root/'workspace06-dark.png'),full_page=True)
 page.get_by_role('button',name='Zmień motyw').click();page.screenshot(path=str(root/'workspace06-light.png'),full_page=True)
 page.set_viewport_size({'width':1000,'height':680});page.screenshot(path=str(root/'workspace06-compact.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Horizontal overflow'
 page.get_by_role('button',name='O programie',exact=True).click();page.wait_for_timeout(50);assert page.get_by_role('dialog').count()==1;page.keyboard.press('Escape')
 page.evaluate('window.__running=true');page.wait_for_timeout(1000)
 assert 'Ostatni komunikat:' in page.locator('.progress-facts').text_content()
 assert page.locator('progress').count()==0
 assert '7' in page.locator('.progress-facts').text_content()
 page.get_by_role('button',name='Anuluj',exact=True).click()
 checks.append('Svelte + mocked IPC: partial scope, diagnostics filter, stable pair IDs after filtering, bidirectional selection, movement details, themes, 1000x680, About, timestamps/counters/cancel')
 assert not errors,errors
 (root/'browser-checks.json').write_text(json.dumps({'status':'PASS','checks':checks,'javascript_errors':errors,'native_ipc':'mocked; tested separately via Rust core'},ensure_ascii=False,indent=2))
 browser.close()
print('REVIEW_BROWSER_PASS',checks)
