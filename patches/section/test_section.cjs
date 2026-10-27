const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[2],'utf8');
const source=html.slice(html.indexOf('function sectionPlaneValues'),html.indexOf('const sectionAxis='));
const ctx={lo:[-10,-20,-30],hi:[10,20,30],center:[0,0,0],span:60};vm.createContext(ctx);vm.runInContext(source,ctx);
for(const axis of ['0','1','2'])for(const percent of [0,50,100])for(const flip of [false,true]){
 const p=ctx.sectionPlaneValues(axis,percent,flip),k=Number(axis),sign=flip?-1:1;
 assert.strictEqual(p[k],sign);assert(Math.abs(p[3]-sign*(ctx.lo[k]+(ctx.hi[k]-ctx.lo[k])*percent/100)*2/60)<1e-9);
}
assert.deepStrictEqual(Array.from(ctx.sectionPlaneValues('off',50,false)),[0,0,0,1]);
// Same fragment discard applies to normal rendering, selection highlight and picking.
assert(html.includes('if(dot(sectionPlane.xyz,modelPoint)>sectionPlane.w)discard;'));
new vm.Script(html.match(/<script>([\s\S]*)<\/script>/)[1].replace('/*__SCENE__*/','[]').replace('/*__STATS__*/','{}'));
console.log('Section: 18 axis/position/side cases, disabled state and JS syntax PASS');
