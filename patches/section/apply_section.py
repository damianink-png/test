from pathlib import Path
import sys
p=Path(sys.argv[1])/'preview_template.html';s=p.read_text(encoding='utf-8')
def patch(old,new):
 global s
 if s.count(old)!=1:raise RuntimeError('Unexpected preview: '+old[:80])
 s=s.replace(old,new)
patch('<section id="treePanel">','''<details><summary>Przekrój podglądu</summary>
<label>Oś <select id="sectionAxis" aria-label="Oś przekroju"><option value="off">Wyłączony</option><option value="0">X</option><option value="1">Y</option><option value="2">Z</option></select></label>
<label>Położenie <input id="sectionPosition" aria-label="Położenie przekroju" type="range" min="0" max="100" step="0.5" value="50" disabled></label>
<label><input id="sectionFlip" type="checkbox" disabled>Odwróć stronę</label>
<p>Odsłonięcie wnętrza modelu; bez wypełnienia powierzchni cięcia. STEP pozostaje pełny.</p></details>
<section id="treePanel">''')
patch('varying float light;void main(){gl_Position', 'varying float light;varying mediump vec3 modelPoint;void main(){modelPoint=pos;gl_Position')
patch('varying float light;void main(){gl_FragColor', 'varying float light;varying mediump vec3 modelPoint;uniform vec4 sectionPlane;void main(){if(dot(sectionPlane.xyz,modelPoint)>sectionPlane.w)discard;gl_FragColor')
patch("const loc=gl.getAttribLocation(pr,'pos')", "const sectionLoc=gl.getUniformLocation(pr,'sectionPlane');\nconst loc=gl.getAttribLocation(pr,'pos')")
patch('function render(picking=false){', '''function sectionPlaneValues(axis,percent,flip){
 if(axis==='off')return [0,0,0,1];
 const k=Number(axis),sign=flip?-1:1;
 const position=lo[k]+(hi[k]-lo[k])*Number(percent)/100;
 const plane=[0,0,0,sign*(position-center[k])*2/span];plane[k]=sign;return plane;
}
const sectionAxis=document.getElementById('sectionAxis'),sectionPosition=document.getElementById('sectionPosition'),sectionFlip=document.getElementById('sectionFlip');
function updateSection(){const off=sectionAxis.value==='off';sectionPosition.disabled=sectionFlip.disabled=off;schedule();}
sectionAxis.onchange=updateSection;sectionPosition.oninput=updateSection;sectionFlip.onchange=updateSection;
function render(picking=false){
gl.uniform4fv(sectionLoc,sectionPlaneValues(sectionAxis.value,sectionPosition.value,sectionFlip.checked));''')
p.write_text(s,encoding='utf-8')
