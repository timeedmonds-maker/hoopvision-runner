#!/usr/bin/env python3
"""Six real-camera same-audio-epoch visual package, source-uncertainty explicit.

Frames are original, exact decoded NBA pixels; NO 3D geometry, image generation
or synthesized "same instant" pixels. All source outputs remain in private 104.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np

NAMES=("Broadcast","High Tight","Left Above Rim","Right Above Rim","Left Slash","Right Slash")
OLD={"Broadcast":275,"High Tight":235,"Left Above Rim":247,
     "Right Above Rim":234,"Left Slash":221,"Right Slash":211}
W,H=3840,2160
def hash_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for x in iter(lambda:f.read(1<<20),b""):h.update(x)
    return h.hexdigest()
def grab(video,indices):
    c=cv2.VideoCapture(str(video))
    if not c.isOpened():raise RuntimeError("CANNOT_DECODE_PRIVATE_SOURCE:"+video.name)
    found={}
    for n in range(max(indices)+1):
        ret,im=c.read()
        if not ret:raise RuntimeError("MISSING_FRAME_NATIVE_IDX")
        if n in indices:found[n]=im
    c.release()
    if len(found)!=len(set(indices)):raise RuntimeError("NATIVE_FRAME_COUNT_MISMATCH")
    return found
def render_tile(image,label,line2,cell_w=1280,cell_h=1080):
    # Only presentation scale. Native source remains 960x540.
    if image.shape[:2]!=(540,960):raise RuntimeError("SOURCE_NOT_NATIVE_960_540")
    c=np.full((cell_h,cell_w,3),16,np.uint8)
    scaled=cv2.resize(image,(cell_w,720),interpolation=cv2.INTER_LINEAR)
    c[145:865]=scaled
    cv2.putText(c,label,(24,54),cv2.FONT_HERSHEY_SIMPLEX,1.2,(255,255,255),2,cv2.LINE_AA)
    cv2.putText(c,line2,(24,100),cv2.FONT_HERSHEY_SIMPLEX,.8,(220,220,220),2,cv2.LINE_AA)
    cv2.putText(c,"SOURCE 960x540 | contact unverified",(24,942),cv2.FONT_HERSHEY_SIMPLEX,.75,(200,200,200),1)
    return c
def make_sheet(cameras,which,out):
    tiles=[]
    for x in cameras:
        data=x[which]
        im=cv2.imread(data["file"],cv2.IMREAD_COLOR)
        tiles.append(render_tile(im,x["camera"],
            f'{which}: frame {data["frame_index"]}, PTS {data["native_pts_s"]:.3f}s'))
    composite=np.vstack([np.hstack(tiles[:3]),np.hstack(tiles[3:])])
    assert composite.shape==(H,W,3)
    if not cv2.imwrite(str(out),composite,[cv2.IMWRITE_JPEG_QUALITY,92]):
        raise RuntimeError("SHEET_WRITE_FAILED")
def run(root,align_file,out):
    d=json.loads(align_file.read_text())
    g=d["graph"]
    if d["game_id"]!="0022600009" or d["event_num"]!=732:
        raise RuntimeError("WRONG_EVENT")
    if not(g.get("connected") and g.get("cycle_consistency_40ms_pass")):
        raise RuntimeError("NO_AUDIO_GRAPH_CERTIFIED_DO_NOT_SELECT_FRAMES")
    candidate=d["provisional_frame_candidates"]
    if len(candidate)!=6:raise RuntimeError("SIX_AUDIO_CANDIDATES_REQUIRED")
    feed={r["label"]:r for r in json.loads((root/"source_manifest.json").read_text())["feeds"]}
    out.mkdir(parents=True,exist_ok=True)
    cameras=[]
    for label in NAMES:
        i=candidate[label]["frame_index"];j=OLD[label]
        q=feed[label];video=root/q["file"]
        if hash_file(video)!=q["native_media_sha256"]:
            raise RuntimeError("VIDEO_SHA_MISMATCH")
        frames=grab(video,{i,j})
        pts=json.loads((root/"native_presentation_timestamps.json").read_text())
        rec={"camera":label,"original_video_sha256":q["native_media_sha256"],
            "native_video_name":video.name}
        for phase,idx in (("audio_aligned",i),("previous_unsynced",j)):
            filename=f'amen732-{phase}-{label.lower().replace(" ","-")}-f{idx:03d}.png'
            path=out/filename
            cv2.imwrite(str(path),frames[idx])
            rec[phase]={"frame_index":idx,
                "native_pts_s":round(float(pts[label]["frames"][idx]["pts_time_s"]),6),
                "file":str(path),"sha256":hash_file(path),
                "native_source_pixels":True,
                "cross_camera_same_physical_frame_certified":False}
        rec["previous_vs_new_frame_offset"]=j-i
        cameras.append(rec)
    new=out/"amen732-sixview-synchronized-candidate-3840x2160.jpg"
    old=out/"amen732-sixview-previous-unsynced-3840x2160.jpg"
    make_sheet(cameras,"audio_aligned",new)
    make_sheet(cameras,"previous_unsynced",old)
    qa={"schema":"hoopvision.freeview.amen732.sixview_native_audio_candidates.v2",
        "game_id":"0022600009","event_num":732,
        "original_source_video_count":6,"source_2d_frame_count_exported":12,
        "camera_pairs_matched":d["accepted_edges"],
        "cycle_residual_max_ms":g["pairwise_residual_max_ms"],
        "model":"none_source_exact_native_video_decodes",
        "before_after":cameras,
        "sheets":[{"filename":new.name,"sha256":hash_file(new)},
                  {"filename":old.name,"sha256":hash_file(old)}],
        "source_frame_identity":"native_video_shas_and_decoded_lossless_png_shas",
        "same_exposure_certified":False,"first_hand_ball_touch_certified":False,
        "actor_silhouettes_certified":False,"camera_intrinsics_extrinsics_verified":False,
        "valid_3d_novel_view_count":0,
        "inference_next":"Independent source-pixel action comparison then genuine Gaussian/human-surface trial, not another depth point-cloud export"}
    (out/"amen732-sixview-native-exact-frame-package-v2.json").write_text(json.dumps(qa,indent=2)+"\n")
    print("SIXVIEW_EXACT_NATIVE_FRAME_PACKAGE",qa["original_source_video_count"],
          "audio_cycle_ms",qa["cycle_residual_max_ms"],
          "old_native_frames_lag",[r["previous_vs_new_frame_offset"] for r in cameras],
          "same_exposure_certified",False,flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--audio-qa",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.source,a.audio_qa,a.out)
