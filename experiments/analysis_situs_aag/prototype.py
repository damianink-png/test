"""Independent AAG-inspired OCCT experiment. NOT production DS Compare and
NOT the upstream Analysis Situs C++ library. Positive SAME still requires
two independent B-Rep Cuts; AAG never removes/accepts a candidate.
"""
import json,math,statistics,random,sys,tempfile
from pathlib import Path
from dataclasses import dataclass
from collections import Counter
from time import perf_counter
import numpy as np
import cadquery as cq
from OCP.TopExp import TopExp,TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape,TopTools_IndexedDataMapOfShapeListOfShape
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakeTorus
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse,BRepAlgoAPI_Cut
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Trsf,gp_Vec,gp_Pnt
from OCP.TopLoc import TopLoc_Location
from OCP.STEPControl import STEPControl_Writer,STEPControl_Reader,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone

@dataclass
class Item:
    shape:object
    key:str
    box:object
    center:object
    volume:float

def vol(shape):
    g=GProp_GProps();BRepGProp.VolumeProperties_s(shape,g)
    return float(g.Mass())

def box(shape):
    b=Bnd_Box();BRepBndLib.AddOptimal_s(shape,b,False,False)
    return np.asarray(b.Get(),float)

def moved(shape,xyz):
    t=gp_Trsf();t.SetTranslation(gp_Vec(*map(float,xyz)))
    return shape.Moved(TopLoc_Location(t))

def item(shape,key,xyz):
    s=moved(shape,xyz);bb=box(s)
    return Item(s,key,bb,(bb[:3]+bb[3:])/2,vol(s))

def sheet_l(w=20.,h=20.):
    return (cq.Workplane('XY').polyline([(0,0),(w,0),(w,2),(2,2),(2,h),(0,h)])
            .close().extrude(4).val().wrapped)

def basis(kind,n=0,ambiguous=False):
    if ambiguous:
        if kind=='plate':return BRepPrimAPI_MakeBox(20,20,4).Shape()
        if kind=='rod':return moved(BRepPrimAPI_MakeCylinder(10,4).Shape(),(10,10,0))
        if kind=='torus':return moved(BRepPrimAPI_MakeTorus(8,2).Shape(),(10,10,2))
        return sheet_l()
    if kind=='plate':return BRepPrimAPI_MakeBox(18+n*.08,21+n*.03,2).Shape()
    if kind=='rod':return BRepPrimAPI_MakeCylinder(3+n*.025,16).Shape()
    if kind=='torus':return BRepPrimAPI_MakeTorus(8+n*.015,1.8).Shape()
    return sheet_l(24+n*.06,18+n*.04)

def build(stations,ambiguous):
    kinds=('plate','rod','torus','bend')
    aa=[];bb=[]
    if ambiguous:
        original={k:basis(k,ambiguous=True) for k in kinds}
        reexport={k:basis(k,ambiguous=True) for k in kinds}
    for n in range(stations):
        xyz=(n*70.,(n%3)*65.,(n%4)*19.)
        for k in kinds:
            x=original[k] if ambiguous else basis(k,n)
            y=reexport[k] if ambiguous else basis(k,n)
            aa.append(item(x,f'{n}/{k}',xyz))
            bb.append(item(y,f'{n}/{k}',xyz))
    random.Random(123).shuffle(bb)
    return aa,bb

