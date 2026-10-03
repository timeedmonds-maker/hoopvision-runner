#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from ortools.sat.python import cp_model

UNOBSERVED="__UNOBSERVED__"

def solve_packet(doc, forbid=None):
    forbid=set(forbid or [])
    m=cp_model.CpModel()
    event_vars={}
    objective=[]
    chosen_meta={}
    hard_owner_forced=[]
    for e in doc["events"]:
        eid=e["event_id"]
        actor=int(e["actor_player_id"])
        vars_for_event={}
        candidate_by_token={}
        for i,c in enumerate(e.get("candidates") or []):
            token=str(c["token"])
            candidate_by_token[token]=c
            v=m.NewBoolVar(f"e_{len(event_vars)}_{i}")
            vars_for_event[token]=v
            event_vars[(eid,token)]=v
            owners={int(x) for x in c.get("existing_segment_owner_ids") or []}
            if owners and actor not in owners:
                m.Add(v==0)
            score=int(round(1000*float(c.get("score",0.0) or 0.0)))
            if score:
                objective.append(score*v)
        u=m.NewBoolVar(f"e_{len(event_vars)}_unobserved")
        vars_for_event[UNOBSERVED]=u
        event_vars[(eid,UNOBSERVED)]=u
        m.Add(sum(vars_for_event.values())==1)

        hard_token=str(e.get("hard_actor_owner_token") or "")
        if hard_token:
            if hard_token not in vars_for_event:
                raise RuntimeError(f"{eid}: hard_actor_owner_token missing from candidate set: {hard_token}")
            # Independent exact owner at the event timestamp is hard retained evidence.
            # The shadow solve therefore cannot assign the named actor to a second body.
            m.Add(vars_for_event[hard_token]==1)
            hard_owner_forced.append({"event_id":eid,"token":hard_token})

        for feid,ftoken in forbid:
            if feid==eid and ftoken in vars_for_event:
                m.Add(vars_for_event[ftoken]==0)

    # Chain constraints: same named actor in tightly linked events must map to the same
    # body token whenever both events have a common observed token. This is shadow-only.
    for chain in doc.get("action_chains") or []:
        for group in chain.get("same_actor_body_groups") or []:
            if len(group)<2: continue
            common=None
            for eid in group:
                toks={tok for (ee,tok) in event_vars if ee==eid and tok!=UNOBSERVED}
                common=toks if common is None else common & toks
            if not common:
                continue
            for token in common:
                base=event_vars[(group[0],token)]
                for eid in group[1:]:
                    m.Add(base==event_vars[(eid,token)])

    if objective:
        m.Maximize(sum(objective))

    s=cp_model.CpSolver()
    s.parameters.num_search_workers=1
    s.parameters.max_time_in_seconds=2
    t=time.perf_counter()
    st=s.Solve(m)
    elapsed=time.perf_counter()-t
    status=s.StatusName(st)
    if st not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        return {"status":status,"elapsed_s":elapsed,"events":[],"objective":None}

    results=[]
    for e in doc["events"]:
        eid=e["event_id"]
        chosen=UNOBSERVED
        for c in e.get("candidates") or []:
            token=str(c["token"])
            if s.Value(event_vars[(eid,token)]):
                chosen=token
                break
        if chosen==UNOBSERVED and not s.Value(event_vars[(eid,UNOBSERVED)]):
            raise RuntimeError(f"{eid}: no chosen assignment")
        generated=set(str(x) for x in e.get("event_generator_candidate_tokens") or [])
        hard=str(e.get("hard_actor_owner_token") or "")
        results.append({
            "event_id":eid,
            "actor_player_id":int(e["actor_player_id"]),
            "player_name":e.get("player_name"),
            "chosen":chosen,
            "hard_actor_owner_token":hard or None,
            "hard_owner_was_event_generator_candidate":bool(hard and hard in generated),
            "event_generator_top_rank_token":next((str(c["token"]) for c in sorted(e.get("candidates") or [],key=lambda x:int(x.get("rank",999))) if str(c["token"]) in generated),None),
            "identity_authorizing":False,
        })
    return {
        "status":status,
        "elapsed_s":elapsed,
        "objective":s.ObjectiveValue() if objective else 0.0,
        "events":results,
        "hard_owner_forced":hard_owner_forced,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    doc=json.loads(Path(a.input).read_text())
    base=solve_packet(doc)
    counterfactuals=[]
    for er in base.get("events") or []:
        tok=er.get("chosen")
        if tok:
            alt=solve_packet(doc,{(er["event_id"],tok)})
            counterfactuals.append({
                "event_id":er["event_id"],
                "forbidden_choice":tok,
                "alternative_status":alt["status"],
                "alternative_events":alt.get("events") or [],
            })
    diagnostics=[]
    for er in base.get("events") or []:
        if er.get("hard_actor_owner_token"):
            if er["hard_owner_was_event_generator_candidate"]:
                diagnostics.append({
                    "event_id":er["event_id"],
                    "finding":"event_generator_included_independent_exact_owner",
                    "top_rank_was_correct_owner":er.get("event_generator_top_rank_token")==er.get("hard_actor_owner_token"),
                })
            else:
                diagnostics.append({
                    "event_id":er["event_id"],
                    "finding":"event_generator_omitted_independent_exact_owner",
                    "top_rank_was_correct_owner":False,
                })
    out={
        "schema":"courtcoder.public-bounded-event-chain-cpsat-shadow.v1",
        "backend":"OR_TOOLS_CP_SAT",
        "fixture_id":doc["fixture_id"],
        "control_candidate_sha":doc["control_candidate_sha"],
        "identity_authorizing":False,
        "solve":base,
        "counterfactuals":counterfactuals,
        "candidate_generation_diagnostics":diagnostics,
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
