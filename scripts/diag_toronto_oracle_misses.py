#!/usr/bin/env python3
import csv, json, math, sys
from collections import Counter
from pathlib import Path

root=Path(sys.argv[1])
def rows(p):
    with open(p,newline="") as f:
        return list(csv.DictReader(f))

tracks=rows(root/"nextgen_mask/tracks.csv")
assign=rows(root/"global_identity/identity_assignments.csv")
obs=rows(root/"identity_segments/uniform_observations.csv")
segs=rows(root/"identity_segments/segments.csv")
cfg=json.load(open(root/"global_identity/resolved_config.json"))
qa=json.load(open(root/"global_identity/global_identity_qa.json"))
try:
    vqa=json.load(open(root/"global_identity/visual_identity_oracle_qa.json"))
except Exception as e:
    vqa={"error":repr(e)}

print("VISUAL_QA",json.dumps(vqa,indent=2))
print("MIXED_SEGMENTS",qa.get("mixed_uniform_segment_ids"))
print("ROLE_SUMMARY",json.dumps({k:v for k,v in qa.get("roles",{}).items() if k in ("rebounder","shooter","shooter_defender")},indent=2))

checks=[
    ("rebounder",203500,9.3038,(611.72882,356.89493)),
    ("shooter_defender",1641711,11.9064,(89.707113,365.42926)),
]

def asbool(v):
    return str(v).strip().lower() in {"1","true","yes"}

for role,pid,t,(ex,ey) in checks:
    print("\n===",role,pid,t,"===")
    rr=[r for r in assign if int(float(r.get("player_id") or -1))==pid and abs(float(r["time_s"])-t)<=0.45]
    rr.sort(key=lambda r:abs(float(r["time_s"])-t))
    print("ASSIGN_NEAR")
    for r in rr[:30]:
        print(json.dumps({k:r.get(k) for k in ("time_s","team","player_id","source_track_id","identity_segment_id","safe","global_margin","ambiguous","evidence_conflict")},sort_keys=True))

    cand=[]
    for r in tracks:
        dt=abs(float(r["time_s"])-t)
        if dt>0.10: continue
        cx=.5*(float(r["x1"])+float(r["x2"])); cy=float(r["y2"])
        d=math.hypot(cx-ex,cy-ey)
        cand.append((d,dt,int(float(r["track_id"])),cx,cy,float(r.get("conf") or 0)))
    cand.sort()
    print("PHYSICAL_NEAR_ORACLE")
    for x in cand[:12]: print(x)

    tids={x[2] for x in cand[:4]}
    relevant=[r for r in obs if int(float(r["source_track_id"])) in tids and abs(float(r["time_s"])-t)<=0.30]
    relevant.sort(key=lambda r:(int(float(r["source_track_id"])),abs(float(r["time_s"])-t)))
    print("OBS_FOR_NEAREST_TRACKS")
    for r in relevant[:80]:
        print(json.dumps({k:r.get(k) for k in ("time_s","source_track_id","identity_segment_id","uniform_cluster","cluster_conf","ambiguous","conf")},sort_keys=True))

    sids={int(float(r["identity_segment_id"])) for r in relevant}
    print("SEGMENTS_FOR_NEAREST_TRACKS")
    for sid in sorted(sids):
        s=next((x for x in segs if int(float(x["segment_id"]))==sid),None)
        print(sid,json.dumps(s,sort_keys=True) if s else None)
