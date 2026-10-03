#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def classify(e):
    actor=int(e["actor_player_id"])
    owners={int(x) for x in (e.get("event_time_owner_ids") or [])}
    dup=[x for x in (e.get("simultaneous_same_player_other_paths") or []) if int(x.get("player_id",-1))==actor]
    accepted=bool(e.get("accepted_anchor",False))
    rows=int((e.get("rank1") or {}).get("unresolved_rows",0) or 0)

    if not accepted:
        status="EVENT_NOT_ACCEPTED"
        new_rows=0
    elif owners:
        if owners=={actor}:
            status="CORROBORATES_EXISTING_OWNER"
        else:
            status="BLOCKED_DIFFERENT_EVENT_TIME_OWNER"
        new_rows=0
    elif dup:
        status="BLOCKED_SIMULTANEOUS_DUPLICATE_IDENTITY"
        new_rows=0
    else:
        status="SAFE_NEW_ROOT_CANDIDATE_SHADOW_ONLY"
        new_rows=rows

    return {
        **e,
        "screening_status":status,
        "safe_new_root_candidate":status=="SAFE_NEW_ROOT_CANDIDATE_SHADOW_ONLY",
        "unique_unknown_rows_recoverable_if_independently_certified":new_rows,
        "identity_authorizing":False,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    doc=json.loads(Path(a.input).read_text())
    rows=[classify(e) for e in doc["events"]]
    safe=[r for r in rows if r["safe_new_root_candidate"]]
    recovered=sum(int(r["unique_unknown_rows_recoverable_if_independently_certified"]) for r in safe)
    gate=doc["screening_gate"]
    out={
        "schema":"courtcoder.public-root-recovery-gate-b-result.v1",
        "fixture_id":doc["fixture_id"],
        "control_candidate_sha":doc["control_candidate_sha"],
        "retained_diagnostic_sha":doc["retained_diagnostic_sha"],
        "identity_authorizing":False,
        "safe_new_root_groups":len(safe),
        "safe_unique_unknown_rows_recoverable":recovered,
        "screening_gate":{
            **gate,
            "root_group_gate_pass":len(safe)>=int(gate["required_new_root_groups"]),
            "unique_row_gate_pass":recovered>=int(gate["required_unique_rows"]),
            "duplicate_conflict_gate_pass":all(
                r["screening_status"]!="BLOCKED_SIMULTANEOUS_DUPLICATE_IDENTITY" for r in safe
            ),
            "pass":len(safe)>=int(gate["required_new_root_groups"]) and recovered>=int(gate["required_unique_rows"]),
        },
        "events":rows,
        "interpretation":"No event root is promoted; this is a shadow screening result only.",
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "safe_new_root_groups":out["safe_new_root_groups"],
        "safe_unique_unknown_rows_recoverable":out["safe_unique_unknown_rows_recoverable"],
        "screening_gate_pass":out["screening_gate"]["pass"],
        "statuses":[[r["event_id"],r["screening_status"]] for r in rows],
    },sort_keys=True))

if __name__=="__main__":
    main()
