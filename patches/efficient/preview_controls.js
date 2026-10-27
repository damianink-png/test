// Original DS Compare implementation; no third-party source embedded.
function selectPreviewMode(mode){
 isolation=false;
 document.getElementById('isolate').textContent='Izoluj';
 itemVisible.fill(true);
 for(const check of checks){
  const status=check.dataset.status;
  check.checked=mode==='all'||(mode==='changes'&&status!=='SAME')||
   (mode==='removed'&&['REMOVED','CHANGED_REMOVED','CHANGED_OLD','MOVED_OLD'].includes(status));
  visible[status]=check.checked;
 }
 syncTree();schedule();
}
function showRevisionPair(){
 if(selectedId<0)return;
 const pair=chunks[selectedId].pair_id;
 selectPreviewMode('all');
 itemVisible=chunks.map((c,i)=>pair!==undefined?c.pair_id===pair:i===selectedId);
 syncTree();schedule();
}
document.getElementById('pair').onclick=showRevisionPair;
