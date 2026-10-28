#!/usr/bin/env python3
"""Amen 732: extract *actual native MP4 frames*, never rely on fixture JPEGs.
Only original 30fps decoded frames, with source video SHA and original PTS.
Offsets are provisional temporal candidates, not certified cross-view contact.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import cv2

GAME="0022600009"
EVENT=732
INDEX={
"Broadcast":275,
"High Tight":235,
"Left Above Rim":247,
"Right Above Rim":234,
"Left Slash":221,
"Right Slash":211,
}
SELECTED_SHIFTS=(-3,0,3)
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()
def verified_decode(video,idxs):
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise RuntimeError("INVALID_SOURCE_MP4:"+video.name)
    results={}
    last=max(idxs)
    # Decode from frame zero to guarantee frame order even across B-frame GOP.
    for i in range(last+1):
        ok,frame=cap.read()
        if not ok:raise RuntimeError(f"DECODE_FAILURE:{video.name}:{i}")
        if i in idxs:
            if frame.shape[:2]!=(540,960):
                raise RuntimeError(f"NATIVE_RESOLUTION_MISMATCH:{video.name}:{i}:{frame.shape}")
            results[i]=frame
    cap.release()
    if len(results)!=len(idxs):raise RuntimeError("MISSING_DECODED_INDICES")
    return results
def run(root:Path,out:Path):
    manifest=json.loads((root/"source_manifest.json").read_text())
    pts=json.loads((root/"native_presentation_timestamps.json").read_text())
    assert manifest["event"]["game_id"]==GAME and int(manifest["event"]["event_num"])==EVENT
    feed={e["label"]:e for e in manifest["feeds"]}
    assert set(INDEX).issubset(feed),sorted(feed)
    out.mkdir(parents=True,exist_ok=True)
    summary={"schema":"hoopvision.freeview.amen732.native_six_video_frame_sets.v1",
             "game_id":GAME,"event_num":EVENT,
             "source_origin":"six verified private 104 NBA native MP4 release assets",
             "estimated_common_exposure_verified":False,
             "first_hand_ball_contact_verified":False,
             "shifts":list(SELECTED_SHIFTS),"camera_views":{}}
    for name,nominal in INDEX.items():
        row=feed[name];video=root/row["file"]
        assert video.is_file(),str(video)
        calc=digest(video)
        assert calc==row["native_media_sha256"],name
        assert pts[name]["clip_sha256"]==calc,name
        p=pts[name]["frames"]
        nums=[nominal+shift for shift in SELECTED_SHIFTS]
        assert 0<=min(nums) and max(nums)<len(p)
        frames=verified_decode(video,set(nums))
        all_rows=[]
        for shift,idx in zip(SELECTED_SHIFTS,nums):
            folder=out/("offset_%+d"%shift)
            folder.mkdir(parents=True,exist_ok=True)
            # Original source frame, lossless PNG; filename retained from the
            # previous prototype for reproducible model configuration.
            ident=name.lower().replace(" ","-")
            dst=folder/("amen732-native-"+ident+"-f"+str(nominal)+".png")
            assert cv2.imwrite(str(dst),frames[idx])
            all_rows.append({"offset_frames":shift,"source_native_index":idx,
                "pts_time_s":p[idx]["pts_time_s"],
                "decoded_source_png":dst.name,
                "decoded_png_sha256":digest(dst),
                "source_video_sha256":calc,
                "source_video_asset_name":video.name})
        summary["camera_views"][name]={"nominal_frame":nominal,"source_native_frame_count":len(p),
                                        "tested":all_rows}
    for shift in SELECTED_SHIFTS:
        folder=out/("offset_%+d"%shift)
        selected={}
        for name,report in summary["camera_views"].items():
            x=next(x for x in report["tested"] if x["offset_frames"]==shift)
            selected[name]=x
        (folder/"native_video_extraction_manifest.json").write_text(json.dumps({
          "schema":"hoopvision.freeview.amen732.six_native_decoded_png.v1",
          "source_original_mp4_SHA_verified":True,
          "actual_native_frame_indices_verified":True,
          "cross_camera_exposure_certified":False,
          "first_contact_certified":False,
          "shift_frames":shift,
          "source_frames":selected},indent=2)+"\n")
    (out/"amen732-six-native-video-window-source-qa.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("AMEN732_SIX_ORIGINAL_NATIVE_MP4S_DECODED_AND_SHA_VERIFIED",
        "views",len(INDEX),"offset_sets",len(SELECTED_SHIFTS),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();run(a.root,a.out)
