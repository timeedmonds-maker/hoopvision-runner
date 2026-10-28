#!/usr/bin/env python3
"""Six *original NBA videos* -> simultaneous-frame candidate -> DA3 3D -> virtual-camera MP4.
Research diagnostic only. This is neither certified first hand-ball contact nor source-supported
3D geometry. No cross-camera time mapping is treated as established fact.
"""
from __future__ import annotations
import argparse, json, math, os, subprocess, sys, time
from pathlib import Path
import cv2, numpy as np

from amen732_native_six_video_frame_sets import run as extract_video_sets, INDEX
from amen732_da3_unposed_sixview_trial import project_source_points, rotation_y, render, sha

GAME="0022600009"
EVENT=732
MODEL="depth-anything/DA3-BASE"
CAMERAS=list(INDEX)
FRAMERATE=24

def estimate_scene_center(depth, K, ext, img_hw):
    # Crop near the airborne Wemby/Amen encounter in reference *Left Slash*.
    h,w=img_hw
    x0,x1=int(.50*w),int(.69*w)
    y0,y1=int(.19*h),int(.65*h)
    z=np.asarray(depth[y0:y1,x0:x1])
    z=z[np.isfinite(z)&(z>0)]
    if len(z)<30:raise RuntimeError("MODEL_CANNOT_LOCATE_DEPTH_NEAR_ACTORS")
    zz=float(np.median(z))
    pixel=np.array([.59*w,.40*h,1.0])
    cc=np.linalg.inv(K)@pixel*zz
    R=ext[:3,:3];t=ext[:3,3]
    return (cc-t)@R

def run_ffmpeg(frames_dir:Path, prefix:str,output:Path,ffmpeg:str):
    # Upload only rendered result to PRIVATE repository, never public artifacts.
    cmd=[ffmpeg,"-nostdin","-y","-loglevel","error","-framerate",str(FRAMERATE),
         "-i",str(frames_dir/(prefix+"_%04d.png")),"-vf","scale=3840:2160:flags=lanczos",
         "-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p",
         "-movflags","+faststart",str(output)]
    subprocess.run(cmd,check=True)
    if output.stat().st_size<10000:raise RuntimeError("EMPTY_ORBIT_MP4")

def path_samples(start,end,frames,go_back):
    def ease(x):
        return .5-.5*math.cos(math.pi*x)
    if go_back:
        mid=frames//2
        return [start+(end-start)*ease(i/max(1,mid-1)) for i in range(mid)]+[end+(start-end)*ease(i/max(1,frames-mid-1)) for i in range(frames-mid)]
    return [start+(end-start)*ease(i/max(1,frames-1)) for i in range(frames)]

def orbit(base,out,points,colors,K,ext,hw,angle_list,ffmpeg):
    output_frames=out/(base+"_frames")
    output_frames.mkdir(exist_ok=True)
    target=np.asarray(points["pivot"])
    R=ext[:3,:3];t=ext[:3,3];C=-R.T@t
    for n,degree in enumerate(angle_list):
        Q=rotation_y(degree)
        Rt=R@Q.T;Ct=target+Q@(C-target);tt=-Rt@Ct
        rgb,support=render(points["xyz"],colors,Rt,tt,K,hw)
        img=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
        # Only explanatory diagnostic annotation on video, not pretending 4K details.
        cv2.putText(img,"6 NATIVE NBA MP4s | UNCALIBRATED MODEL | RESEARCH ONLY",
            (8,20),cv2.FONT_HERSHEY_SIMPLEX,.31,(255,255,255),1,cv2.LINE_AA)
        cv2.putText(img,f"virtual yaw {degree:+.1f} deg", (8,39),
            cv2.FONT_HERSHEY_SIMPLEX,.34,(255,255,255),1,cv2.LINE_AA)
        if not cv2.imwrite(str(output_frames/f"{base}_{n:04d}.png"),img):
            raise RuntimeError("CANNOT_WRITE_ORBIT_FRAME")
    output=out/(base+"-3840x2160.mp4")
    run_ffmpeg(output_frames,base,output,ffmpeg)
    return {"mp4":output.name,"sha256":sha(output),"frames":len(angle_list),
            "angles_min_max":[round(float(min(angle_list)),2),round(float(max(angle_list)),2)],
            "duration_s":round(len(angle_list)/FRAMERATE,3),
            "size_bytes":output.stat().st_size,"encoded_dimensions":[3840,2160],
            "geometry_model_only":True}

