#!/usr/bin/env python3
"""Scale already-validated 14-game official NBA PBP and provider ON/OFF to 28.

SOURCE RULE: official game-scoped NBA lineup/ONOFF POSS and ratings are NBA
provider observations, NEVER reconstructed Game Pulse full possession chains.
The 14-game baseline remains immutable. Fail closed on missing/ambiguous sources.
All results publish ONLY in private 104.
"""
from __future__ import annotations
import argparse,base64,datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path

REPO="timeedmonds-maker/104"
SCHEMA="gamepulse.official-nba-onoff-tracking-reconciled.v1"
PREFIX="gamepulse/fusion"
FORMAL="gamepulse.formal-nba-pbp-event-clock.v1"
OFFICIAL_INDEX="gamepulse/fusion/onoff/index.json"
NEW_GAMES=["0022600006","0022600007","0022600008","0022600009",
"0022600094","0022600095","0022600096","0022600097","0022600098",
"0022600099","0022600100","0022600101","0022600102","0022600103"]

def command(*args,inp=None,allow_not_found=False):
    p=subprocess.run(["gh","api",*args],input=inp,text=True,capture_output=True,timeout=140)
    if p.returncode:
        if allow_not_found and ('404' in p.stderr or 'Not Found' in p.stderr):
            return None
        raise RuntimeError("PRIVATE_GITHUB_API_"+str(p.returncode))
    return json.loads(p.stdout)

def private_bytes(path,optional=False):
    r=command(f"repos/{REPO}/contents/{path}?ref=main",allow_not_found=optional)
    return base64.b64decode(r["content"]) if r is not None else None

def private_json(path,optional=False):
    s=private_bytes(path,optional)
    return json.loads(s) if s is not None else None

def put(path,blob):
    assert isinstance(blob,bytes) and len(blob)<980000, "PRIVATE_INDEX_SIZE_CAP"
    ep=f"repos/{REPO}/contents/{path}"
    for attempt in range(5):
        r=command(ep,allow_not_found=True)
        data={"branch":"main","message":"data(gamepulse): validate original NBA PBP and independent native ONOFF with private QA",
              "content":base64.b64encode(blob).decode("ascii")}
        if r is not None:
            if base64.b64decode(r["content"])==blob:return "ALREADY_PRESENT"
            data["sha"]=r["sha"]
        try:
            written=command("-X","PUT",ep,"--input","-",inp=json.dumps(data))
            break
        except RuntimeError:
            if attempt==4:raise
            time.sleep(attempt+1)
    readback=None
    for attempt in range(6):
        try:
            readback=private_bytes(path)
            if readback is not None:break
        except RuntimeError:
            if attempt==5:raise
        time.sleep(1+attempt)
    if hashlib.sha256(readback).digest()!=hashlib.sha256(blob).digest():
        raise RuntimeError("PRIVATE_SHA_READBACK_FAILED")
    return "VERIFIED_PRIVATE_SHA"

def save_json(path,data):
    return put(path,(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(",",":"))+"\n").encode())

def load_code(root):
    for name in ("validate_official_onoff_2026.py","official_pbp_timestamps_2026.py","official_pbp_allgames_2026.py"):
        raw=private_bytes(f"{PREFIX}/{name}")
        assert raw and b"from __future__" in raw, "CANONICAL_VALIDATOR_MISSING"
        (root/name).write_bytes(raw)
    sys.path.insert(0,str(root))