def descriptor(shape):
    nodes=TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape,TopAbs_FACE,nodes)
    if nodes.Extent()<1 or nodes.Extent()>800:return None
    types=[];radii=[]
    for i in range(1,nodes.Extent()+1):
        adaptor=BRepAdaptor_Surface(TopoDS.Face_s(nodes.FindKey(i)))
        kind=str(adaptor.GetType()).split('.')[-1].replace('GeomAbs_','')
        types.append(kind)
        if kind=='Cylinder':radii.append(round(adaptor.Cylinder().Radius(),3))
        if kind=='Torus':
            t=adaptor.Torus()
            radii.extend((round(t.MajorRadius(),3),round(t.MinorRadius(),3)))
    emap=TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape,TopAbs_EDGE,TopAbs_FACE,emap)
    arcs=Counter()
    degree=[set() for _ in types]
    for i in range(1,emap.Extent()+1):
        ids=sorted({nodes.FindIndex(TopoDS.Face_s(f))-1
                    for f in emap.FindFromIndex(i)})
        ids=[x for x in ids if x>=0]
        for p in range(len(ids)):
            for q in range(p+1,len(ids)):
                degree[ids[p]].add(ids[q]);degree[ids[q]].add(ids[p])
    for i,neighbors in enumerate(degree):
        for j in neighbors:
            if i<j:arcs[tuple(sorted((types[i],types[j])))]+=1
    return (tuple(sorted(Counter(types).items())),tuple(sorted(arcs.items())),
            tuple(sorted(Counter(len(x) for x in degree).items())),
            tuple(sorted(radii)))

def hist(a,b):
    if not a and not b:return 1.
    x=dict(a);y=dict(b);keys=x.keys()|y.keys()
    denom=sum(max(x.get(k,0),y.get(k,0)) for k in keys)
    return sum(min(x.get(k,0),y.get(k,0)) for k in keys)/denom if denom else 1.

def score(a,b):
    if a is None or b is None:return 0.
    radii=1. if not a[3] and not b[3] else (
        sum(any(abs(v-w)<.02 for w in b[3]) for v in a[3])/max(len(a[3]),len(b[3]),1))
    return .50*hist(a[0],b[0])+.35*hist(a[1],b[1])+.10*hist(a[2],b[2])+.05*radii

class Cache:
    def __init__(self):self.items={};self.hits=0;self.misses=0
    def get(self,s):
        # Python hash(s.TShape()) is an unstable wrapper identity.
        # Hash a location-free native shape and verify IsPartner on hit.
        key=(hash(s.Located(TopLoc_Location())),int(s.Orientation()))
        for old,feature in self.items.get(key,()):
            if s.IsPartner(old):
                self.hits+=1;return feature
        value=descriptor(s)
        self.items.setdefault(key,[]).append((s,value))
        self.misses+=1
        return value

def overlap(a,b):
    return float(np.prod(np.maximum(0.,np.minimum(a[3:],b[3:])-np.maximum(a[:3],b[:3]))))

def priority(a,b):
    ov=overlap(a.box,b.box)
    envelope=max(float(np.prod(a.box[3:]-a.box[:3])),
                 float(np.prod(b.box[3:]-b.box[:3])),1e-6)
    distance=np.linalg.norm(a.center-b.center)/max(1.,np.linalg.norm(a.box[3:]-a.box[:3]))
    return ov/envelope-.08*distance

def candidate_rows(a,b):
    rows=[]
    for x in a:
        scored=[]
        for j,y in enumerate(b):
            if overlap(x.box,y.box)<.13*max(x.volume,y.volume):
                continue
            scored.append((-priority(x,y),j))
        rows.append([j for _,j in sorted(scored)])
    return rows

def adaptive(a,b,rows):
    cache=Cache();ambiguous=0;start=perf_counter();ordered=[]
    for x,js in zip(a,rows):
        if len(js)<2 or priority(x,b[js[0]])-priority(x,b[js[1]])>.025:
            ordered.append(js[:]);continue
        ambiguous+=1;lhs=cache.get(x.shape)
        ranked=[(score(lhs,cache.get(b[j].shape)),pos,j) for pos,j in enumerate(js)]
        ordered.append([j for sc,pos,j in sorted(ranked,key=lambda v:(-v[0],v[1]))])
    return ordered,cache,perf_counter()-start,ambiguous

def native_equal(a,b):
    if abs(vol(a)-vol(b))>max(1e-5,1e-7*max(vol(a),vol(b))):return False
    for x,y in ((a,b),(b,a)):
        op=BRepAlgoAPI_Cut(x,y);op.Build()
        if not op.IsDone():return False
        if abs(vol(op.Shape()))>1e-5:return False
    return True

