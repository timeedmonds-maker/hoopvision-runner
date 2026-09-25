#!/usr/bin/env python3
import csv,json,sys
from pathlib import Path
root=Path(sys.argv[1])
def rows(p):
    with open(p,newline="") as f:return list(csv.DictReader(f))
links=rows(root/"sam31/continuity_links.csv")
plan=json.load(open(root/"sam31/sam31_plan.json"))
segs=rows(root/"identity_segments/segments.csv")
seg_by={int(float(r["segment_id"])):r for r in segs}
watch={2,3,4,5,6,7,8,45,46,47,48,49}
print("LINKS_INVOLVING_WATCH")
for r in links:
    a=int(float(r.get("from_segment_id") or -1)); b=int(float(r.get("to_segment_id") or -1))
    if a in watch or b in watch:
        print(json.dumps(r,sort_keys=True))
print("PLAN_INVOLVING_WATCH")
jobs=plan if isinstance(plan,list) else (plan.get("jobs") or plan.get("plan") or plan.get("windows") or [])
for j in jobs:
    vals=set()
    for k in ("from_segment_id","to_segment_id","source_segment_id","target_segment_id"):
        if j.get(k) is not None:
            try: vals.add(int(j[k]))
            except: pass
    for x in j.get("candidate_segment_ids") or []:
        try: vals.add(int(x))
        except: pass
    if vals & watch:
        print(json.dumps(j,sort_keys=True))
print("WATCH_SEGMENTS")
for sid in sorted(watch):
    if sid in seg_by: print(sid,json.dumps(seg_by[sid],sort_keys=True))
