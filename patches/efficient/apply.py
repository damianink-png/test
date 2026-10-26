from pathlib import Path
import sys,ast,shutil
root=Path(sys.argv[1]);here=Path(__file__).parent
for name in ('robust_translation.py','shared_mesh.py'):shutil.copy2(here/name,root/name)
def edit(name,old,new):
    p=root/name;s=p.read_text(encoding='utf-8')
    if s.count(old)!=1:raise RuntimeError(f'Unexpected source {name}: {old[:80]}')
    s=s.replace(old,new);p.write_text(s,encoding='utf-8')
edit('preview3d.py','    mesh_cache=_MeshCache()', '    from .shared_mesh import SharedMesh\n    mesh_cache=SharedMesh()')
edit('preview3d.py', '''        vertices=(mesh_cache.world_points(part.shape,max(0.15,min(3.0,extent*0.003)))-origin).reshape(-1)
        if not vertices.size:raise ValueError(f'Brak siatki części {part.name}; podgląd nie został opublikowany.')
        total+=len(vertices)//9''', '''        payload,count=mesh_cache.pack(part.shape,max(0.15,min(3.0,extent*0.003)),origin,_faces_meshed)
        total+=count//3''')
edit('preview3d.py',"'data':base64.b64encode(np.asarray(vertices,dtype='<f4').tobytes()).decode('ascii')",'**payload')
edit('preview3d.py',"'mesh_cache_hits':mesh_cache.hits,", "'mesh_cache_hits':mesh_cache.hits,'unique_meshes':mesh_cache.definitions,")
edit('preview_template.html', '''for(const piece of scene){const str=atob(piece.data),bytes=new Uint8Array(str.length);for(let i=0;i<str.length;i++)bytes[i]=str.charCodeAt(i);const pts=new Float32Array(bytes.buffer);''', '''const meshDefinitions=new Map();
for(const piece of scene){
 if(piece.mesh_data!==undefined){const str=atob(piece.mesh_data),bytes=new Uint8Array(str.length);for(let i=0;i<str.length;i++)bytes[i]=str.charCodeAt(i);meshDefinitions.set(piece.mesh_id,new Float32Array(bytes.buffer));delete piece.mesh_data;}
 const local=meshDefinitions.get(piece.mesh_id);if(!local)throw Error('Brak definicji siatki '+piece.mesh_id);
 const pts=new Float32Array(local.length),m=piece.matrix;
 for(let i=0;i<local.length;i+=3)for(let k=0;k<3;k++)pts[i+k]=m[k*4]*local[i]+m[k*4+1]*local[i+1]+m[k*4+2]*local[i+2]+m[k*4+3];''')
edit('preview_template.html', "if(!chunks.length)throw Error('Brak brył w scenie HTML.');", "meshDefinitions.clear();\nif(!chunks.length)throw Error('Brak brył w scenie HTML.');")
# Start from strict RC9 Stability, NOT the later optional-Common patch.
p=root/'revision_overlap.py';s=p.read_text(encoding='utf-8')
if 'OPTIONAL_COMMON_FAILED' in s:raise RuntimeError('Expected strict RC9 source')
s=s.replace("except Exception:\n                stat['invalid_boolean']+=1;continue", "except Exception as exc:\n                raise NativeGeometryFailure('Niekompletna analiza wspólnego materiału: '+str(exc)) from exc")
s=s.replace("except Exception:\n            stat['invalid_boolean']+=1;continue", "except Exception as exc:\n            raise NativeGeometryFailure('Niekompletna analiza różnic materiału: '+str(exc)) from exc")
p.write_text(s,encoding='utf-8')
for name in ('preview3d.py','shared_mesh.py','robust_translation.py','revision_overlap.py'):ast.parse((root/name).read_text(encoding='utf-8'))
print('Exact preview definitions; indexed consensus; strict incomplete-analysis propagation')
# Existing assertions still check decoded world-space coordinates, all bodies,
# colors and tree identities. Only their payload reader changes for schema 2.
tests=root.parent/'tests'
shutil.copy2(here/'preview_decode.py',tests/'preview_decode.py')
for name in ('test_r6_preview.py','test_r13_html_tree.py'):
    p=tests/name;s=p.read_text(encoding='utf-8')
    s='from preview_decode import expand_scene\n'+s
    s=s.replace("return json.loads(re.search(r'const scene=(.*);',text).group(1))", "return expand_scene(json.loads(re.search(r'const scene=(.*);',text).group(1)))")
    s=s.replace("return json.loads(re.search(r'^const scene=(.*);$',text,flags=re.M).group(1))", "return expand_scene(json.loads(re.search(r'^const scene=(.*);$',text,flags=re.M).group(1)))")
    p.write_text(s,encoding='utf-8')
