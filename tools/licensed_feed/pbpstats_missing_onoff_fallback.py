#!/usr/bin/env python3
"""Independently audit full-game PBPStats lineup possessions for NBA ONOFF gaps.

Never backfill Game Pulse possessions from tracking frames. Never claim a
single-game response unless every 5-man row is game-scoped, full-game seconds
and points reconcile to original NBA final. Preserve failures in private QA.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,os,subprocess,sys,tempfile,time
import urllib.request,urllib.parse
from pathlib import Path

REPO="timeedmonds-maker/104"
MISSING=("0022600009","0022600099","0022600103")

def gh(*args,input=None,optional=False):
    p=subprocess.run(["gh","api",*args],input=input,text=True,capture_output=True,timeout=100)
    if p.returncode:
        if optional and ("404" in p.stderr or "Not Found" in p.stderr):return None
        raise RuntimeError("PRIVATE_GITHUB_QUERY_FAILED")
    return json.loads(p.stdout)

def data(path,optional=False):
    x=gh(f"repos/{REPO}/contents/{path}?ref=main",optional=optional)
    return base64.b64decode(x["content"]) if x else None

def save(path,record):
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
    if len(raw)>=950000:raise ValueError("PRIVATE_GAME_RESULT_SIZE_LIMIT")
    ep=f"repos/{REPO}/contents/{path}"
    for attempt in range(4):
        old=gh(ep,optional=True)
        if old and data(path)==raw:return
        pay={"branch":"main","message":"qa(gamepulse): independently audit single-game PBPStats five-man possessions",
             "content":base64.b64encode(raw).decode()}
        if old:pay["sha"]=old["sha"]
        try:
            gh("-X","PUT",ep,"--input","-",input=json.dumps(pay));break
        except RuntimeError:
            if attempt==3:raise
            time.sleep(1+attempt)
    for attempt in range(6):
        try:
            if data(path)==raw:return
        except RuntimeError:
            if attempt==5:raise
        time.sleep(attempt+1)
    raise RuntimeError("PRIVATE_SOURCE_SHA_READBACK_FAILED")

def run(gid):
    if gid not in MISSING:raise ValueError("unreviewed_game")
    # Only NBA original final and private indexed player identities may authorize.
    raw=data(f"data/extensions/nba_blueprint_2026_27/games/{gid}/blueprint_report_raw.json")
    report=json.loads(raw)
    view=json.loads(data(f"gamepulse/fusion/index/games/{gid}.json"))
    assert str(report["game_header"]["gameId"])==gid and report["game_header"]["gameStatus"]==3
    assert view["game_id"]==gid
    query=urllib.parse.urlencode({"GameId":gid,"Type":"Lineup"})
    url="https://api.pbpstats.com/get-game-stats?"+query
    summary={"schema":"gamepulse.pbpstats-independent-game-lineups-source-audit.v1","game_id":gid,
             "source_endpoint":"PBPStats get-game-stats with GameId and Type=Lineup",
             "native_gamepulse_possessions_certified":False,"source_validated":False}
    try:
        req=urllib.request.Request(url,headers={"Accept":"application/json",
              "Origin":"https://www.pbpstats.com","Referer":"https://www.pbpstats.com/",
              "User-Agent":"Mozilla/5.0 Chrome/131 Safari/537.36"})
        with urllib.request.urlopen(req,timeout=26) as resp:
            if resp.status!=200:raise RuntimeError("PBPSTATS_STATUS_NOT_200")
            blob=resp.read(2800000)
        if len(blob)>2600000:raise ValueError("PBPSTATS_SIZE_LIMIT")
        body=json.loads(blob)
        summary["source_sha256"]=hashlib.sha256(blob).hexdigest()
        summary["source_fields"]=sorted(body)[:30]
        rows=next((body.get(k) for k in ("multi_row_table_data","game_stats","rows","data")
                   if isinstance(body.get(k),list)),None)
        summary["rows_received"]=len(rows) if rows is not None else 0
        if not rows:raise ValueError("PBPSTATS_NO_SINGLE_GAME_LINEUP_ROWS")
        # Parse existing canonical source rules rather than constructing values.
        with tempfile.TemporaryDirectory() as t:
            dest=Path(t)
            (dest/"native_pbp_lineups.py").write_bytes(data("gamepulse/fusion/native_pbp_lineups.py"))
            sys.path.insert(0,t)
            from native_pbp_lineups import parse_team
            outcome={}
            for side in ("home","away"):
                tid=str(report["game_header"][side+"Team"]["teamId"])
                scoped=[x for x in rows if isinstance(x,dict) and str(x.get("TeamId"))==tid]
                parsed=parse_team(report,view,side,{"multi_row_table_data":scoped},
                    {"state":"SOURCE_READABLE","sha256":summary["source_sha256"],
                     "source":"PBPSTATS_GET_GAME_STATS_GAMEID_NATIVE_LINEUPS","params":{"GameId":gid,"Type":"Lineup"}})
                outcome[side]=parsed
            summary["teams"]={side:{"team":r["team"],"certified":r["certified"],
                "gate":r.get("gate"),"rows_qualified":r.get("rows_qualified"),
                "totals":r.get("totals"),"anomaly_count":len(r.get("anomalies",[]))}
                for side,r in outcome.items()}
            if not all(r["certified"] for r in outcome.values()):
                raise ValueError("PBPSTATS_SCORE_TIME_OR_SINGLE_GAME_QA_FAILED")
            summary["source_validated"]=True
            output={"schema":"gamepulse.pbpstats-native-game5-possession-2026-27.v1",
                "game_id":gid,"source_provenance":summary,
                "teams":outcome,"certified_provider_game_lineups":True,
                "native_gamepulse_possession_boundary_certified":False}
            save(f"gamepulse/fusion/pbp_native/games/{gid}.json",output)
    except Exception as exc:
        summary["source_gate"]=type(exc).__name__+":"+str(exc)[:90]
    save(f"gamepulse/fusion/native_28_qa/pbpstats_fallback_{gid}.json",summary)
    print("PBPSTATS_SINGLE_GAME_SCOPE_AND_SCORE_AUDIT",
          json.dumps({"game_id":gid,"certified":summary["source_validated"],"gate":summary.get("source_gate")}))
    if not summary["source_validated"]:raise RuntimeError("PBPSTATS_NATIVE_SOURCE_NOT_CERTIFIED")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--game",required=True)
    a=p.parse_args();run(a.game)
