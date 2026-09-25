#!/usr/bin/env python3
import csv,json,sys
from pathlib import Path
from collections import Counter
root=Path(sys.argv[1])
def rows(p):
    with open(p,newline="") as f: return list(csv.DictReader(f))
obs=rows(root/"identity_segments/uniform_observations.csv")
segs=rows(root/"identity_segments/segments.csv")
assign=rows(root/"global_identity/identity_assignments.csv")
links=rows(root/"sam31/continuity_links.csv")
groups=rows(root/"sam31/continuity_groups.csv")
anchors=json.load(open(root/"semantic_anchors.json"))
pid=1641711

print("ANCHORS",json.dumps(anchors,indent=2))
print("ACCEPTED_SAM_LINKS")
for r in links:
    if str(r.get("accepted","")).lower() in {"true","1"}: print(json.dumps(r,sort_keys=True))
print("SAM_GROUPS",json.dumps(groups,indent=2))

for sid in (3,7,8,48,49):
    s=next((r for r in segs if int(float(r["segment_id"]))==sid),None)
    q=[r for r in obs if int(float(r["identity_segment_id"]))==sid]
    print("SEGMENT",sid,json.dumps(s,sort_keys=True) if s else None)
    print("CLUSTERS",dict(Counter(r.get("uniform_cluster","") for r in q)),"AMBIG",dict(Counter(r.get("ambiguous","") for r in q)))

print("DICK_ASSIGNMENTS")
for r in assign:
    if int(float(r.get("player_id") or -1))==pid and 8.5<=float(r["time_s"])<=12.5:
        print(json.dumps({k:r.get(k) for k in ("time_s","source_track_id","identity_segment_id","safe","global_margin","ambiguous","team")},sort_keys=True))

print("TRACK0_3_OBS")
for r in obs:
    if int(float(r["source_track_id"])) in {0,3} and 8.5<=float(r["time_s"])<=12.5:
        print(json.dumps({k:r.get(k) for k in ("time_s","source_track_id","identity_segment_id","uniform_cluster","cluster_conf","ambiguous","conf","x1","y1","x2","y2")},sort_keys=True))


print("TRACK2_3_COMPARISON")
for r in obs:
    if int(float(r["source_track_id"])) in {2,3} and 8.8<=float(r["time_s"])<=12.2:
        print(json.dumps({k:r.get(k) for k in ("time_s","source_track_id","identity_segment_id","uniform_cluster","cluster_conf","ambiguous","conf","x1","y1","x2","y2")},sort_keys=True))

print("TRACK2_3_ASSIGNMENTS")
for r in assign:
    if int(float(r["source_track_id"])) in {2,3} and 8.8<=float(r["time_s"])<=12.2:
        print(json.dumps({k:r.get(k) for k in ("time_s","player_id","source_track_id","identity_segment_id","safe","global_margin","ambiguous","team","evidence_conflict")},sort_keys=True))

print("TRACK2_3_SEGMENTS")
for r in segs:
    if int(float(r.get("source_track_id") or -1)) in {2,3}:
        end=float(r["end_s"]); start=float(r["start_s"])
        if end>=8.8 and start<=12.2:
            print(json.dumps(r,sort_keys=True))


print("TRACK3_OCR_EVIDENCE")
ocrp=root/"identity_ocr/ocr_evidence.json"
if ocrp.exists():
    raw=json.load(open(ocrp))
    for rec in raw:
        try: sid=int(float(rec.get("track_id")))
        except: continue
        if sid in {41,42,43,44,45,46,47,48,49,50}:
            print(json.dumps(rec,sort_keys=True))
print("TRACK3_TRACK_IDENTITY")
tip=root/"identity_ocr/track_identity.csv"
if tip.exists():
    for r in rows(tip):
        try: sid=int(float(r.get("track_id")))
        except: continue
        if sid in {41,42,43,44,45,46,47,48,49,50}:
            print(json.dumps(r,sort_keys=True))
