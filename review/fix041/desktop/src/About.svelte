<script lang="ts">
 import {onMount} from 'svelte';
 import {X,RotateCcw,Layers3} from 'lucide-svelte';
 import logo from './assets/DSCompare.png';
 import {version} from '../package.json';
 let {onclose}:{onclose:()=>void}=$props();
 let dialog:HTMLDialogElement;let replay=$state(0);
 onMount(()=>{dialog.showModal();return()=>{if(dialog.open)dialog.close()}});
 function backdrop(event:MouseEvent){if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}
</script>
<dialog bind:this={dialog} class="about-dialog" aria-labelledby="about-title" onclose={onclose} onclick={backdrop}>
 <div class="about-top"><span><Layers3 size={16}/> O PROGRAMIE</span><button class="icon-button" aria-label="Zamknij okno O programie" onclick={()=>dialog.close()}><X size={19}/></button></div>
 <div class="about-body">
  {#key replay}<div class="logo-stage" role="img" aria-label="Logo DS Compare: modele A i B">
   <div class="logo-glow amber"></div><div class="logo-glow teal"></div>
   <div class="logo-assembly"><img class="logo-half logo-left" src={logo} alt="" draggable="false"/><img class="logo-half logo-right" src={logo} alt="" draggable="false"/><div class="logo-scan"></div></div>
   <span class="logo-caption">A <i></i> B</span>
  </div>{/key}
  <h1 id="about-title">DS Compare</h1><p class="about-tagline">Każda rewizja ma swoją historię.</p>
  <span class="about-version">Desktop {version} <span>·</span> RC9</span>
  <div class="about-author"><span>AUTOR APLIKACJI</span><strong>Damian Szymczyk</strong><p>Porównywanie geometrii CAD i rewizji złożeń</p></div>
  <dl class="about-facts"><div><dt>Modele</dt><dd>STEP / STP</dd></div><div><dt>Raporty</dt><dd>HTML · STEP · CSV · 3D</dd></div><div><dt>Interfejs</dt><dd>Svelte 5 · Tauri 2</dd></div><div><dt>Geometria</dt><dd>Python · Open CASCADE</dd></div></dl>
  <p class="about-credit">© 2026 Damian Szymczyk</p>
 </div>
 <div class="about-actions"><button class="subtle replay-animation" onclick={()=>replay++}><RotateCcw size={14}/>Powtórz animację</button><button class="primary" onclick={()=>dialog.close()}>Zamknij</button></div>
</dialog>
<style>
 .about-dialog{color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:17px;padding:0;width:min(520px,calc(100vw - 36px));max-height:calc(100dvh - 40px);box-shadow:0 35px 140px #0007;overflow:auto;scrollbar-width:thin;animation:about-enter .22s ease-out}
 .about-dialog::backdrop{background:#03070dbb;backdrop-filter:blur(7px)}
 .about-top{display:flex;align-items:center;justify-content:space-between;padding:14px 18px 8px 24px}.about-top>span{display:flex;gap:8px;align-items:center;font-size:9px;letter-spacing:1.9px;color:var(--muted);font-weight:600}.about-top button{padding:7px}
 .about-body{text-align:center;padding:0 34px 25px}.logo-stage{height:215px;width:260px;position:relative;margin:0 auto;isolation:isolate;display:grid;place-items:center;perspective:600px}.logo-assembly{position:relative;width:164px;height:164px;filter:drop-shadow(0 10px 16px #0003);overflow:hidden;border-radius:27px;transform:translateZ(0)}
 .logo-half{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;user-select:none;will-change:transform;animation-duration:1.45s;animation-timing-function:cubic-bezier(.18,.8,.22,1);animation-fill-mode:both}.logo-left{clip-path:inset(0 50% 0 0);animation-name:assemble-left}.logo-right{clip-path:inset(0 0 0 50%);animation-name:assemble-right}.logo-scan{position:absolute;inset:-10px auto -10px -70%;width:45%;background:linear-gradient(110deg,transparent,#fff2,transparent);transform:skewX(-15deg);animation:compare-scan 1.5s .7s ease-in-out both;pointer-events:none}
 .logo-glow{position:absolute;width:140px;height:140px;border-radius:50%;filter:blur(28px);z-index:-1;opacity:.15;animation:glow-settle 2s ease-out both}.amber{background:#ffb84d;left:20px;top:35px}.teal{background:#3fd3c2;right:20px;top:35px}.logo-caption{position:absolute;bottom:3px;display:flex;align-items:center;gap:12px;color:var(--muted);font-size:9px;letter-spacing:2px;opacity:.7}.logo-caption i{display:block;width:46px;height:1px;background:linear-gradient(90deg,#ffb84d,#3fd3c2)}
 .about-body h1{font-size:31px;letter-spacing:-1.2px;font-weight:650;margin:18px 0 7px}.about-tagline{font-size:12px;color:var(--muted);margin:0}.about-version{display:inline-flex;gap:9px;align-items:center;font-size:10px;color:var(--muted);padding:6px 11px;border:1px solid var(--line);border-radius:20px;margin:15px 0 23px}.about-version span{opacity:.5}
 .about-author{padding:20px 10px 21px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.about-author>span{display:block;font-size:8px;letter-spacing:1.8px;color:var(--muted);margin-bottom:10px}.about-author strong{font-size:20px;letter-spacing:-.4px;font-weight:550}.about-author p{font-size:10px;margin-top:8px;color:var(--muted)}.about-facts{display:grid;grid-template-columns:1fr 1fr;gap:19px 18px;text-align:left;margin:23px 0}.about-facts dt{color:var(--muted);font-size:9px;margin-bottom:6px}.about-facts dd{font-size:11px;margin:0}.about-credit{font-size:9px;color:var(--muted);margin-top:24px}.about-actions{border-top:1px solid var(--line);padding:15px 23px;display:flex;align-items:center;justify-content:space-between;gap:15px}.about-actions .primary{font-size:11px;padding:9px 20px}.replay-animation{font-size:10px}
 @keyframes assemble-left{from{transform:translate3d(-35px,7px,0) rotateY(-22deg);opacity:0}35%{opacity:1}to{transform:translate3d(0,0,0) rotateY(0);opacity:1}}
 @keyframes assemble-right{from{transform:translate3d(35px,-7px,0) rotateY(22deg);opacity:0}35%{opacity:1}to{transform:translate3d(0,0,0) rotateY(0);opacity:1}}
 @keyframes compare-scan{from{left:-70%;opacity:0}25%{opacity:1}to{left:150%;opacity:0}}
 @keyframes glow-settle{from{opacity:0;transform:scale(.7)}50%{opacity:.25}to{opacity:.15;transform:scale(1)}}
 @keyframes about-enter{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}
 @media(prefers-reduced-motion:reduce){.about-dialog,.logo-half,.logo-scan,.logo-glow{animation:none!important;will-change:auto}.logo-scan{display:none}.replay-animation{display:none}}
 @media(max-height:760px){.logo-stage{height:155px}.logo-assembly{width:124px;height:124px}.logo-caption{display:none}.about-body h1{margin-top:12px}.about-author{padding:14px 5px}.about-version{margin-bottom:16px}.about-body{padding-bottom:16px}.about-facts{gap:13px;margin:17px 0}}
</style>
