#!/usr/bin/env python3
"""Private, independent game-time coverage audit; never publishes tracking frames."""
import datetime as dt
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from urllib.request import Request, urlopen

GAME="0022600091"
START=int(dt.datetime(2026,10,22,0,30,tzinfo=dt.timezone.utc).timestamp()*1000)
REPO="timeedmonds-maker/104"
TAG="gamepulse-sdk-"+GAME
WINDOW_MS=5000
CHUNK_COUNT=300
PARTS=7
OUTPUT="gameplay-QA.json"

def gh(*args):
    r=subprocess.run(["gh",*args,"--repo",REPO],check=False,text=True,
       capture_output=True,timeout=120)
    if r.returncode:raise RuntimeError("private_readback_failed")
    return r.stdout

def official(filename):
    url="https://cdn.nba.com/static/json/liveData/"+filename
    req=Request(url,headers={"Accept":"application/json, text/plain, */*",
      "Accept-Language":"en-US,en;q=0.9",
      "Origin":"https://www.nba.com",
      "Referer":"https://www.nba.com/",
      "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
    with urlopen(req,timeout=25) as response:
        raw=response.read(15_000_001)
    if len(raw)>15_000_000:raise RuntimeError("official_data_oversize")
    return json.loads(raw)

def unix_ms(value):
    if not isinstance(value,str):return None
    try:
        return int(dt.datetime.fromisoformat(value.replace("Z","+00:00")).timestamp()*1000)
    except ValueError:return None

def audit():
    base=START-600_000
    first=None
    last=None
    unique=set()
    player_frames=0
    player_last=None
    total_empty=0
    total_windows=0
    for part in range(PARTS):
        stem="sdk-part-%02d"%part
        with tempfile.TemporaryDirectory() as tmp:
            gh("release","download",TAG,"--pattern",stem+".tar.gz","--dir",tmp)
            gh("release","download",TAG,"--pattern",stem+".json","--dir",tmp)
            archive=Path(tmp)/(stem+".tar.gz")
            sidecar=json.loads((Path(tmp)/(stem+".json")).read_text())
            observed_sha=hashlib.sha256(archive.read_bytes()).hexdigest()
            if sidecar.get("archive_sha256")!=observed_sha:
                raise RuntimeError("checkpoint_sha_mismatch")
            with tarfile.open(archive,"r:gz") as tar:
                manifest=json.load(tar.extractfile("manifest.json"))
                expected_start=base+part*CHUNK_COUNT*WINDOW_MS
                if (manifest.get("game_id")!=GAME or
                    manifest.get("part")!=part or
                    manifest.get("start_ms")!=expected_start or
                    manifest.get("successful_windows")!=CHUNK_COUNT or
                    manifest.get("observed") is not True or
                    manifest.get("imputed") is not False):
                    raise RuntimeError("checkpoint_manifest_invalid")
                if any(manifest.get(key)!=sidecar.get(key) for key in
                       ("game_id","part","start_ms","successful_windows",
                        "empty_windows","frames_with_players","frames_with_ball")):
                    raise RuntimeError("checkpoint_sidecar_mismatch")
                raw=tar.extractfile("frames.jsonl.gz").read()
                with gzip.open(io.BytesIO(raw),"rt",encoding="utf-8") as frames:
                    local_frames=0
                    local_player_frames=0
                    for line in frames:
                        frame=json.loads(line)
                        stamp=frame.get("timestamp")
                        # Keyframes can straddle the five-second slot or a
                        # chunk boundary. Keep the official game-day bounds,
                        # but do not incorrectly force frame time into the job.
                        if not isinstance(stamp,int) or not START-3_600_000<=stamp<=START+8*3_600_000:
                            raise RuntimeError("frame_timestamp_invalid")
                        unique.add(stamp)
                        first=stamp if first is None else min(first,stamp)
                        last=stamp if last is None else max(last,stamp)
                        local_frames+=1
                        if any(key!="ball" for key in (frame.get("positions") or {})):
                            local_player_frames+=1
                            player_last=stamp if player_last is None else max(player_last,stamp)
                    if (local_frames!=manifest.get("unique_keyframes") or
                        local_player_frames!=manifest.get("frames_with_players")):
                        raise RuntimeError("frame_count_mismatch")
                    player_frames+=local_player_frames
            total_windows+=CHUNK_COUNT
            total_empty+=manifest.get("empty_windows",0)

    box=official("boxscore/boxscore_"+GAME+".json").get("game") or {}
    pbp=official("playbyplay/playbyplay_"+GAME+".json").get("game") or {}
    if str(box.get("gameId"))!=GAME or str(box.get("gameStatus"))!="3" or str(pbp.get("gameId"))!=GAME:
        raise RuntimeError("official_game_final_not_verified")
    # Last genuine in-game action (fourth quarter; the record is not a capture oracle).
    action_times=[unix_ms(item.get("timeActual")) for item in pbp.get("actions",[])
      if isinstance(item,dict) and item.get("period")==4]
    action_times=[t for t in action_times if t is not None]
    if not action_times or player_last is None:
        raise RuntimeError("playbyplay_or_positions_missing")
    end=max(action_times)
    gap=end-player_last
    # Classify separately from the 13-part extended capture acceptance.
    covered=(total_windows==2100 and player_frames>100 and
             first is not None and first<=START+20*60*1000 and
             player_last>=end-120_000 and end<=base+PARTS*CHUNK_COUNT*WINDOW_MS)
    return {
      "schema":"gamepulse-gameplay-coverage-qa.v1",
      "game_id":GAME,
      "source":"private SHA-verified SDK frames and independent official NBA play-by-play",
      "official_game_status":"final",
      "checked_parts":PARTS,
      "verified_five_second_windows":total_windows,
      "recorded_empty_windows":total_empty,
      "unique_position_frames":len(unique),
      "frames_with_players":player_frames,
      "first_position_timestamp_ms":first,
      "last_position_timestamp_ms":last,
      "last_player_position_timestamp_ms":player_last,
      "last_official_q4_action_timestamp_ms":end,
      "q4_last_action_minus_last_player_frame_ms":gap,
      "gameplay_coverage_status":"supported" if covered else "inconclusive",
      "limitations":"Temporal coverage check only; not per-player identity or frame-level tracking accuracy certification"
    }

def main():
    report=audit()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/OUTPUT
        path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
        gh("release","upload",TAG,str(path),"--clobber")
        check=Path(tmp)/"readback"
        check.mkdir()
        gh("release","download",TAG,"--pattern",OUTPUT,"--dir",str(check))
        if hashlib.sha256((check/OUTPUT).read_bytes()).hexdigest()!=expected:
            raise RuntimeError("private_qa_readback_failed")
    print("PRIVATE_GAMEPLAY_QA_SAVED",report["gameplay_coverage_status"])

if __name__=="__main__":
    try:main()
    except Exception as e:
        # Never print URLs, credentials, private manifests or raw frames.
        msg=str(e)
        kind=type(e).__name__
        code=(msg if msg.replace("_","").isalnum() else "class_"+kind)
        if kind=="HTTPError":
            status=getattr(e,"code",None)
            code="official_http_"+str(status) if isinstance(status,int) else "official_http_error"
        print("PRIVATE_GAMEPLAY_QA_BLOCKED",code)
        raise SystemExit(2)
