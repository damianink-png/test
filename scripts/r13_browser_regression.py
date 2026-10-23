"""R13 browser regression: tree names, selection, filtering and picking in offline Edge."""
from pathlib import Path
import os
from playwright.sync_api import sync_playwright
from dsac29.step_io import load_step
from dsac29.compare import Record
from dsac29.preview3d import create_preview

root=Path.cwd()
a=load_step(str(root/'samples/MODEL_A.step'))
b=load_step(str(root/'samples/MODEL_B.step'))
out=root/'R13_HTML_TREE_BROWSER.html'
records=[
    Record(0,None,'REMOVED',''),
    Record(None,0,'ADDED',''),
    Record(1,1,'MOVED',''),
]
info=create_preview(out,records,a,b)
assert info['elementy']==4,info
edges=[
    Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe',
    Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Microsoft/Edge/Application/msedge.exe'
]
exe=next((p for p in edges if p.exists()),None)
assert exe,'Brak Microsoft Edge w runnerze Windows'
with sync_playwright() as driver:
    browser=driver.chromium.launch(executable_path=str(exe),headless=True,
        args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1280,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(out.as_uri())
    page.wait_for_function("document.querySelectorAll('.tree-leaf').length===4",timeout=30000)
    assert not page.locator('#err').is_visible(),page.locator('#err').inner_text()
    assert page.locator('#tree .tree-leaf').count()==4
    assert page.locator('.tree-leaf .filename').first.inner_text().strip()
    page.locator('#tree .tree-leaf').first.click()
    assert page.locator('.tree-leaf.selected').count()==1
    assert 'rewizja A' in page.locator('#selection').inner_text()
    page.locator('#focus').click()
    page.locator('#isolate').click()
    assert page.locator('#isolate').inner_text()=='Pokaż pozostałe'
    page.locator('#isolate').click()
    page.locator('#treeSearch').fill('słowo którego nie ma w nazwie')
    assert page.locator('#tree .tree-leaf:visible').count()==0
    page.locator('#treeSearch').fill('')
    assert page.locator('#tree .tree-leaf:visible').count()==4
    page.locator('#removed').click()
    assert page.locator('#legend input[data-status="REMOVED"]').is_checked()
    page.locator('#all').click()
    page.locator('#clearPick').click()
    page.locator('#xray').uncheck()
    page.locator('#alpha').fill('1')
    page.locator('#xray').check()
    # Actual canvas -> tree picking, sampling locations over the model area.
    found=False
    for x,y in [(590,460),(500,420),(630,370),(690,500),(460,500),(550,590),
                (650,580),(380,410),(750,430)]:
        page.mouse.click(x,y)
        if page.locator('.tree-leaf.selected').count()==1:
            found=True
            break
    assert found,'Clicking visible WebGL geometry did not select a tree item'
    assert page.locator('#selection').inner_text().strip()
    assert not errors,errors
    page.screenshot(path=str(root/'R13_HTML_TREE_SCREEN.png'),full_page=True)
    browser.close()
print('PASS R13: offline Edge WebGL 3D tree, search, old/new, both selection directions')
