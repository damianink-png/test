"""Check actual preview occurrence records, including removed material."""
import json,re,math,base64,struct
def audit_preview(text,summary,*,allow_uncertain=False):
 match=re.search(r'^const scene=(.*);$',text,re.M);assert match,'Missing scene'
 scene=json.loads(match.group(1));records=summary['records'];observed={};meshes=set()
 regions={r['record_index']:r for r in summary.get('material_regions',[])}
 assert not summary.get('material_errors'),'Incomplete material analysis'
 for p in scene:
  i=p['record_index'];assert 0<=i<len(records)
  role=p['role'];assert role in ('A','B')
  assert p['part_index']==records[i]['a_index' if role=='A' else 'b_index']
  assert p['pair_id']==f'PAIR_{i:06d}'
  assert p['alpha']==(summary['old_alpha'] if role=='A' else 1.)
  assert len(p['matrix'])==12 and all(math.isfinite(x) for x in p['matrix'])
  if 'mesh_data' in p:
   data=base64.b64decode(p['mesh_data'],validate=True)
   assert data and len(data)%36==0
   assert all(math.isfinite(x[0]) for x in struct.iter_unpack('<f',data))
   assert p['mesh_id'] not in meshes
   meshes.add(p['mesh_id'])
  assert p['mesh_id'] in meshes
  observed.setdefault(i,set()).add((role,p['status']))
 for i,r in enumerate(records):
  status=r['status']
  if status in ('SAME','RENAMED'):
   expected={('B','SAME')}
   if summary.get('preview_3d',{}).get('dual_revisions'):expected.add(('A','SAME'))
  elif status=='ADDED':expected={('B','ADDED')}
  elif status=='REMOVED':expected={('A','REMOVED')}
  elif status=='MOVED':expected={('A','MOVED_OLD'),('B','MOVED')}
  elif status=='CHANGED':
   reg=regions[i]
   expected={(role,key) for role,key,v in [('B','CHANGED_COMMON',reg['common_mm3']),('B','CHANGED_ADDED',reg['added_mm3']),('A','CHANGED_REMOVED',reg['removed_mm3'])] if v>1e-7}
   if summary.get('preview_3d',{}).get('dual_revisions') and reg['common_mm3']>1e-7:expected.add(('A','CHANGED_COMMON'))
  elif status=='UNCERTAIN' and allow_uncertain:
   expected=set()
   if r.get('a_index') is not None:expected.add(('A','UNCERTAIN_OLD'))
   if r.get('b_index') is not None:expected.add(('B','UNCERTAIN_NEW'))
  else:raise AssertionError('Unverified status '+status)
  assert observed.get(i,set())==expected,f'Missing/wrong scene regions: {i}'
 assert len(scene)==summary['preview_3d']['elementy']
 return len(scene)
