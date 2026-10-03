#!/usr/bin/env python3
import argparse, json, time
from pathlib import Path
from ortools.sat.python import cp_model


def solve(event, forbid=None):
    forbid=forbid or set()
    m=cp_model.CpModel()
    vs={}
    terms=[]
    actor=int(event["actor_player_id"])
    for i,c in enumerate(event.get("candidates") or []):
        key=f"{c['physical_path_id']}:{c['identity_segment_id']}"
        v=m.NewBoolVar(f"body_{i}")
        vs[key]=v
        if key in forbid:
            m.Add(v==0)
        owners={int(x) for x in (c.get("existing_segment_owner_ids") or [])}
        if owners and owners!={actor}:
            m.Add(v==0)
        else:
            score=int(round(1000*float(c.get("score",0.0))))
            terms.append(score*v)
    u=m.NewBoolVar("unobserved")
    vs["__UNOBSERVED__"]=u
    if "__UNOBSERVED__" in forbid:
        m.Add(u==0)
    m.Add(sum(vs.values())==1)
    if terms:
        m.Maximize(sum(terms))
    s=cp_model.CpSolver()
    s.parameters.num_search_workers=1
    s.parameters.max_time_in_seconds=2
    t=time.perf_counter()
    status=s.Solve(m)
    elapsed=time.perf_counter()-t
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        return {"status":s.StatusName(status),"chosen":None,"objective":None,"elapsed_s":elapsed}
    chosen=next(k for k,v in vs.items() if s.Value(v))
    return {"status":s.StatusName(status),"chosen":chosen,"objective":s.ObjectiveValue(),"elapsed_s":elapsed}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    d=json.loads(Path(a.input).read_text())
    results=[]
    for e in d["events"]:
        base=solve(e)
        alt=solve(e,{base["chosen"]}) if base.get("chosen") else None
        blocked=[]
        actor=int(e["actor_player_id"])
        for c in e.get("candidates") or []:
            owners=sorted({int(x) for x in (c.get("existing_segment_owner_ids") or [])})
            if owners and owners != [actor]:
                blocked.append({
                    "physical_path_id":c["physical_path_id"],
                    "identity_segment_id":c["identity_segment_id"],
                    "existing_segment_owner_ids":owners,
                    "reason":"existing_exact_segment_owner_conflicts_with_event_actor"
                })
        results.append({
            "event_id":e["event_id"],
            "actor_player_id":actor,
            "player_name":e.get("player_name"),
            "base":base,
            "counterfactual":alt,
            "blocked_candidates":blocked,
            "identity_authorizing":False
        })
    out={
        "schema":"courtcoder.public-bounded-cpsat-shadow.v1",
        "backend":"OR_TOOLS_CP_SAT",
        "fixture_id":d["fixture_id"],
        "control_candidate_sha":d["control_candidate_sha"],
        "identity_authorizing":False,
        "results":results
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
