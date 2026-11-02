"""Browser interaction tests with actual Tauri JS listeners and explicit native IPC simulation."""
import json,os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
demo=Path(__file__).resolve().parent/'fixture';summary=json.loads((demo/'PODSUMOWANIE.json').read_text(encoding='utf8'))
summary['bom_csv']=False
script=r'''window.isTauri=true;window.__fixture=FIXTURE;window.__calls=[];window.__job=null;window.__callbacks={};window.__listeners={};let seq=1;
window.__TAURI_INTERNALS__={metadata:{currentWindow:{label:'main'},currentWebview:{label:'main'}},transformCallback:f=>{const id=seq++;window.__callbacks[id]=f;return id;},unregisterCallback:id=>delete window.__callbacks[id],convertFileSrc:p=>'http://127.0.0.1:8768/artifacts/'+p.split(/[\\/]/).pop(),invoke:async(cmd,args)=>{window.__calls.push({cmd,args});if(cmd==='load_settings')return null;if(cmd==='environment')return {engine_ready:true};if(cmd==='plugin:event|listen'){window.__listeners[args.event]=args.handler;return seq++;}if(cmd==='plugin:dialog|open')return '/test/results';if(cmd==='load_result')return window.__fixture;if(cmd==='artifact_path')return '/test/results/'+args.name;if(cmd==='start_job'){window.__job={id:'job'+seq++,folder:'/test/results',running:true,cancelled:false,events:['Common OCCT'],question:null,result:null,summary:null,error:null};return window.__job;}if(cmd==='poll_job')return window.__job;if(cmd==='cancel_job'){window.__job={...window.__job,running:false,cancelled:true};return null;}if(cmd==='answer_question'){window.__job.question=null;return null;}return null;}};
window.__drop=(paths,x,y)=>{const id=window.__listeners['tauri://drag-drop'];window.__callbacks[id]({payload:{paths,position:{x:x*devicePixelRatio,y:y*devicePixelRatio}}});};
'''.replace('FIXTURE',json.dumps(summary))
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1280,'height':720},device_scale_factor=1.25);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def route_artifact(route):
  name=route.request.url.rsplit('/',1)[-1]
  if name in ('BOM_A.html','BOM_B.html'):route.fulfill(body='<html><body><h1>'+name+'</h1><table><tr><td>Osłona</td></tr></table></body></html>',content_type='text/html')
  else:route.fulfill(path=str(demo/name),content_type='text/html')
 page.route('**/artifacts/*',route_artifact)
 page.add_init_script(script);page.goto('http://127.0.0.1:8768');page.wait_for_function("window.__listeners['tauri://drag-drop']!==undefined")
 assert page.get_by_label('Tolerancja geometryczna',exact=True).count()==1
 assert not page.get_by_label('Tolerancja geometryczna',exact=True).is_visible()
 page.get_by_role('button',name='Ustawienia',exact=True).click()
 expected=['Bez zmian','Bez zmian w detalu','Dodany materiał','Usunięty materiał',
           'Nowe B','Usunięte A','Przesunięte — stare A','Przesunięte — nowe B',
           'Do sprawdzenia — A','Do sprawdzenia — B']
 assert page.locator('.colors label').all_inner_texts()==expected
 assert page.locator('.colors input[type="color"]').count()==10
 page.screenshot(path=str(out/'palette-10.png'))
 page.get_by_role('button',name='Porównanie',exact=True).click()
 def drop(paths,role):
  box=page.locator('[data-drop-role="'+role+'"]').bounding_box();assert box
  page.evaluate('(v)=>window.__drop(v.paths,v.x,v.y)',{'paths':paths,'x':box['x']+box['width']/2,'y':box['y']+box['height']/2});page.wait_for_timeout(100)
 drop(['C:\\Modele\\Osłona A.STEP'],'a');drop(['D:\\Modele\\Osłona B.stp'],'b')
 assert 'Osłona A.STEP' in page.locator('[data-drop-role=a]').inner_text();assert 'Osłona B.stp' in page.locator('[data-drop-role=b]').inner_text()
 drop(['C:\\bad.exe'],'a');assert page.get_by_role('alert').is_visible();page.get_by_label('Zamknij komunikat').click()
 compare_button=page.get_by_role('button',name='Porównaj rewizje',exact=True).bounding_box()
 new_button=page.get_by_role('button',name='Nowe porównanie',exact=True).bounding_box()
 assert compare_button and new_button
 assert new_button['y'] >= compare_button['y'] + compare_button['height'] - 1, 'Nowe porównanie must be below Porównaj rewizje'
 assert abs(new_button['x']-compare_button['x']) < 20, 'Comparison actions must share a column'
 page.screenshot(path=str(out/'compare-1280.png'))
 page.get_by_role('button',name='Nowe porównanie',exact=True).click();assert 'Wybierz model A' in page.locator('[data-drop-role=a]').inner_text()
 page.get_by_role('button',name='Masa części',exact=True).click();drop(['C:\\A.step','C:\\A.step','D:\\B.step'],'mass');assert page.locator('.file-list li').count()==2
 page.get_by_role('button',name='Oblicz masę',exact=True).click()
 page.evaluate("window.__job={...window.__job,running:false,result:{ok:true,podsumowanie:{masa_calosci_kg:44.931862,liczba_plikow:2,liczba_bryl:553,gestosc_kg_m3:7850}}}")
 page.get_by_label('Wynik obliczenia masy').wait_for();assert '44,932' in page.get_by_label('Wynik obliczenia masy').inner_text()
 assert 'masa_calosci_kg' not in page.locator('main').inner_text();page.get_by_role('button',name='Otwórz zestawienie HTML').click()
 assert page.evaluate("window.__calls.some(c=>c.cmd==='open_artifact'&&c.args.name==='RAPORT_MASY.html')")
 page.screenshot(path=str(out/'mass-1280.png'))
 page.get_by_role('button',name='Otwórz wyniki',exact=True).click();assert page.get_by_role('heading',name='Wyniki porównania',exact=True).is_visible();assert page.get_by_label('Wyniki porównania').count()==1;assert page.locator('aside.rail nav button').count()==2;assert page.locator('iframe').count()==0
 page.get_by_role('button',name='BOM A · HTML',exact=True).click();assert page.evaluate("window.__calls.some(c=>c.cmd==='open_artifact'&&c.args.name==='BOM_A.html')")
 page.get_by_role('button',name='BOM B · HTML',exact=True).click();assert page.evaluate("window.__calls.some(c=>c.cmd==='open_artifact'&&c.args.name==='BOM_B.html')")
 assert page.locator('iframe').count()==0
 page.screenshot(path=str(out/'results-1280.png'))
 page.get_by_role('button',name='Podgląd 3D · HTML').click()
 assert page.evaluate("window.__calls.some(c=>c.cmd==='open_artifact'&&c.args.name==='PODGLAD_KOLOROW_3D.html')")
 assert page.locator('iframe').count()==0;page.screenshot(path=str(out/'preview-link-1280.png'))
 for width,height in [(1920,1080),(1366,768),(1024,600),(800,600),(640,480),(480,360)]:
  page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(100)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),('preview overflow',width,page.evaluate('document.documentElement.scrollWidth'))
 page.get_by_role('button',name='Nowe porównanie',exact=True).click();page.wait_for_timeout(900);assert page.get_by_role('heading',name='Porównaj modele',exact=True).is_visible();assert page.locator('iframe').count()==0
 for width,height in [(1366,768),(1024,600),(640,480),(480,360)]:
  page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(100);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),('compare overflow',width)
 page.screenshot(path=str(out/'compare-480.png'));page.set_viewport_size({'width':1280,'height':720})
 drop(['A.step','B.step'],'a');page.get_by_role('button',name='Porównaj rewizje',exact=True).click();assert page.get_by_role('button',name='Nowe porównanie',exact=True).is_disabled()
 page.evaluate("window.__job.question={token:'t',unresolved:true,material_unverified:false,translation_mm:[0,0,0],reason:'No anchor',unverified_A:0,unverified_B:0}")
 page.get_by_role('alertdialog').wait_for();assert 'Czy modele mają wspólne położenie?' in page.get_by_role('alertdialog').inner_text();assert page.locator('.translation').count()==0
 page.screenshot(path=str(out/'alignment-unresolved.png'));page.get_by_role('button',name='Oryginalne położenie',exact=True).click()
 # Material uncertainty must never require a user decision or show the old modal.
 page.evaluate("window.__job.question={token:'material-case',unresolved:false,material_unverified:true,translation_mm:[0,0,0],reason:'INVALID_BREP_AFTER_REPAIR',unverified_A:2,unverified_B:2}")
 page.wait_for_function("window.__calls.some(c=>c.cmd==='answer_question'&&c.args.token==='material-case'&&c.args.decision==='review')",timeout=5000)
 assert page.get_by_role('alertdialog').count()==0
 assert 'Niepełna analiza geometrii' not in page.locator('body').inner_text()
 assert 'Zapisuję automatycznie raport częściowy' in page.locator('main').inner_text()
 page.evaluate("window.__job={...window.__job,running:false,summary:window.__fixture}")
 page.get_by_role('heading',name='Wyniki porównania',exact=True).wait_for(timeout=5000)
 assert page.get_by_label('Postęp analizy').count()==0
 assert page.get_by_label('Wyniki porównania').count()==1
 page.get_by_role('button',name='Nowe porównanie',exact=True).click();page.wait_for_timeout(200)
 assert page.get_by_label('Wyniki porównania').count()==0
 assert not errors,errors
 print('USABILITY_BROWSER_PASS: native SDK drop events at 125% DPI, A/B and batch drops, dedup/rejection, formatted mass, HTML BOM routing, inline results/external HTML 3D, fresh comparison/stale job reset, 480–1920px layouts, unresolved alignment, automatic partial report, correct new-comparison placement, active-job guard',flush=True)
 browser.close()
