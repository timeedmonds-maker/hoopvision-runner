#!/usr/bin/env python3
import csv,json,math,sys
from pathlib import Path
root=Path(sys.argv[1])

def rows(p):
    with open(p,newline="") as f:return list(csv.DictReader(f))
obs=rows(root/"identity_segments/uniform_observations.csv")
anchors=json.load(open(root/"semantic_anchors.json"))
cfg=json.load(open(root/"base_config.json"))
shid=anchors["qa"]["shooter_segment_id"]
shrows=[r for r in obs if int(float(r["identity_segment_id"]))==int(shid)]
# use exact row nearest catch, mirroring current anchor resolution
catch=float(cfg["timing"]["catch_s"])
sr=min(shrows,key=lambda r:abs(float(r["time_s"])-catch))
frame=int(float(sr["source_frame"]))
sx1,sy1,sx2,sy2=[float(sr[k]) for k in ("x1","y1","x2","y2")]
sw=max(1.,sx2-sx1); sh=max(1.,sy2-sy1)
scx=.5*(sx1+sx2); scy=.5*(sy1+sy2)

def dist(r):
    cx=.5*(float(r["x1"])+float(r["x2"])); cy=.5*(float(r["y1"])+float(r["y2"]))
    return math.hypot((cx-scx)/sw,(cy-scy)/sh)

q=[r for r in obs if int(float(r["source_frame"]))==frame and str(r.get("ambiguous","")).lower() not in {"true","1"}]
q.sort(key=dist)
print("CATCH",catch,"SHOOTER_SEGMENT",shid,"SHOOTER_TRACK",sr["source_track_id"],"FRAME",frame,"TIME",sr["time_s"])
print("ALL_CLEAR_CANDIDATES_GEOMETRY_ORDER")
for r in q:
    print(json.dumps({
      "source_track_id":int(float(r["source_track_id"])),
      "identity_segment_id":int(float(r["identity_segment_id"])),
      "uniform_cluster":r.get("uniform_cluster"),
      "cluster_conf":float(r.get("cluster_conf") or 0),
      "mapped_team":r.get("mapped_team"),
      "distance":dist(r),
      "box":[float(r[k]) for k in ("x1","y1","x2","y2")]
    },sort_keys=True))