def run(root,out,ffmpeg):
    source=out/"decoded_native";extract_video_sets(root,source)
    import torch
    from depth_anything_3.api import DepthAnything3
    torch.set_num_threads(3)
    model=DepthAnything3.from_pretrained(MODEL).to(device="cpu").eval()
    diagnostics=[]
    center=None
    start=time.time()
    # Source before/at/after the action: all 6 *videos* contribute 3 native frames each.
    for shift in (-3,0,3):
        folder=source/("offset_%+d"%shift)
        data=json.loads((folder/"native_video_extraction_manifest.json").read_text())
        paths=[str(folder/data["source_frames"][name]["decoded_source_png"]) for name in CAMERAS]
        with torch.inference_mode():
            pred=model.inference(image=paths,process_res=448,
                 process_res_method="upper_bound_resize",use_ray_pose=False)
        if pred.extrinsics is None or pred.intrinsics is None:
            raise RuntimeError("MODEL_DID_NOT_INFER_SIX_CAMERAS")
        ext=np.asarray(pred.extrinsics);K=np.asarray(pred.intrinsics)
        if ext.shape[1:]==(4,4):ext=ext[:,:3,:]
        pts,rgb,ext,K,images=project_source_points(pred,stride=2)
        if len(pts)<10000:raise RuntimeError("EMPTY_SCENE")
        # Every time stratum is reconstructed from all 6 MP4 camera feeds.
        base={"offset_native_frames":shift,"video_count":len(paths),
              "predicted_camera_count":len(ext),"scene_points":len(pts),
              "frame_indices":{name:data["source_frames"][name]["source_native_index"] for name in CAMERAS},
              "native_pts_by_camera":{name:data["source_frames"][name]["pts_time_s"] for name in CAMERAS},
              "unverified_same_exposure":True}
        centers=np.stack([-e[:3,:3].T@e[:3,3] for e in ext])
        origin=np.median(pts,axis=0)
        dr=centers-origin
        dr/=np.maximum(np.linalg.norm(dr,axis=1,keepdims=True),1e-6)
        degs=[]
        for i in range(len(dr)):
            for j in range(i+1,len(dr)):
                degs.append(float(np.degrees(np.arccos(np.clip(dr[i]@dr[j],-1,1)))))
        base["max_predicted_camera_separation_degrees"]=round(max(degs),2)
        diagnostics.append(base)
        if shift==0:
            # Keep center-frame only for the bullet-time orbit; earlier/later
            # six-view reconstructions are distinct, unaligned dynamic states.
            pivot=estimate_scene_center(pred.depth[4],K[4],ext[4],
                                       (int(images.shape[1]),int(images.shape[2])))
            center={"xyz":pts.astype(np.float32),"pivot":pivot,"rgb":rgb,
                    "K":K[4],"ext":ext[4],"hw":tuple(images.shape[1:3])}
        print("SIX_VIDEO_TEMPORAL_FUSION",shift,"views",len(paths),"model_points",len(pts),flush=True)
    if center is None:raise RuntimeError("NO_CENTRAL_FREEZE")
    out.mkdir(exist_ok=True,parents=True)
    # Full unrestricted 360 sweep and a denser candidate wide orbit; neither
    # is promoted to a verified replay merely because it rendered.
    results=[]
    wide=path_samples(-90,80,96,True)
    results.append(orbit("amen732-sixvideo-wide170-candidate",out,center,center["rgb"],
                         center["K"],center["ext"],center["hw"],wide,ffmpeg))
    full=path_samples(-180,180,96,False)
    results.append(orbit("amen732-sixvideo-full360-diagnostic",out,center,center["rgb"],
                         center["K"],center["ext"],center["hw"],full,ffmpeg))
    qa={"schema":"hoopvision.freeview.amen732.six_native_mp4_multivideo_3d.v1",
        "game_id":GAME,"event_num":EVENT,
        "input":"all_six_original_native_mp4_files_sha256_verified",
        "input_original_camera_video_count":6,
        "total_native_frame_observations":18,
        "distinct_source_video_timestamps":3,
        "per_time_sixview_model_diagnostics":diagnostics,
        "model":MODEL,"model_source":"pinned DA3 code",
        "camera_intrinsics_extrinsics_supplied":False,
        "elapsed_s":round(time.time()-start,2),
        "real_six_video_multi_camera_reconstruction_executed":True,
        "full_360_sweep_coverage_certified":False,
        "widest_physically_faithful_arc_degrees":None,
        "same_exposure_certified":False,
        "hand_ball_contact_certified":False,
        "method":"feedforward joint six-view 3D depth fusion, depth-sorted surfel render",
        "note":"Both moving-camera outputs are diagnostic, not certified game evidence. Rendering does not establish correct hidden actor surfaces.",
        "outputs":results}
    (out/"amen732-native-sixvideo-3d-reconstruction-qa.json").write_text(json.dumps(qa,indent=2)+"\n")
    print("AMEN732_SIX_NATIVE_VIDEOS_TO_VIRTUAL_CAMERA_MP4",json.dumps(
        {"frames":18,"model":MODEL,"outputs":[x["mp4"] for x in results],
         "certified_arc":None}),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--ffmpeg",required=True)
    a=p.parse_args();run(a.root,a.out,a.ffmpeg)