print("TRACK3_ALL_ASSIGNMENTS")
for r in assign:
    if int(float(r["source_track_id"]))==3 and 5.5<=float(r["time_s"])<=14.3:
        print(json.dumps({k:r.get(k) for k in ("time_s","player_id","source_track_id","identity_segment_id","safe","global_margin","ambiguous","team","evidence_conflict")},sort_keys=True))


print("SEGMENT36_IDENTITY_EVIDENCE")
ocrp=root/"identity_ocr/ocr_evidence.json"
if ocrp.exists():
    for rec in json.load(open(ocrp)):
        try: sid=int(float(rec.get("track_id")))
        except: continue
        if sid==36:
            print("OCR36",json.dumps(rec,sort_keys=True))
tip=root/"identity_ocr/track_identity.csv"
if tip.exists():
    for r in rows(tip):
        try: sid=int(float(r.get("track_id")))
        except: continue
        if sid==36:
            print("TRACK_ID36",json.dumps(r,sort_keys=True))
for r in assign:
    if int(float(r.get("identity_segment_id") or -1))==36:
        print("ASSIGN36",json.dumps({k:r.get(k) for k in ("time_s","player_id","player_name","jersey","source_track_id","identity_segment_id","safe","global_margin","ambiguous","team","direct_ocr","jersey_support")},sort_keys=True))


print("DEFENDER_TEMPORAL_GEOMETRY")
import math
bytime={}
for r in obs:
    t=round(float(r["time_s"]),4)
    bytime.setdefault(t,{})[int(float(r["source_track_id"]))]=r
def center(r):
    return ((float(r["x1"])+float(r["x2"]))*0.5,(float(r["y1"])+float(r["y2"]))*0.5)
def h(r): return max(1.0,float(r["y2"])-float(r["y1"]))
for cand in (0,2,3,4,10,12):
    vals=[]
    for t,m in sorted(bytime.items()):
        if 8.9<=t<=9.8 and 5 in m and cand in m:
            a=center(m[5]); b=center(m[cand])
            d=math.hypot(a[0]-b[0],a[1]-b[1])/max(1.0,0.5*(h(m[5])+h(m[cand])))
            vals.append((t,d,str(m[cand].get("ambiguous")),float(m[cand].get("cluster_conf") or 0)))
    if vals:
        ds=[x[1] for x in vals]
        print("CAND",cand,"N",len(vals),"MEAN",round(sum(ds)/len(ds),4),"MIN",round(min(ds),4),"MAX",round(max(ds),4),"SERIES",json.dumps(vals))


print("TRACK0_POSITIVE_PROVENANCE")
track0_segments=sorted({int(float(r["identity_segment_id"])) for r in obs if int(float(r["source_track_id"]))==0})
print("TRACK0_SEGMENT_IDS",track0_segments)
for r in assign:
    if int(float(r["source_track_id"]))==0 and int(float(r.get("player_id") or -1))==pid:
        print("DICK_TRACK0",json.dumps({k:r.get(k) for k in (
            "time_s","player_id","player_name","source_track_id","raw_source_track_id",
            "identity_segment_id","safe","global_margin","ambiguous",
            "positive_identity_evidence","positive_identity_evidence_propagated",
            "semantic_anchor","direct_ocr","jersey_support"
        )},sort_keys=True))
if ocrp.exists():
    for rec in json.load(open(ocrp)):
        try: sid=int(float(rec.get("track_id")))
        except: continue
        if sid in track0_segments:
            print("TRACK0_OCR",json.dumps(rec,sort_keys=True))
if tip.exists():
    for r in rows(tip):
        try: sid=int(float(r.get("track_id")))
        except: continue
        if sid in track0_segments:
            print("TRACK0_IDENTITY_ROW",json.dumps(r,sort_keys=True))
print("TRACK0_SAM_GROUP_ROWS")
for r in groups:
    try: sid=int(float(r.get("identity_segment_id")))
    except: continue
    if sid in track0_segments:
        print(json.dumps(r,sort_keys=True))
