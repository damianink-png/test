"""CAD landmark registration: global consensus, trimmed rigid refinement.

Own NumPy implementation of distance-consistent correspondence sampling and
trimmed point-to-point refinement. No scaling, no reflections, no geometry
classification. Every returned pose is only a hypothesis for B-Rep checking.
See docs/registration-audit-0.6.5.md for sources, limits and design choices.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import product, permutations
from math import floor
import numpy as np


@dataclass
class Pose:
    rotation: np.ndarray
    translation: np.ndarray
    pairs: list
    volume: float
    source: str


def pose_distance(rotation,translation,other_rotation,other_translation,points,radius=0.):
    """Conservative displacement bound; angular epsilon alone fails far from 0."""
    dr=np.asarray(rotation)-np.asarray(other_rotation)
    dt=np.asarray(translation)-np.asarray(other_translation)
    displacement=np.linalg.norm(points@dr.T+dt,axis=1)
    return float(np.max(displacement,initial=0.)+radius*np.linalg.norm(dr,2))


def check_cancel(cancelled):
    if cancelled and cancelled():
        from .compare import Cancelled
        raise Cancelled('Przerwano analizę')


def landmarks(parts, cancelled=None):
    """Rigid-equivariant landmarks from ORIGINAL vertices, independent of COM.

    Deduplicate coordinates so seam/topology multiplicity cannot move a point.
    Vertexless solids use a real CAD surface centroid. These are search points,
    never an assertion that the topology/geometry of two solids is equal.
    """
    from OCP.BRep import BRep_Tool
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Pnt
    from .geometry_registry import GeometryRegistry
    registry=GeometryRegistry();local_points={};points=[]
    for p in parts:
        check_cancel(cancelled)
        key=registry.definition(p)
        if key not in local_points:
            shape=p.shape.Located(TopLoc_Location())
            vertices={};ex=TopExp_Explorer(shape,TopAbs_VERTEX)
            while ex.More():
                v=BRep_Tool.Pnt_s(TopoDS.Vertex_s(ex.Current()))
                xyz=(v.X(),v.Y(),v.Z())
                vertices.setdefault(tuple(round(x,8) for x in xyz),xyz)
                ex.Next()
            if vertices:
                local_points[key]=np.mean(sorted(vertices.values()),axis=0)
            else:
                props=GProp_GProps();BRepGProp.SurfaceProperties_s(shape,props)
                center=props.CentreOfMass()
                local_points[key]=np.array([center.X(),center.Y(),center.Z()])
        world=gp_Pnt(*map(float,local_points[key])).Transformed(p.shape.Location().Transformation())
        point=np.array([world.X(),world.Y(),world.Z()])
        if not np.isfinite(point).all():raise ValueError('Nieprawidłowy punkt odniesienia CAD')
        points.append(point)
    return np.asarray(points,dtype=float).reshape((-1,3))


def compatible(a,b):
    # Loose descriptor admission, including ordinary STEP integration drift.
    # This threshold is NOT passed to any native geometry proof.
    return (getattr(a,'feature_kind',None)==getattr(b,'feature_kind',None) and
            min(a.area,b.area,a.volume,b.volume)>0 and
            abs(a.area-b.area)<=max(1.,.025*max(a.area,b.area)) and
            abs(a.volume-b.volume)<=max(.01,.05*max(a.volume,b.volume)))


def spread(ids,points,limit):
    ids=sorted(ids,key=lambda i:tuple(points[i]))
    if len(ids)<=limit:return ids
    # Distances to the cohort center are invariant under rigid placement.
    center=np.mean(points[ids],axis=0)
    first=max(ids,key=lambda i:(float(np.sum((points[i]-center)**2)),-i))
    selected=[first];used={first};dist=np.sum((points[ids]-points[first])**2,axis=1)
    for _ in range(limit-1):
        k=max((k for k in range(len(ids)) if ids[k] not in used),key=lambda k:(float(dist[k]),-k))
        selected.append(ids[k]);used.add(ids[k]);dist=np.minimum(dist,np.sum((points[ids]-points[ids[k]])**2,axis=1))
    return selected


def correspondences(a,b,aa,bb,limit=256):
    from .material_names import material_name_key
    # Index a broad area interval; no quadratic all-pairs matrix for 20k solids.
    order=sorted(range(len(b)),key=lambda j:b[j].area)
    areas=np.asarray([b[j].area for j in order]);families=[];descriptor_cache={}
    for i,p in enumerate(a):
        descriptor=(float(p.area),float(p.volume))
        if descriptor not in descriptor_cache:
            width=max(1.1,p.area*.027)
            lo=int(np.searchsorted(areas,p.area-width));hi=int(np.searchsorted(areas,p.area+width,side='right'))
            descriptor_cache[descriptor]=[j for j in order[lo:hi] if compatible(p,b[j])]
        js=descriptor_cache[descriptor]
        if js:families.append((len(js),i,js))
    families.sort(key=lambda x:(x[0],-a[x[1]].volume,tuple(aa[x[1]])))
    # Rare parts first, but reserve witnesses throughout repeated cohorts.
    chosen=[];seen=set()
    for count,i,js in families:
        key=(round(np.log(max(a[i].volume,1e-9)),1),round(np.log(max(a[i].area,1e-9)),1))
        if key not in seen:
            chosen.append((count,i,js));seen.add(key)
        if len(chosen)>=48:break
    extra=spread([i for _,i,_ in families],aa,min(32,len(families))) if families else []
    by_i={i:(count,i,js) for count,i,js in families}
    chosen.extend(by_i[i] for i in extra if i not in {v[1] for v in chosen})
    pools=[]
    for count,i,js in chosen:
        named=[j for j in js if material_name_key(a[i].name)==material_name_key(b[j].name)]
        sample=spread(js,bb,min(12,len(js)))
        candidates=list(dict.fromkeys(named[:2]+sample))
        pools.append([(i,j) for j in candidates])
    # Round robin stops a family of screws from exhausting the search budget.
    pairs=[]
    for k in range(max(map(len,pools),default=0)):
        for pool in pools:
            if k<len(pool):pairs.append(pool[k])
            if len(pairs)>=limit:return pairs
    return pairs


def match_pose(a,b,aa,bb,rotation,translation,gate,additional_points=None):
    inputs=[(aa,bb)]
    if additional_points is not None:inputs.append(additional_points)
    indexes=[]
    for left,right in inputs:
        cells=defaultdict(list)
        for i,point in enumerate(left):cells[tuple(np.floor(point/gate).astype('int64'))].append(i)
        indexes.append((cells,left,right@rotation.T+translation))
    options={}
    for j in range(len(b)):
        near={}
        for cells,left,moved in indexes:
            point=moved[j];base=tuple(np.floor(point/gate).astype('int64'))
            for delta in product((-1,0,1),repeat=3):
                for i in cells.get(tuple(base[k]+delta[k] for k in range(3)),()):
                    distance=float(np.linalg.norm(left[i]-point))
                    if distance<=gate and compatible(a[i],b[j]):near[i]=min(near.get(i,float('inf')),distance)
        if near:options[j]=[i for i in sorted(near,key=lambda i:(near[i],i))]
    # Maximum-cardinality one-to-one matching. Iterative augmenting paths do
    # not overflow the Python stack on large repeated component families.
    owner={};reverse={}
    for start in sorted(options,key=lambda j:(len(options[j]),j)):
        queue=[start];seen_j={start};seen_i=set();parent={};free=None
        for j in queue:
            for i in options[j]:
                if i in seen_i:continue
                seen_i.add(i);parent[i]=j
                if i not in owner:free=i;break
                other=owner[i]
                if other not in seen_j:seen_j.add(other);queue.append(other)
            if free is not None:break
        if free is None:continue
        while True:
            j=parent[free];old=reverse.get(j);owner[free]=j;reverse[j]=free
            if old is None:break
            free=old
    return sorted(owner.items())


def fit(aa,bb,weights=None):
    if len(aa)<3:return None
    weights=np.ones(len(aa)) if weights is None else np.asarray(weights)
    weights=weights/sum(weights)
    ca=weights@aa;cb=weights@bb;x=aa-ca;y=bb-cb
    if np.linalg.matrix_rank(x,tol=1e-7)<2 or np.linalg.matrix_rank(y,tol=1e-7)<2:return None
    u,_,vt=np.linalg.svd((y*weights[:,None]).T@x)
    flip=np.eye(3);flip[-1,-1]=1. if np.linalg.det(u@vt)>0 else -1.
    rotation=(u@flip@vt).T
    return rotation,ca-rotation@cb


def refine(a,b,aa,bb,rotation,translation,gate,cancelled=None):
    """Descriptor-constrained trimmed component-landmark ICP; scale is fixed."""
    for _ in range(6):
        check_cancel(cancelled)
        pairs=match_pose(a,b,aa,bb,rotation,translation,gate)
        if len(pairs)<3:break
        ii,jj=np.asarray(pairs).T
        residual=np.linalg.norm(aa[ii]-(bb[jj]@rotation.T+translation),axis=1)
        median=float(np.median(residual));mad=float(np.median(np.abs(residual-median)))
        keep=residual<=min(gate,max(1e-5,median+3*max(mad,1e-6)))
        if sum(keep)<3:break
        ii,jj=ii[keep],jj[keep]
        keys=[(round(np.log(a[i].area),1),round(np.log(a[i].volume),1)) for i in ii]
        counts=Counter(keys)
        result=fit(aa[ii],bb[jj],[1/counts[key] for key in keys])
        if result is None:break
        rr,tt=result
        delta=np.linalg.norm(tt-translation)+np.linalg.norm(rr-rotation)
        rotation,translation=rr,tt
        if delta<1e-9:break
    return rotation,translation


def hypotheses(a,b,tolerance,*,features=None,extended=False,rotations=False,cancelled=None,progress=None):
    if not a or not b:return []
    aa,bb=features if features is not None else (landmarks(a,cancelled),landmarks(b,cancelled))
    mass_points=None
    if not any(getattr(p,'feature_kind',None) is not None for p in a+b):
        # Secondary SEARCH index: STEP face splitting can bias vertex means.
        # Neither this index nor its mean translation is an equality proof.
        mass_points=(np.asarray([p.center for p in a]),np.asarray([p.center for p in b]))
    radius=max((float(np.linalg.norm(p.bbox)) for p in b),default=0.)
    gate=max(.05,5*tolerance)
    pool=correspondences(a,b,aa,bb,512 if extended else 256)
    poses=[]
    def offer(rotation,translation,source):
        if not np.isfinite(rotation).all() or not np.isfinite(translation).all():return
        if np.linalg.norm(rotation-np.eye(3))<1e-9 and np.linalg.norm(translation)<=tolerance:return
        if any(pose_distance(rotation,translation,p.rotation,p.translation,bb,radius)<=tolerance*.1 for p in poses):return
        pairs=match_pose(a,b,aa,bb,rotation,translation,gate,mass_points)
        if len(pairs)<(1 if len(a)==len(b)==1 else 2):return
        volume=sum(max(0.,a[i].volume) for i,j in pairs)
        poses.append(Pose(rotation,translation,pairs,volume,source))
    if not rotations:
        bins=defaultdict(list)
        for i,j in pool:
            off=aa[i]-bb[j];bins[tuple(np.round(off/gate).astype('int64'))].append(off)
        for values in sorted(bins.values(),key=lambda v:-len(v))[:(192 if extended else 48)]:
            check_cancel(cancelled);offer(np.eye(3),np.median(values,axis=0),'cad_translation_consensus')
        # Cohort means are unbiased by repeated occurrence sampling when
        # counts agree. They remain proposals and require native proofs.
        groups_a=defaultdict(list);groups_b=defaultdict(list)
        def key(p):return (round(np.log(p.area),1),round(np.log(p.volume),1))
        for i,p in enumerate(a):groups_a[key(p)].append(i)
        for j,p in enumerate(b):groups_b[key(p)].append(j)
        for k in sorted(groups_a.keys() & groups_b.keys()):
            ii,jj=groups_a[k],groups_b[k]
            if len(ii)==len(jj):offer(np.eye(3),np.mean(aa[ii],axis=0)-np.mean(bb[jj],axis=0),'cad_cohort_translation')
        if mass_points is not None and len(a)==len(b):
            offer(np.eye(3),np.mean(mass_points[0],axis=0)-np.mean(mass_points[1],axis=0),'mass_center_search_hint')
    elif len(pool)>=3:
        if progress:progress(f'Wyrównanie globalne: graf zgodności {len(pool)} skojarzeń CAD; szukanie obrotu i przesunięcia.')
        ij=np.asarray(pool);left=aa[ij[:,0]];right=bb[ij[:,1]]
        da=np.linalg.norm(left[:,None,:]-left[None,:,:],axis=2)
        db=np.linalg.norm(right[:,None,:]-right[None,:,:],axis=2)
        graph=(np.abs(da-db)<=gate)&(ij[:,0,None]!=ij[None,:,0])&(ij[:,1,None]!=ij[None,:,1])
        np.fill_diagonal(graph,False)
        degree=graph.sum(axis=1);order=np.argsort(-degree,kind='stable')
        rng=np.random.default_rng(19460119)
        tested=set();raw=[]
        for trial in range(1800 if extended else 600):
            if trial%32==0:check_cancel(cancelled)
            first=int(order[trial%len(order)]) if trial<len(order) else int(rng.choice(order))
            neighbors=np.flatnonzero(graph[first])
            if len(neighbors)<2:continue
            second=int(neighbors[trial%len(neighbors)]) if trial<len(order) else int(rng.choice(neighbors))
            third_options=np.flatnonzero(graph[first]&graph[second])
            if not len(third_options):continue
            third=int(third_options[trial%len(third_options)])
            triple=tuple(sorted((first,second,third)))
            if triple in tested:continue
            tested.add(triple);result=fit(left[list(triple)],right[list(triple)])
            if result is None:continue
            rotation,translation=result
            residual=np.linalg.norm(left-(right@rotation.T+translation),axis=1)
            count=int(sum(residual<=gate))
            if count>=3:raw.append((count,rotation,translation))
        selected=[]
        for count,rotation,translation in sorted(raw,key=lambda v:-v[0]):
            if any(np.linalg.norm(rotation-r)<1e-5 and np.linalg.norm(translation-t)<gate for r,t in selected):continue
            selected.append((rotation,translation))
            rr,tt=refine(a,b,aa,bb,rotation,translation,gate,cancelled)
            offer(rr,tt,'cad_distance_graph_trimmed_icp')
            if len(selected)>=(16 if extended else 8):break
    if rotations and not poses:
        # One component or collinear component centers cannot determine a
        # rotation from point triples. Native CAD principal frames provide
        # additional proposals; their eigenvalues never certify geometry.
        # Proper signed permutations cover frame sign/order ambiguity.
        for i,j in pool[:8]:
            check_cancel(cancelled)
            for perm in permutations(range(3)):
                for signs in product((-1.,1.),repeat=3):
                    basis=np.zeros((3,3))
                    for row,col in enumerate(perm):basis[row,col]=signs[row]
                    rr=np.asarray(a[i].axes)@basis@np.asarray(b[j].axes).T
                    if np.linalg.det(rr)<.999999:continue
                    offer(rr,aa[i]-rr@bb[j],'cad_principal_frame_proposal')
    if rotations and mass_points is not None and len(a)==len(b):
        for p in sorted(poses,key=lambda p:-len(p.pairs))[:3]:
            offer(p.rotation,np.mean(mass_points[0],axis=0)-p.rotation@np.mean(mass_points[1],axis=0),'mass_center_rigid_hint')
    poses.sort(key=lambda p:(-len(p.pairs),-p.volume,tuple(p.translation)))
    return poses