def validate_one(gid,root):
    assert gid in NEW_GAMES
    source=private_json(f"{PREFIX}/index/games/{gid}.json")
    assert source["game"]["game_id"]==gid and source["game"]["tracking_frames"]>0
    load_code(root)
    from validate_official_onoff_2026 import validate_game
    from official_pbp_allgames_2026 import certify_game
    summary={"game_id":gid,"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "native_possession_chain_certified":False,
             "nba_provider_onoff_certified":False,"formal_pbp_certified":False,
             "source_scope":"NBA official game-scoped lineup rating and PBP score/clock; no inferred tracking possessions"}
    failed=False
    try:
        for attempt in range(3):
            qa,details=validate_game(source)
            teams=list(qa.get("teams",{}).values())
            if (qa.get("official_lineup_rows",0)>0 and qa.get("player_onoff_verified",0)>0
                and all(t.get("official_single_game_scope_verified") and t.get("official_full_game_lineup_time_covered")
                        and t.get("onoff_conflicts")==0 for t in teams) and len(teams)==2):break
            if attempt<2:time.sleep(3+attempt)
        summary["onoff_source_qa"]={team:{k:meta.get(k) for k in (
            "official_5man","onoff_verified_players","official_single_game_scope_verified",
            "official_full_game_lineup_time_covered","onoff_conflicts","lineup_error","onoff_error")}
            for team,meta in qa.get("teams",{}).items()}
        ok=(qa.get("official_lineup_rows",0)>0 and qa.get("player_onoff_verified",0)>0
          and not qa.get("player_onoff_conflicts")
          and all(t.get("official_single_game_scope_verified") is True
              and t.get("official_full_game_lineup_time_covered") is True
              and t.get("onoff_conflicts")==0
              for t in qa.get("teams",{}).values())
          and len(qa.get("teams",{}))==2)
        if not ok:raise ValueError("INDEPENDENT_NBA_GAME_SCOPED_ONOFF_QA_INCOMPLETE")
        rows=details["lineup_compared"]
        players=details["players_onoff"]
        output={"schema":SCHEMA,"game_id":gid,"source_qa":qa,
             "official_lineups":rows,"player_onoff":players,
             "verified_player_onoff":qa["player_onoff_verified"],
             "matched_qualified_tracking_lineups":qa["matched_official_lineups"],
             "official_possession_values_available":sum(x["official_possessions"] is not None for x in rows),
             "sampled_tracking_shots_are_not_all_fga":True,
             "provider_possessions_are_not_gamepulse_tracking_possessions":True}
        save_json(f"{PREFIX}/onoff/games/{gid}.json",output)
        summary.update(nba_provider_onoff_certified=True,
          official_lineups=len(rows),verified_players=len(players),
          nba_provider_ppp_lineups=sum(x.get("nba_offensive_ppp") is not None for x in rows))
    except Exception as exc:
        failed=True
        summary["onoff_issue"]=type(exc).__name__+":"+str(exc)[:110]
    try:
        game=source["game"]
        pbp=certify_game(gid,[game["away"],game["home"]])
        assert pbp["schema"]==FORMAL and pbp["qa"]["nba_score_reconciled_to_boxscore"] is True
        assert len(pbp["actions"])>=300
        save_json(f"{PREFIX}/official_pbp_timing/games/{gid}.json",pbp)
        summary.update(formal_pbp_certified=True,formal_nba_actions=len(pbp["actions"]))
    except Exception as exc:
        failed=True
        summary["pbp_issue"]=type(exc).__name__+":"+str(exc)[:110]
    save_json(f"{PREFIX}/native_28_qa/games/{gid}.json",summary)
    print("PRIVATE_ORIGINAL_NBA_SOURCE_QA",json.dumps({k:v for k,v in summary.items() if k not in ("onoff_issue","pbp_issue")}))
    if failed:raise RuntimeError("NATIVE_NBA_SOURCE_INCOMPLETE_PRESERVED_BASELINE")

