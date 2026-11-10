"""Open3D FPFH + fast global registration / RANSAC against local ICP.
CAD-like synthetic surface clouds, no production DS Compare integration.
Metrics use independent known synthetic ground truth, not automatic fitness alone.
"""
from pathlib import Path
from time import perf_counter
import json
import math
import numpy as np
import open3d as o3d

rng=np.random.default_rng(20261110)

def sample_box(center, dims, count=400):
    center=np.asarray(center,float);dims=np.asarray(dims,float)
    faces=rng.integers(0,6,size=count)
    v=rng.uniform(-.5,.5,(count,3))*dims
    for axis in range(3):
        mask=(faces//2)==axis
        v[mask,axis]=((-1.)**(faces[mask]%2))*.5*dims[axis]
    return v+center

def sample_torus(center,major,minor,count=400):
    a=rng.uniform(0,2*np.pi,count)
    b=rng.uniform(0,2*np.pi,count)
    x=(major+minor*np.cos(b))*np.cos(a)
    y=(major+minor*np.cos(b))*np.sin(a)
    z=minor*np.sin(b)
    return np.column_stack((x,y,z))+np.asarray(center)

def geometry():
    return np.concatenate([
        sample_box((-180,-40,-40),(64,14,45),550),
        sample_box((-30,110,0),(24,100,13),500),
        sample_box((135,-125,65),(75,45,23),500),
        sample_torus((80,90,-80),42,7,650),
        sample_torus((-135,155,105),21,4,450),
    ])

def rot(axis,angle):
    axis=np.asarray(axis,float);axis/=np.linalg.norm(axis)
    x,y,z=axis
    s=np.sin(angle);c=np.cos(angle);C=1-c
    return np.array([[x*x*C+c,x*y*C-z*s,x*z*C+y*s],
                     [y*x*C+z*s,y*y*C+c,y*z*C-x*s],
                     [z*x*C-y*s,z*y*C+x*s,z*z*C+c]])

def point_cloud(points):
    p=o3d.geometry.PointCloud()
    p.points=o3d.utility.Vector3dVector(points)
    return p

def compute_features(points,voxel):
    cloud=point_cloud(points)
    reduced=cloud.voxel_down_sample(voxel)
    reduced.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(
        radius=2.5*voxel,max_nn=45))
    feature=o3d.pipelines.registration.compute_fpfh_feature(
        reduced,o3d.geometry.KDTreeSearchParamHybrid(
            radius=5.0*voxel,max_nn=100))
    return reduced,feature

def evaluate(result,r_true,t_true,seconds):
    x=result.transformation
    inverse_r=r_true.T
    inverse_t=-(inverse_r@t_true)
    return {'time_s':round(seconds,3),
            'translation_error_mm':round(float(np.linalg.norm(x[:3,3]-inverse_t)),3),
            'rotation_error_deg':round(float(np.degrees(
                np.arccos(np.clip((np.trace(x[:3,:3]@inverse_r.T)-1)/2,-1,1)))),3),
            'fitness':round(float(result.fitness),4),
            'inlier_rmse':round(float(result.inlier_rmse),3)}

def case(name,angle,missing=0.20,outliers=0.20):
    source=geometry()
    r_true=rot((.4,.7,.5),angle)
    t_true=np.array((130.,-280.,-410.))
    keep=rng.random(len(source))>(missing)
    b_true=source[keep]@r_true.T+t_true
    b_true=b_true+rng.normal(0,.12,b_true.shape)
    scale_min=np.min(b_true,axis=0)
    scale_max=np.max(b_true,axis=0)
    out=rng.uniform(scale_min-40,scale_max+40,size=(int(len(b_true)*outliers),3))
    b=np.concatenate((b_true,out))
    a_cloud=point_cloud(source)
    b_cloud=point_cloud(b)
    voxel=9.0
    start=perf_counter()
    a_small,a_fp=compute_features(source,voxel)
    b_small,b_fp=compute_features(b,voxel)
    feature_secs=perf_counter()-start
    methods={}
    # Naive local ICP is a baseline *proxy*, not the DS Compare engine.
    t0=np.mean(source,axis=0)-np.mean(b,axis=0)
    initial=np.eye(4);initial[:3,3]=t0
    started=perf_counter()
    try:
        icp=o3d.pipelines.registration.registration_icp(
            b_cloud,a_cloud,22.,initial,
            o3d.pipelines.registration.TransformationEstimationPointToPoint(),
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=65))
        methods['centroid_seeded_ICP']=evaluate(icp,r_true,t_true,perf_counter()-started)
    except Exception as exc:
        methods['centroid_seeded_ICP']={'error':str(exc)}
    started=perf_counter()
    try:
        fgr=o3d.pipelines.registration.registration_fgr_based_on_feature_matching(
            b_small,a_small,b_fp,a_fp,
            o3d.pipelines.registration.FastGlobalRegistrationOption(
                maximum_correspondence_distance=20.0,iteration_number=64,
                maximum_tuple_count=1200))
        methods['FPFH_FGR']=evaluate(fgr,r_true,t_true,perf_counter()-started+feature_secs)
    except Exception as exc:
        methods['FPFH_FGR']={'error':str(exc)}
    started=perf_counter()
    try:
        result=o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
            b_small,a_small,b_fp,a_fp,True,20.0,
            o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
            4,
            [o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(.9),
             o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(20.0)],
            o3d.pipelines.registration.RANSACConvergenceCriteria(25000,.999))
        methods['FPFH_RANSAC']=evaluate(result,r_true,t_true,perf_counter()-started+feature_secs)
    except Exception as exc:
        methods['FPFH_RANSAC']={'error':str(exc)}
    return {'case':name,'source_points':len(source),'revised_points':len(b),
            'reused_fraction':round(float(keep.mean()),3),
            'outlier_ratio':outliers,'feature_seconds':round(feature_secs,3),
            'downsample_A':len(a_small.points),'downsample_B':len(b_small.points),
            'methods':methods}

if __name__=='__main__':
    results={
        'engine':'Open3D 0.19.0 real FPFH+FGR/RANSAC and ICP',
        'model':'synthetic point clouds sampled from CAD-like boxes and toroidal surfaces',
        'accuracy_thresholds':{'translation_mm':1.,'rotation_degrees':.5},
        'note':'No production DS Compare; no ZW3D STEP; full preprocessing included in global timings',
        'cases':[
            case('translation_20pct_removed_20pct_outliers',0.,missing=.20,outliers=.20),
            case('rotation_20pct_removed_20pct_outliers',.46,missing=.20,outliers=.20)
        ],
    }
    for case_result in results['cases']:
        for method,detail in case_result['methods'].items():
            if 'translation_error_mm' in detail:
                detail['correct']=bool(detail['translation_error_mm']<1.
                                       and detail['rotation_error_deg']<.5)
    out=Path('evidence/alternative-open3d.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(results,indent=2,ensure_ascii=False),flush=True)
