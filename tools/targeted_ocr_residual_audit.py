#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    d=json.loads(Path(a.input).read_text())
    rows=[]
    for p in d["paths"]:
        runs=p.get("strict_residual_runs") or []
        strong=[r for r in runs if r.get("dual_exact_ten_all_samples")]
        support=sum(int(r.get("support_samples",0)) for r in runs)
        strong_support=sum(int(r.get("support_samples",0)) for r in strong)
        rows.append({
            "physical_path_id":p["physical_path_id"],
            "unresolved_rows":int(p["unresolved_rows"]),
            "research_hypothesis_jersey":p.get("research_hypothesis_jersey"),
            "strict_residual_run_count":len(runs),
            "strict_residual_support_samples":support,
            "dual_exact_ten_all_run_count":len(strong),
            "dual_exact_ten_all_support_samples":strong_support,
            "independent_crop_truth_ready":d["independent_crop_truth_status"]=="READY",
            "ocr_authorization_ready":False,
            "next_action":"INDEPENDENT_CROP_TRUTH_AND_SPECIALIST_OCR_COMPARISON",
        })
    rows.sort(key=lambda x:(-x["unresolved_rows"],-x["strict_residual_support_samples"]))
    out={
        "schema":"courtcoder.public-targeted-ocr-opportunity-result.v1",
        "fixture_id":d["fixture_id"],
        "control_candidate_sha":d["control_candidate_sha"],
        "identity_authorizing":False,
        "candidate_path_count":len(rows),
        "unique_unresolved_rows_in_scope":sum(x["unresolved_rows"] for x in rows),
        "independent_crop_truth_status":d["independent_crop_truth_status"],
        "promotion_blocked_until_independent_crop_truth":d["independent_crop_truth_status"]!="READY",
        "paths":rows,
        "interpretation":"These rows are an OCR opportunity upper bound, not recoverable coverage. Research jersey hypotheses and residual exact-five evidence cannot authorize identity.",
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
      "candidate_path_count":out["candidate_path_count"],
      "unique_unresolved_rows_in_scope":out["unique_unresolved_rows_in_scope"],
      "promotion_blocked_until_independent_crop_truth":out["promotion_blocked_until_independent_crop_truth"],
    },sort_keys=True))
if __name__=="__main__": main()
