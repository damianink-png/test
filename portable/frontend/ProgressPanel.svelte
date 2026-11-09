<script lang="ts">
 import {onMount} from 'svelte';
 import type {Job} from './model';
 import CadComparisonScene from './CadComparisonScene.svelte';
 let {job,elapsed,oncancel}:{job:Job;elapsed:number;oncancel:()=>void}=$props();
 let now=$state(Date.now()),logs=$state(false);
 const progress=$derived(job.progress);
 const age=$derived(progress?.timestamp_ms?Math.max(0,Math.floor((now-progress.timestamp_ms)/1000)):null);
 const percent=$derived(progress?.total&&progress.completed!==undefined?Math.min(100,Math.max(0,100*progress.completed/progress.total)):null);
 const steps=['Import','Analiza','Porównanie','Wynik'];
 const phase=$derived((progress?.phase||job.events.at(-1)||'').toLowerCase());
 const phaseIndex=$derived(
    /raport|export|zapis|generow|wynik|podsumowan|scena/.test(phase)?3:
    /porówn|dopas|brep|common|zgodno|rejestrac|wyrówn|transformac|rewizj/.test(phase)?2:
    /import|readfile|transfer|wczytywan|wczytan|otwieran/.test(phase)?0:1);
 onMount(()=>{const timer=setInterval(()=>now=Date.now(),1000);return()=>clearInterval(timer)});
</script>

<section class="job-panel cad-job" aria-label="Postęp analizy">
 <div class="job-header">
  <span class="job-indicator" class:running-dot={job.running}></span>
  <strong>{job.running?job.question?'Oczekiwanie na decyzję':'Analiza w toku':job.cancelled?'Anulowano':job.error?'Analiza przerwana':'Operacja zakończona'}</strong>
  <span class="muted">{Math.floor(elapsed/60)}:{String(elapsed%60).padStart(2,'0')}</span>
  <button class="subtle" onclick={()=>logs=!logs}>{logs?'Ukryj dziennik':'Dziennik analizy'}</button>
  {#if job.running}<button class="cancel-button" onclick={oncancel}>Anuluj</button>{/if}
 </div>
 <CadComparisonScene paused={Boolean(job.question)}/>
 <div class="cad-job-steps" aria-label="Etapy analizy">
  {#each steps as step,i}
   <span class:active={phaseIndex===i} class:done={phaseIndex>i}>
    <i aria-hidden="true">{phaseIndex>i?'✓':String(i+1).padStart(2,'0')}</i>
    {step}
   </span>
  {/each}
 </div>
 <div class="progress-facts"><span>{job.question?'Wybierz sposób dalszej analizy.':progress?.phase||'Przygotowywanie analizy…'}</span>
  {#if percent!==null}<strong>{Math.round(percent)}%</strong>{/if}
 </div>
 {#if job.running}
  {#if percent!==null}
   <progress aria-label="Postęp bieżącego etapu" max="100" value={percent}></progress>
  {:else}
   <div class="indeterminate" role="progressbar" aria-label="Oczekiwanie na wynik bieżącej operacji"><span></span></div>
  {/if}
  {#if age!==null&&age>60&&!job.question}
   <p>Ostatni komunikat dziennika: {job.events.length?job.events[job.events.length-1]:'Oczekiwanie na pierwszy komunikat…'} · {age} s bez aktualizacji. Dłuższa operacja CAD nie musi oznaczać zawieszenia.</p>
  {/if}
 {/if}
 {#if logs}<pre>{job.events.join('\n')}</pre>{/if}
</section>

<style>
 .cad-job{overflow:hidden;padding:16px;border-radius:13px}
 .cad-job :global(.job-header){margin-bottom:14px}
 .cad-job-steps{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0 15px}
 .cad-job-steps span{display:flex;align-items:center;justify-content:center;gap:7px;min-width:0;border:1px solid var(--line);border-radius:8px;background:var(--bg);padding:9px 4px;font-size:11px;color:var(--muted);font-weight:600;white-space:nowrap}
 .cad-job-steps i{font-style:normal;font-size:10px;display:grid;place-items:center;width:21px;height:21px;border:1px solid var(--soft);border-radius:7px;flex:none}
 .cad-job-steps span.active{color:#84e5e1;border-color:#23b8cb;background:linear-gradient(110deg,#105267,#143045);box-shadow:inset 0 0 13px #13ccdf1b}
 .cad-job-steps span.active i{border-color:#39cdea;color:#c5ffff;box-shadow:0 0 10px #22defc55}
 .cad-job-steps span.done{color:var(--accent)}
 .cad-job-steps span.done i{background:#125c50;border-color:#349d7e;color:#b9f9de}
 .cad-job :global(.progress-facts){display:flex;justify-content:space-between;gap:10px;align-items:center}
 .cad-job :global(.progress-facts strong){color:var(--accent);font-variant-numeric:tabular-nums}
 @media(max-width:640px){.cad-job-steps{gap:4px}.cad-job-steps span{font-size:9px;gap:3px}.cad-job-steps i{width:17px;height:17px;font-size:9px}.cad-job{padding:10px}}
 @media(prefers-reduced-motion:reduce){.cad-job :global(.indeterminate span){animation:none}}
</style>
