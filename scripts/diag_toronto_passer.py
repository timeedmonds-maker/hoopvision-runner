#!/usr/bin/env python3
from __future__ import annotations
import csv, json, sys
from collections import Counter, defaultdict
from pathlib import Path

root=Path(sys.argv[1])

def rows(p):
    with open(p,newline="") as f:
        return list(csv.DictReader(f))

obs=rows(root/"identity_segments/uniform_observations.csv")
assoc=rows(root/"semantic_anchors.associations.csv")
cfg=json.load(open(root/"base_config.json"))
qa=json.load(open(root/"identity_ocr/qa.json"))
print("OCR_QA",json.dumps(qa,sort_keys=True))
print("CONFIG_OFFENSE",cfg["event"].get("offense_team"),"CATCH",cfg["timing"].get("catch_s"),"ACTION",cfg.get("action"))
print("ASSOC_MAPPED_TEAM_COUNTS",dict(Counter(r.get("mapped_team","") for r in assoc)))
print("OBS_COLUMNS",list(obs[0]) if obs else [])
print("ASSOC_COLUMNS",list(assoc[0]) if assoc else [])

catch=float(cfg["timing"]["catch_s"])
elapsed=float((cfg.get("action") or {}).get("oreb_to_make_s",3.0))
offense=cfg["event"]["offense_team"]
W={1:1.8,5:.28,6:2.1,7:1.2}
STRONG={1,6,7}

def votes(group_rows):
    by=defaultdict(list)
    for r in group_rows:
        by[int(r["source_track_id"])].append(r)
    out=[]
    for tid,g in by.items():
        w=sw=0.0; strong=[]
        for r in g:
            cid=int(r["det_class"])
            base=max(0.0,float(r["association_score"]))
            amb=str(r.get("ambiguous","")).lower() in {"true","1"}
            z=base*W.get(cid,0.0)*(.35 if amb else 1.0)
            w+=z
            if cid in STRONG:
                sw+=z; strong.append(float(r["time_s"]))
        out.append({
            "tid":tid,"weight":w,"strong_weight":sw,"samples":len(g),"strong_samples":len(strong),
            "strong_start":min(strong) if strong else None,"strong_end":max(strong) if strong else None,
            "start":min(float(r["time_s"]) for r in g),"end":max(float(r["time_s"]) for r in g),
            "classes":dict(Counter(int(r["det_class"]) for r in g)),
        })
    return sorted(out,key=lambda x:(x["weight"],x["strong_weight"],x["samples"]),reverse=True)

sq=[r for r in assoc if r.get("mapped_team")==offense and catch-.70<=float(r["time_s"])<=catch+.45]
shoot=votes(sq)
print("SHOOTER_VOTES",json.dumps(shoot[:8],indent=2))
if not shoot:
    raise SystemExit
sv=shoot[0]
prior=[r for r in assoc if r.get("mapped_team")==offense and float(r["time_s"])<catch-.05 and int(r["source_track_id"])!=sv["tid"]]
pv=[]
for v in votes(prior):
    g=[r for r in prior if int(r["source_track_id"])==v["tid"]]
    weak=max(0.0,v["weight"]-v["strong_weight"])
    rec=max(0.0,1.0-(catch-max(float(r["time_s"]) for r in g))/max(1.0,elapsed+1.0))
    v.update(role_score=v["strong_weight"]+min(.60,.12*weak)+.35*rec,recency=rec)
    pv.append(v)
earlier=[v for v in pv if v["strong_end"] is not None and v["strong_end"]<=sv["strong_start"]-.08]
earlier=sorted(earlier,key=lambda x:(x["role_score"],x["strong_weight"],x["strong_end"]),reverse=True)
print("PASSER_VOTES_EARLIER",json.dumps(earlier[:10],indent=2))
if not earlier:
    raise SystemExit
best=earlier[0]
tid=best["tid"]; target=best["end"]
track=[r for r in obs if int(float(r["source_track_id"]))==tid]
print("PASSER_TRACK_ID",tid,"TARGET_TIME",target,"ROWS",len(track))
near=[]
for r in track:
    t=float(r["time_s"]); dt=abs(t-target)
    if dt<=1.0:
        near.append({
            "time_s":t,"dt":dt,"uniform_cluster":r.get("uniform_cluster"),
            "cluster_conf":r.get("cluster_conf"),"ambiguous":r.get("ambiguous"),"conf":r.get("conf"),
            "identity_segment_id":r.get("identity_segment_id"),"raw_source_track_id":r.get("raw_source_track_id"),
        })
print("PASSER_NEAR_ROWS",json.dumps(sorted(near,key=lambda x:(x["dt"],x["time_s"]))[:40],indent=2))
print("PASSER_TRACK_CLUSTER_COUNTS",dict(Counter(r.get("uniform_cluster","") for r in track)))
print("PASSER_TRACK_AMBIG_COUNTS",dict(Counter(r.get("ambiguous","") for r in track)))
vals=[float(r["cluster_conf"]) for r in track if r.get("cluster_conf") not in (None,"")]
print("PASSER_TRACK_CLUSTER_CONF_RANGE",min(vals) if vals else None,max(vals) if vals else None)
