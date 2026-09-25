#!/usr/bin/env python3
import csv, json, sys
from collections import Counter
from pathlib import Path

root=Path(sys.argv[1])
seg_id=16
pid=1642263

def rows(p):
    with open(p,newline="") as f:
        return list(csv.DictReader(f))

obs=rows(root/"identity_segments/uniform_observations.csv")
segs=rows(root/"identity_segments/segments.csv")
roster=json.load(open(root/"exact_lineup_roster.json"))
players=[p for t in roster["teams"].values() for p in t["players"]]
player=next((p for p in players if int(p["id"])==pid),None)
print("PLAYER",json.dumps(player,sort_keys=True))
s=next(r for r in segs if int(float(r["segment_id"]))==seg_id)
print("SEGMENT",json.dumps(s,sort_keys=True))
q=[r for r in obs if int(float(r["identity_segment_id"]))==seg_id]
print("OBS_ROWS",len(q))
print("OBS_CLUSTER_COUNTS",dict(Counter(r.get("uniform_cluster","") for r in q)))
print("OBS_CLUSTER_CONF_MINMAX",
      min(float(r["cluster_conf"]) for r in q),
      max(float(r["cluster_conf"]) for r in q))
print("OBS_AMBIG_COUNTS",dict(Counter(r.get("ambiguous","") for r in q)))
for r in q[:40]:
    print("OBS",json.dumps({k:r.get(k) for k in ("time_s","source_track_id","raw_source_track_id","uniform_cluster","cluster_conf","ambiguous","conf")},sort_keys=True))