def assemble():
    original=private_json(OFFICIAL_INDEX)
    old=private_json("gamepulse/fusion/official_pbp_timing/index.json")
    fusion=private_json("gamepulse/fusion/index/index.json")
    if len(fusion["games"])>28:
        # Frozen 28-game acceptance must never downgrade a separately certified
        # larger season event index or erase added game coverage.
        print("FROZEN_28_ASSEMBLY_SKIPPED_NEWER_SEASON_INDEX_PRESERVED",len(fusion["games"]))
        return
    assert len(fusion["games"])==28
    assert original["schema"]==SCHEMA and old["source_game_count"]==14
    merged=dict(original["games"])
    manifest=dict(old["games"])
    outstanding={}
    for gid in NEW_GAMES:
        report=private_json(f"{PREFIX}/native_28_qa/games/{gid}.json",True)
        reasons=[]
        if not report or not report.get("formal_pbp_certified"):
            reasons.append("OFFICIAL_NBA_PBP_NOT_VERIFIED")
        else:
            events=private_json(f"{PREFIX}/official_pbp_timing/games/{gid}.json",True)
            if (not events or events.get("schema")!=FORMAL or events.get("game_id")!=gid
                or len(events.get("actions",[]))<300
                or events.get("qa",{}).get("nba_score_reconciled_to_boxscore") is not True):
                reasons.append("OFFICIAL_NBA_PBP_QA_FAILED")
            else:
                manifest[gid]={"game_id":gid,"state":events["state"],
                  "action_records":len(events["actions"]),
                  "source_file":f"{PREFIX}/official_pbp_timing/games/{gid}.json",
                  "source_pbp_sha256":events["source_provenance"]["nba_pbp_sha256"],
                  "official_final":events["official_final"],"video_pts_certified":0}
        if not report or not report.get("nba_provider_onoff_certified"):
            reasons.append("NBA_GAME_SCOPED_ONOFF_NOT_VERIFIED")
        else:
            doc=private_json(f"{PREFIX}/onoff/games/{gid}.json",True)
            if (not doc or doc.get("schema")!=SCHEMA or doc.get("game_id")!=gid
                or doc.get("verified_player_onoff",0)<=0
                or doc.get("official_possession_values_available",0)<=0):
                reasons.append("NBA_PROVIDER_ONOFF_FILE_QA_FAILED")
            else:
                raw=private_bytes(f"{PREFIX}/onoff/games/{gid}.json")
                merged[gid]={"path":f"{PREFIX}/onoff/games/{gid}.json",
                    "sha256":hashlib.sha256(raw).hexdigest(),
                    "official_fives":len(doc["official_lineups"]),
                    "matched_tracking_fives":doc["matched_qualified_tracking_lineups"],
                    "player_onoff_verified":doc["verified_player_onoff"],
                    "official_possession_rows":doc["official_possession_values_available"],
                    "nba_provider_ppp_fives":report.get("nba_provider_ppp_lineups",0)}
        if reasons:
            outstanding[gid]={"reasons":reasons,
                "provider_source_qa":(report or {}).get("onoff_source_qa",{})}
    full_timing=set(manifest)==set(fusion["games"])
    full_onoff=set(merged)==set(fusion["games"])
    # Publish the verified official game-clock material independently, even if
    # a distinct NBA advanced-stats endpoint is temporarily missing data.
    event_index={"schema":"gamepulse.formal-nba-official-event-clock-28game.v1",
        "source_frozen_original_14":"gamepulse/fusion/official_pbp_timing/index.json",
        "game_count":len(manifest),"complete_28":full_timing,
        "games":manifest,"possession_boundary_time_certified":False,
        "shot_release_video_sync_certified":False}
    save_json(f"{PREFIX}/official_pbp_timing/index-2026-27-expanded.json",event_index)
    # Keep the original 14-game ON/OFF index and all original result files intact.
    onoff_index={"schema":SCHEMA,"source_frozen_original_14":OFFICIAL_INDEX,
        "game_count":len(merged),"complete_28":full_onoff,
        "source_policy":"NBA provider lineup possessions/efficiencies and independently verified ONOFF; never frame-derived PPP",
        "native_possession_chain_certified":False,"games":merged}
    save_json(f"{PREFIX}/onoff/index-2026-27-expanded.json",onoff_index)
    status={"schema":"gamepulse.native-official-28game-integration-qa.v1",
        "checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "fusion_game_count":len(fusion["games"]),
        "provider_onoff_games":len(merged),"nba_formal_pbp_games":len(manifest),
        "missing_new_games":outstanding,
        "native_gamepulse_possessions_certified":0,
        "provider_rating_ppp_not_native_event_chain":True,
        "all_28_verified":full_onoff and full_timing}
    save_json(f"{PREFIX}/native_28_qa/season_status.json",status)
    print("NBA_ORIGINAL_SOURCE_PRIVATE_INDEX_QA",json.dumps({
        "official_event_games":len(manifest),"provider_onoff_games":len(merged),
        "full_pbp":full_timing,"full_onoff":full_onoff,"outstanding":sorted(outstanding)}))
    if not status["all_28_verified"]:
        raise RuntimeError("NBA_PROVIDER_ONOFF_STILL_INCOMPLETE_PRESERVED_VERIFIED_PARTIAL_INDEX")
    print("OFFICIAL_NBA_PBP_AND_ONOFF_28GAME_PRIVATE_SEARCH_VERIFIED")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("operation",choices=["one","assemble"])
    p.add_argument("--game")
    a=p.parse_args()
    if a.operation=="one":
        assert a.game in NEW_GAMES
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as t:validate_one(a.game,Path(t))
    else:assemble()
if __name__=="__main__":main()
