#!/usr/bin/env python3
"""Native-frame synchronized six-camera video review; no novel-view claims.

Uses original event-732 native video PTS and the SHA-verified 15-edge audio
offset graph from the SAME reacquired source files. No interpolation, blending,
or reconstructed human/ball pixels. All generated NBA media stays PRIVATE.
"""
from __future__ import annotations
import argparse,hashlib,json,subprocess
from pathlib import Path
import cv2,numpy as np

VIEWS=("Broadcast","High Tight","Left Above Rim","Right Above Rim","Left Slash","Right Slash")
W,H=3840,2160
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()
def extract(video,needed):
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise RuntimeError("NATIVE_MOVIE_CANNOT_OPEN")
    images={}
    for i in range(max(needed)+1):
        ok,frame=cap.read()
        if not ok:raise RuntimeError("SOURCE_FRAME_DECODING_GAP")
        if i in needed:
            if frame.shape[:2]!=(540,960):
                raise RuntimeError("REACQUIRED_SOURCE_WRONG_NATIVE_DIMENSIONS")
            images[i]=frame
    cap.release()
    if len(images)!=len(needed):raise RuntimeError("MISSING_NATIVE_FRAME_AFTER_DECODE")
    return images
def run(source,alignment,out,ffmpeg,fps,begin,end):
    qa=json.loads(alignment.read_text())
    manifest=json.loads((source/"source_manifest.json").read_text())
    pts=json.loads((source/"native_presentation_timestamps.json").read_text())
    if qa.get("game_id")!="0022600009" or qa.get("event_num")!=732 or manifest["event"]["event_num"]!=732:
        raise RuntimeError("WRONG_GAME_EVENT")
    graph=qa["graph"]
    if not(graph["connected"] and graph["cycle_consistency_40ms_pass"] and qa["accepted_edges"]==15):
        raise RuntimeError("SIX_AUDIO_CAMERA_GRAPH_NOT_ACCEPTED")
    if not (0<begin<end<30) or fps not in (12,15,20,24):
        raise RuntimeError("INVALID_TIME_WINDOW")
    out.mkdir(parents=True,exist_ok=True)
    records={}
    count=int(np.ceil((end-begin)*fps))
    times=begin+np.arange(count,dtype=float)/fps
    fby={f["label"]:f for f in manifest["feeds"]}
    for label in VIEWS:
        feed=fby[label];video=source/feed["file"]
        vh=sha(video)
        if vh!=feed["native_media_sha256"] or vh!=pts[label]["clip_sha256"]:
            raise RuntimeError("SOURCE_AUDIO_SYNC_VERSION_MISMATCH")
        lag=graph["relative_audio_delay_vs_broadcast_s"][label]
        stamps=np.array([float(x["pts_time_s"]) for x in pts[label]["frames"]],dtype=float)
        wanted=times+lag
        idxs=np.searchsorted(stamps,wanted,side="left")
        idxs=np.clip(idxs,0,len(stamps)-1)
        earlier=np.maximum(idxs-1,0)
        idxs=np.where(abs(stamps[earlier]-wanted)<abs(stamps[idxs]-wanted),earlier,idxs)
        errors=np.round(1000*(stamps[idxs]-wanted),2)
        if max(abs(errors))>25:
            raise RuntimeError("AUDIO_CONSENSUS_FRAME_MISMATCH_GT25MS:"+label)
        images=extract(video,set(int(x) for x in idxs))
        records[label]={"sha256":vh,"source_file":video.name,
                        "source_original_pts_s":[round(float(stamps[i]),6) for i in idxs],
                        "source_native_frame_idx":[int(i) for i in idxs],
                        "native_pts_vs_model_audio_target_error_ms":errors.tolist(),
                        "mean_abs_select_error_ms":round(float(np.mean(abs(errors))),3),
                        "max_abs_select_error_ms":round(float(max(abs(errors))),3),
                        "frames":images}
    out_mp4=out/"amen732-all-six-original-camera-video-synchronized-3840x2160.mp4"
    command=[ffmpeg,"-nostdin","-y","-hide_banner","-v","error",
             "-f","rawvideo","-pix_fmt","bgr24","-video_size",f"{W}x{H}",
             "-framerate",str(fps),"-i","pipe:0",
             "-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=44100",
             "-map","0:v","-map","1:a","-c:v","libx264","-preset","veryfast",
             "-crf","25","-pix_fmt","yuv420p","-profile:v","high",
             "-level:v","5.1","-c:a","aac","-b:a","64k",
             "-movflags","+faststart","-shortest",str(out_mp4)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for k,ref_time in enumerate(times):
            canvas=np.full((H,W,3),12,np.uint8)
            for i,label in enumerate(VIEWS):
                native=records[label]["frames"][records[label]["source_native_frame_idx"][k]]
                # Never crop away the hand-ball encounter, show whole source.
                cell=cv2.resize(native,(1280,720),interpolation=cv2.INTER_LINEAR)
                row,col=divmod(i,3)
                y0=row*1080+125;x0=col*1280
                canvas[y0:y0+720,x0:x0+1280]=cell
                ident=records[label]["source_native_frame_idx"][k]
                cv2.putText(canvas,f"{label} | native frame {ident}",
                    (x0+22,row*1080+66),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2,cv2.LINE_AA)
                cv2.putText(canvas,f"Native PTS {records[label]['source_original_pts_s'][k]:.3f}s",
                    (x0+22,row*1080+100),cv2.FONT_HERSHEY_SIMPLEX,.7,(205,205,205),2,cv2.LINE_AA)
                cv2.putText(canvas,"source 960x540, no reconstruction",
                    (x0+22,row*1080+900),cv2.FONT_HERSHEY_SIMPLEX,.7,(230,230,230),1)
            cv2.putText(canvas,f"EVENT 732 | AUDIO CLOCK REF {ref_time:.3f}s | SAME-EXPOSURE NOT CERTIFIED",
                (20,1070),cv2.FONT_HERSHEY_SIMPLEX,1.1,(255,255,255),2,cv2.LINE_AA)
            proc.stdin.write(canvas.tobytes())
            if k in (0,count//4,count//2,3*count//4,count-1):
                cv2.imwrite(str(out/f"amen732-sixcam-source-{k:03d}-3840x2160.jpg"),
                    canvas,[cv2.IMWRITE_JPEG_QUALITY,87])
        proc.stdin.close()
        errors=proc.stderr.read()
        done=proc.wait(timeout=240)
        if done!=0:raise RuntimeError("FFMPEG_UHD_ENCODING_FAILED:"+errors.decode("utf-8","replace")[-1600:])
    finally:
        if proc.poll() is None:
            proc.kill();proc.wait()
    if not out_mp4.is_file() or out_mp4.stat().st_size<50000:
        raise RuntimeError("RENDERED_SOURCE_MOSAIC_EMPTY")
    clean={k:{f:v for f,v in row.items() if f!="frames"} for k,row in records.items()}
    qa_doc={
      "schema":"hoopvision.freeview.amen732.six_full_video_audio_aligned_mosaic.v1",
      "game_id":"0022600009","event_num":732,
      "provenance":"SIX_ORIGINAL_FULL_NATIVE_MP4S_CURRENT_HLS_VERSION_ONLY",
      "sources":clean,"frames":count,"fps":fps,
      "reference_audio_epoch_window":[begin,end],
      "pairwise_audio_edges":15,"audio_max_cycle_residual_ms":graph["pairwise_residual_max_ms"],
      "pixels":"EXACT_SOURCE_FRAMES_UNSYNTHESIZED_960x540_SCALED_FOR_REVIEW",
      "same_physical_exposure_certified":False,
      "actor_ball_contact_frame_certified":False,
      "archived_20261024_source_version_identical":False,
      "novel_viewpoint_reconstructed":False,
      "novel_viewpoint_accepted":False,
      "video_3840x2160":out_mp4.name,
      "video_sha256":sha(out_mp4),
      "video_bytes":out_mp4.stat().st_size
    }
    (out/"amen732-sixcam-native-synced-source-video-qa.json").write_text(json.dumps(qa_doc,indent=2)+"\n")
    print("AMEN732_REAL_SIX_CAMERA_SOURCE_4K_VIDEO",count,"sha",qa_doc["video_sha256"],
        "bytes",qa_doc["video_bytes"],"same_exposure_certified",False,flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--audio",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--ffmpeg",required=True)
    p.add_argument("--fps",type=int,default=15)
    p.add_argument("--begin",type=float,default=8.3)
    p.add_argument("--end",type=float,default=10.8)
    a=p.parse_args()
    run(a.source,a.audio,a.out,a.ffmpeg,a.fps,a.begin,a.end)
