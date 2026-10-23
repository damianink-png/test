"""SO-ARM100: real assembly roundtrip STEP and global translation recovery.

Checks the displacement hypothesis, not unsupported 19/19 SAME classification;
STEP roundtrips can alter B-Rep beyond strict identity tolerances.
"""
import sys,json
from pathlib import Path
from OCP.gp import gp_Trsf,gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from dsac29.step_io import load_step,ColoredDocument
from dsac29.deferred_alignment import propose_from_stage1

src=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
out.mkdir(parents=True,exist_ok=True)
a=load_step(str(src),max_solids=1000)
assert len(a)==19,len(a)
shift=(1275.,-395.,210.)
tr=gp_Trsf();tr.SetTranslation(gp_Vec(*shift))
writer=ColoredDocument(group_by_status=False,reuse_definitions=True)
for p in a:writer.add(BRepBuilderAPI_Transform(p.shape,tr,True).Shape(),
                      p.name,(.4,.5,.75),1.)
moved=out/"REAL_SO_ARM100_SHIFTED.step"
writer.write(str(moved))
b=load_step(str(moved),max_solids=1000)
assert len(b)==len(a)
proposal=propose_from_stage1(a,b,[],list(range(len(a))),list(range(len(b))),.01,
                             progress=lambda m:print("ALIGN:",m,flush=True))
print("SO REAL ROUNDTRIP ALIGNMENT",proposal,flush=True)
assert proposal is not None and proposal.get("status")=="registered",proposal
offset=proposal["translation_B_to_A_mm"]
assert all(abs(float(offset[i])+shift[i])<.05 for i in range(3)),offset
assert proposal.get("center_votes",0)>=18
assert proposal.get("votes",0)>=2
assert proposal.get("method")=="centroid_consensus_brep_anchors"
outcome={"source_file":src.name,"real_cad_solids":len(a),
         "shift_B_mm":shift,"detected_B_to_A_mm":offset,
         "coarse_centroid_votes":proposal["center_votes"],
         "strict_BRep_proofs":proposal["votes"],
         "classification":"not asserted due STEP roundtrip B-Rep numerical drift"}
(out/"SO_ROUNDTRIP_ALIGNMENT_TEST.json").write_text(
    json.dumps(outcome,indent=2,ensure_ascii=False),encoding="utf8")
print("SO SHIFT RECOVERY PASS",outcome,flush=True)
