#!/usr/bin/env python3
"""Ephemeral official NBA six-feed clip acquisition for research-grade Freeview.

Only official HLS streams. Does not publish video, playlists, signed URLs or frames.
Native MP4 bytes may differ from earlier archived copies; record fresh provenance.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib, html, json, re, subprocess, urllib.parse, urllib.request
from pathlib import Path

CAMERAS = ("Broadcast", "High Tight", "Left Above Rim", "Right Above Rim",
           "Left Slash", "Right Slash")
GAME, EVENT = "0022600009", 732
HEADERS = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
           "Referer":"https://clips.nba.com/","Accept":"*/*"}

def request_bytes(url: str) -> bytes:
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=40) as response:
        return response.read()

def sha(path: Path):
    digest=hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda:fp.read(1<<20),b""):
            digest.update(chunk)
    return digest.hexdigest()

def join_signed(base: str,child: str) -> str:
    merged=urllib.parse.urljoin(base,child)
    a=urllib.parse.urlsplit(base);b=urllib.parse.urlsplit(merged)
    if a.query and not b.query:
        merged=urllib.parse.urlunsplit(b._replace(query=a.query))
    return merged

def options_from_page(page_url: str) -> dict[str,str]:
    html_doc=request_bytes(page_url).decode("utf-8","replace")
    result={}
    for match in re.finditer(r'<option\s+value="([^"]+)"([^>]*)>(.*?)</option>',
                             html_doc,flags=re.I|re.S):
        name=re.sub(r'<[^>]+>','',html.unescape(match.group(3))).strip()
        url=html.unescape(match.group(1)).strip()
        if ".m3u8" in url.lower() and urllib.parse.urlsplit(url).hostname=="lrmedia.nba.com":
            result[name]=url
    missing=[name for name in CAMERAS if name not in result]
    if missing:
        raise RuntimeError("OFFICIAL_NATIVE_CAMERA_FEED_MISSING:"+",".join(missing))
    return result

def media_segments(url: str,depth=0):
    if depth>4:raise RuntimeError("HLS_RECURSION_LIMIT")
    lines=[s.strip() for s in request_bytes(url).decode("utf-8","replace").splitlines() if s.strip()]
    if not lines or lines[0]!="#EXTM3U":raise RuntimeError("BAD_OFFICIAL_HLS_PLAYLIST")
    variants=[]
    for i,line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):continue
        bw=re.search(r'BANDWIDTH=(\d+)',line)
        for child in lines[i+1:]:
            if not child.startswith("#"):
                variants.append((int(bw.group(1)) if bw else 0,join_signed(url,child)))
                break
    if variants:return media_segments(max(variants,key=lambda x:x[0])[1],depth+1)
    init=None;segments=[]
    for line in lines:
        if line.startswith("#EXT-X-MAP:"):
            m=re.search(r'URI="([^"]+)"',line)
            if m:init=join_signed(url,m.group(1))
        elif not line.startswith("#"):
            segments.append(join_signed(url,line))
    if not segments:raise RuntimeError("NO_MEDIA_SEGMENTS")
    return ([init] if init else [])+segments

def source_meta(path: Path,ffprobe: str):
    args=[ffprobe,"-v","error","-select_streams","v:0","-show_entries",
          "stream=width,height,time_base,avg_frame_rate,r_frame_rate:"
          "frame=best_effort_timestamp,best_effort_timestamp_time,"
          "pkt_dts_time,pkt_duration_time","-show_frames","-of","json",str(path)]
    result=json.loads(subprocess.check_output(args,text=True))
    st=result.get("streams") or []
    frames=result.get("frames") or []
    if len(st)!=1 or len(frames)<260:
        raise RuntimeError("SHORT_OR_UNREADABLE_ORIGINAL_CAMERA_CLIP")
    if (int(st[0]["width"]),int(st[0]["height"]))!=(960,540):
        raise RuntimeError("UNEXPECTED_NATIVE_FRAME_DIMENSIONS")
    rows=[]
    for idx,f in enumerate(frames):
        pts=f.get("best_effort_timestamp_time")
        if pts is None:raise RuntimeError("MISSING_NATIVE_FRAME_PTS")
        rows.append({"frame_index":idx,
                     "pts_time_s":str(pts),
                     "best_effort_timestamp":f.get("best_effort_timestamp"),
                     "pkt_dts_time_s":f.get("pkt_dts_time"),
                     "pkt_duration_time_s":f.get("pkt_duration_time")})
    return {"stream":st[0],"frames":rows}

def fetch_feed(name,url,target,ffmpeg,ffprobe):
    items=media_segments(url)
    blocks=[None]*len(items)
    with ThreadPoolExecutor(max_workers=min(8,len(items))) as pool:
        futures={pool.submit(request_bytes,link):i for i,link in enumerate(items)}
        for done in as_completed(futures):
            blocks[futures[done]]=done.result()
    temp=target.with_suffix(".hls.part")
    with temp.open("wb") as fp:
        for item in blocks:
            if item is None:raise RuntimeError("MISSING_SEGMENT")
            fp.write(item)
    try:
        subprocess.run([ffmpeg,"-nostdin","-y","-hide_banner","-loglevel","error",
                        "-i",str(temp),"-map","0:v:0","-map","0:a:0?",
                        "-c","copy","-movflags","+faststart",str(target)],
                       check=True)
    finally:
        temp.unlink(missing_ok=True)
    meta=source_meta(target,ffprobe)
    digest=sha(target)
    return name,{"file":target.name,"sha256":digest,"meta":meta,
                 "native_media_sha256":digest,"total_bytes":target.stat().st_size}

def main(root:Path,page_url:str,ffmpeg:str,ffprobe:str):
    root.mkdir(parents=True,exist_ok=True)
    opts=options_from_page(page_url)
    all_feeds={}
    # Bounded concurrent cameras; source URLs never logged.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={}
        for name in CAMERAS:
            suffix=name.lower().replace(" ","-")
            filename=f"{GAME}-e{EVENT}-{suffix}.mp4"
            fut=pool.submit(fetch_feed,name,opts[name],root/filename,ffmpeg,ffprobe)
            futures[fut]=name
        for fut in as_completed(futures):
            name,row=fut.result()
            all_feeds[name]=row
            print("SOURCE_NATIVE_CAMERA_VERIFIED",name,
                  "frames",len(row["meta"]["frames"]),
                  "bytes",row["total_bytes"],flush=True)
    if len(all_feeds)!=6 or len({v["sha256"] for v in all_feeds.values()})!=6:
        raise RuntimeError("SIX_DISTINCT_CAMERA_BINARIES_NOT_VERIFIED")
    feeds=[]; pts={}
    for name in CAMERAS:
        row=all_feeds[name]
        feeds.append({"label":name,"file":row["file"],
                     "native_media_sha256":row["sha256"],
                     "calibration_current_frame_certified":False,
                     "same_contact_state_certified":False})
        pts[name]={"clip_sha256":row["sha256"],
                   "stream":row["meta"]["stream"],
                   "frames":row["meta"]["frames"]}
    manifest={"schema":"hoopvision.freeview.native-multicamera-evidence.v1",
              "event":{"game_id":GAME,"event_num":EVENT,
                       "first_hand_ball_contact_pts_certified":False},
              "source_kind":"OFFICIAL_NBA_LIVE_RESOLVED_HLS_NATIVE",
              "source_view_count":len(feeds),"feeds":feeds,
              "quality":{"native_clips":"DECODED_AND_SHA_VERIFIED",
                         "first_touch":"UNVERIFIED",
                         "synchronized_triplet":"UNVERIFIED",
                         "calibration":"UNVERIFIED"}}
    (root/"source_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (root/"native_presentation_timestamps.json").write_text(json.dumps(pts,indent=2)+"\n")
    print("SIX_DIRECT_OFFICIAL_NBA_NATIVE_MP4S_READY",len(feeds),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--page",default=f"https://clips.nba.com/?gameNo={GAME}&eventNum={EVENT}&source=grs")
    p.add_argument("--ffmpeg",required=True)
    p.add_argument("--ffprobe",required=True)
    a=p.parse_args()
    main(a.root,a.page,a.ffmpeg,a.ffprobe)
