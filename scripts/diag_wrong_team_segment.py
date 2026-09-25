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

# Independent identity evidence for the segment.
ocr=json.load(open(root/"identity_ocr/ocr_evidence.json"))
print("OCR_TOPLEVEL_TYPE",type(ocr).__name__)
print("OCR_SEGMENT16",json.dumps(
    {k:v for k,v in (ocr.items() if isinstance(ocr,dict) else []) if str(k)=="16"},
    sort_keys=True
) if isinstance(ocr,dict) else "not-dict")
try:
    ti=rows(root/"identity_ocr/track_identity.csv")
    print("TRACK_IDENTITY_SEG16",json.dumps([r for r in ti if r.get("identity_segment_id")=="16" or r.get("segment_id")=="16" or r.get("source_track_id")=="1"],indent=2))
except Exception as e:
    print("TRACK_IDENTITY_ERR",repr(e))

for sid in (3,72,80):
    ss=next((r for r in segs if int(float(r["segment_id"]))==sid),None)
    qq=[r for r in obs if int(float(r["identity_segment_id"]))==sid]
    print("ROLE_SEGMENT",sid,
          "SEG",json.dumps(ss,sort_keys=True) if ss else None,
          "CLUSTERS",dict(Counter(r.get("uniform_cluster","") for r in qq)),
          "AMBIG",dict(Counter(r.get("ambiguous","") for r in qq)))