def trial(stations,ambiguous):
    a,b=build(stations,ambiguous)
    original=candidate_rows(a,b)
    ranked,cache,feature_time,amb=adaptive(a,b,original)
    truth={x.key:j for j,x in enumerate(b)}
    assert all(truth[x.key] in row for x,row in zip(a,original))
    assert all(set(x)==set(y) for x,y in zip(original,ranked))
    attempts={}
    for label,rows in (('baseline',original),('adaptive',ranked)):
        t=perf_counter();calls=0;verified=0;false_matches=0
        for x,js in zip(a,rows):
            for j in js:
                calls+=1
                ok=native_equal(x.shape,b[j].shape)
                if ok:
                    verified+=1
                    false_matches+=x.key!=b[j].key
                    break
        attempts[label]={'native_calls':calls,'verified':verified,
                         'incorrect_pairings':false_matches,
                         'native_seconds':round(perf_counter()-t,4)}
    total_adaptive=round(attempts['adaptive']['native_seconds']+feature_time,4)
    attempts['adaptive']['total_seconds']=total_adaptive
    attempts['baseline']['total_seconds']=attempts['baseline']['native_seconds']
    assert attempts['baseline']['verified']==attempts['adaptive']['verified']==len(a)
    assert attempts['baseline']['incorrect_pairings']==attempts['adaptive']['incorrect_pairings']==0
    return {'stations':stations,'solids_A':len(a),'solids_B':len(b),
            'scenario':'ambiguous_identical_envelopes' if ambiguous else 'ordinary_distinct_envelopes',
            'candidate_pairs':sum(map(len,original)),
            'ambiguous_parts':amb,'feature_seconds':round(feature_time,4),
            'cache_hits':cache.hits,'cache_misses':cache.misses,
            **attempts}

def topology_repartition():
    same=BRepPrimAPI_MakeBox(20,10,2).Shape()
    left=BRepPrimAPI_MakeBox(gp_Pnt(0,0,0),10,10,2).Shape()
    right=BRepPrimAPI_MakeBox(gp_Pnt(10,0,0),10,10,2).Shape()
    op=BRepAlgoAPI_Fuse(left,right);op.Build()
    assert op.IsDone()
    result=op.Shape()
    f1=descriptor(same);f2=descriptor(result)
    s=score(f1,f2)
    ok=native_equal(same,result)
    assert ok and s<.999
    return {'native_equal':ok,'aag_similarity':round(s,3),
            'face_count_A':sum(n for name,n in f1[0]),
            'face_count_B':sum(n for name,n in f2[0]),
            'if_hard_AAG_equality_required_false_negative':True}

def step_smoke():
    out=[]
    with tempfile.TemporaryDirectory() as tmp:
        for kind in ('plate','bend','torus','rod'):
            shape=basis(kind,2)
            fname=str(Path(tmp)/(kind+'.stp'))
            writer=STEPControl_Writer();writer.Transfer(shape,STEPControl_AsIs)
            assert writer.Write(fname)==IFSelect_RetDone
            reader=STEPControl_Reader();assert reader.ReadFile(fname)==IFSelect_RetDone
            reader.TransferRoots();other=reader.OneShape()
            ok=native_equal(shape,other)
            out.append({'kind':kind,'AAG':round(score(descriptor(shape),descriptor(other)),3),
                        'verified':ok})
    assert all(x['verified'] for x in out)
    return out

if __name__=='__main__':
    ordinary=trial(60,False)
    ambiguous=trial(32,True)
    data={'method':'Python/OCP AAG-inspired only, not native Analysis Situs C++',
          'scope':'native SAME candidate ordering; not full DS Compare or crash-isolated Common',
          'ordinary':ordinary,'ambiguous':ambiguous,
          'different_face_partition':topology_repartition(),
          'STEP_roundtrips':step_smoke(),
          'production_modified':False}
    dest=Path(sys.argv[1] if len(sys.argv)>1 else 'aag-results.json')
    dest.parent.mkdir(exist_ok=True,parents=True)
    dest.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps(data,indent=2,ensure_ascii=False))
