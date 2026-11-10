"""Experimental REAL TEASER++ Python binding, not a TEASER approximation.
Identical shuffled correspondences compared with SciPy Kabsch + 240-trial RANSAC.
The run is on Linux because official TEASER++ docs don't support Windows.
"""
import numpy as np, json, time
from pathlib import Path
from collections import Counter
import teaserpp_python as teaser

rng=np.random.default_rng(451)
n=85
old=rng.uniform(-900,900,(n,3))
axis=np.array([.4,.2,.7]);axis/=np.linalg.norm(axis)
theta=.46;x,y,z=axis
k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
r=np.eye(3)+np.sin(theta)*k+(1-np.cos(theta))*(k@k)
t=np.array([130.,-280.,-410.])
new=old@r.T+t+rng.normal(0.,.04,(n,3))
bad=rng.choice(n,25,replace=False)
new[bad]=rng.uniform(-1500,1500,(len(bad),3))

def kabsch(a,b):
    ma=a.mean(axis=0);mb=b.mean(axis=0)
    u,s,vt=np.linalg.svd((a-ma).T@(b-mb))
    d=np.eye(3);d[-1,-1]=np.linalg.det(u@vt)
    q=u@d@vt
    return q,mb-ma@q

def measure(rotation,translation):
    return dict(rotation_error_deg=float(np.rad2deg(np.arccos(np.clip((np.trace(rotation.T@r)-1)/2,-1,1)))),
                translation_error_mm=float(np.linalg.norm(translation-t)))

start=time.perf_counter()
best=None
for it in range(240):
    ids=rng.choice(n,3,replace=False)
    rr,tt=kabsch(old[ids],new[ids])
    delta=np.linalg.norm(old@rr+tt-new,axis=1)
    inliers=delta<.5
    if best is None or inliers.sum()>best.sum():best=inliers
rr,tt=kabsch(old[best],new[best])
# Kabsch produces a ROW-vector rotation old @ rr -> new. TEASER++
# produces a COLUMN-vector rotation R @ old -> new; compare rr.T to R.
baseline={'seconds':round(time.perf_counter()-start,5),'inliers':int(best.sum()),**measure(rr.T,tt)}

params=teaser.RobustRegistrationSolverParams(
    cbar2=1,
    noise_bound=.20,
    estimate_scaling=False,
    rotation_estimation_algorithm=teaser.RotationEstimationAlgorithm.GNC_TLS,
    rotation_gnc_factor=1.4,
    rotation_max_iterations=100,
    rotation_cost_threshold=1e-12
)
solver=teaser.RobustRegistrationSolver(*params)
start=time.perf_counter()
solver.solve(old.T.copy(),new.T.copy())
secs=time.perf_counter()-start
solution=solver.getSolution() if hasattr(solver,'getSolution') else solver.solution
teaser_result={'seconds':round(secs,5),
               'rot_matrix_shape':list(np.asarray(solution.rotation).shape),
               **measure(np.asarray(solution.rotation),np.asarray(solution.translation).reshape(3))}
data={'n_correspondences':n,'wrong_correspondences':len(bad),
      'noise_sigma_mm':.04,'results':{'kabsch_ransac_240':baseline,'TEASER++':teaser_result},
      'platform':'Ubuntu Linux: Python C++ binding built from official upstream',
      'not_full_DSCompare':True}
p=Path('evidence/alternative-teaser.json');p.parent.mkdir(exist_ok=True,parents=True)
p.write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data,indent=2),flush=True)
