import base64
import numpy as np

def expand_scene(scene):
    definitions={};result=[]
    for piece in scene:
        if 'mesh_data' in piece:
            definitions[piece['mesh_id']]=np.frombuffer(base64.b64decode(piece['mesh_data']),dtype='<f4').reshape(-1,3)
        local=definitions[piece['mesh_id']]
        m=np.asarray(piece['matrix']).reshape(3,4)
        world=local@m[:,:3].T+m[:,3]
        result.append(dict(piece,data=base64.b64encode(np.asarray(world,dtype='<f4').tobytes()).decode()))
    return result

