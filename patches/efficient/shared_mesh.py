"""Exact native-definition reuse for offline preview payloads only."""
import base64
import numpy as np
from OCP.TopLoc import TopLoc_Location

class SharedMesh:
    def __init__(self):
        self.entries={};self.hits=0;self.definitions=0
    def pack(self,shape,deflection,origin,mesh):
        local=shape.Located(TopLoc_Location())
        key=(hash(local),int(local.Orientation()),float(deflection))
        found=None
        for saved,definition in self.entries.get(key,()):
            if local.IsSame(saved):found=definition;break
        if found is None:
            points=np.asarray(list(mesh(local,deflection)),dtype=float).reshape(-1,3)
            if not points.size:raise ValueError('Brak pełnej siatki definicji części')
            # Center local coordinates before float32 conversion as well.
            center=(points.min(axis=0)+points.max(axis=0))/2
            data=base64.b64encode(np.asarray(points-center,dtype='<f4').tobytes()).decode('ascii')
            found=(self.definitions,center,len(points),data)
            self.entries.setdefault(key,[]).append((local,found));self.definitions+=1
            payload={'mesh_data':data}
        else:
            self.hits+=1;payload={}
        ident,center,count,_=found
        tr=shape.Location().Transformation()
        rot=np.array([[tr.Value(i,j) for j in range(1,4)] for i in range(1,4)])
        offset=rot@center+np.array([tr.Value(i,4) for i in range(1,4)])-origin
        payload.update(mesh_id=ident,matrix=np.column_stack((rot,offset)).reshape(-1).tolist())
        return payload,count

