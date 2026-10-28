#!/usr/bin/env python3
"""Amen/Wemby event 732: six-view *uncalibrated* DA3 diagnostic, not a certified replay.

Research-only geometry candidate. Source frames are archived JPEG exports of
native video, with provisional per-feed freeze instants; they are NOT certified
same-exposure observations. No input camera K/R/t is supplied. Camera estimates,
sparse novel views, support masks and diagnostics are strictly model candidates.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, time
from pathlib import Path
import cv2
import numpy as np

GAME, EVENT = "0022600009", 732
VIEWS = [
    ("Broadcast", "amen732-native-broadcast-f275.jpg", 275),
    ("High Tight", "amen732-native-high-tight-f235.jpg", 235),
    ("Left Above Rim", "amen732-native-left-above-rim-f247.jpg", 247),
    ("Right Above Rim", "amen732-native-right-above-rim-f234.jpg", 234),
    ("Left Slash", "amen732-native-left-slash-f221.jpg", 221),
    ("Right Slash", "amen732-native-right-slash-f211.jpg", 211),
]
ANGLES = list(range(-180,180,10))
DETAIL_ANGLES = [0,5,10,15,20,25,45,60,90,120,150,180,-5,-10,-15,-20,-25,-45,-60,-90,-120,-150]
MODEL = "depth-anything/DA3-SMALL"
SOURCE_TYPE = "ORIGINAL_NBA_NATIVE_VIDEO_JPEG_EXPORT"
EVIDENCE = "PROVISIONAL_FREEZE_ALIGNMENT_UNCERTIFIED"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rotation_y(deg):
    theta=math.radians(deg); c,s=math.cos(theta),math.sin(theta)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]],dtype=np.float64)

def project_source_points(pred, stride=2):
    im=np.asarray(pred.processed_images)
    z=np.asarray(pred.depth)
    ext=np.asarray(pred.extrinsics)
    ins=np.asarray(pred.intrinsics)
    if im.ndim!=4 or z.ndim!=3 or len(im)!=len(z) or len(ext)!=len(im):
        raise RuntimeError("INVALID_DA3_OUTPUT_SHAPES")
    if ext.shape[1:]==(4,4):ext=ext[:,:3,:]
    if ext.shape[1:]!=(3,4) or ins.shape[1:]!=(3,3):
        raise RuntimeError("INVALID_DA3_CAMERA_SHAPES")
    h,w=z.shape[1:];yy,xx=np.mgrid[0:h:stride,0:w:stride]
    pix=np.stack([xx.ravel(),yy.ravel(),np.ones(xx.size)],axis=1)
    pts=[];rgb=[]
    for i in range(len(im)):
        d=z[i,::stride,::stride].reshape(-1).astype(np.float64)
        valid=np.isfinite(d)&(d>1e-6)
        rays=pix[valid]@np.linalg.inv(ins[i]).T
        pc=rays*d[valid,None]
        R=ext[i,:3,:3];t=ext[i,:3,3]
        xyz=(pc-t)@R
        color=im[i,::stride,::stride].reshape(-1,3)[valid]
        finite=np.all(np.isfinite(xyz),axis=1)
        pts.append(xyz[finite]);rgb.append(color[finite])
    return np.concatenate(pts), np.concatenate(rgb), ext, ins, im

def render(points,colors,R,t,K,hw):
    h,w=hw
    xyz=points@R.T+t
    positive=np.isfinite(xyz).all(1)&(xyz[:,2]>1e-6)
    xyz=xyz[positive];color=colors[positive]
    xyzpx=xyz@K.T
    uv=xyzpx[:,:2]/xyzpx[:,2,None]
    ok=np.isfinite(uv).all(1)
    uv=uv[ok];xyz=xyz[ok];color=color[ok]
    x=np.rint(uv[:,0]).astype(np.int32);y=np.rint(uv[:,1]).astype(np.int32)
    inside=(x>=0)&(x<w)&(y>=0)&(y<h)
    x=x[inside];y=y[inside];depth=xyz[inside,2];color=color[inside]
    flat=y*w+x
    sort=np.argsort(depth,kind="stable")
    _,where=np.unique(flat[sort],return_index=True)
    chosen=sort[where]
    canvas=np.zeros((h*w,3),dtype=np.uint8)
    canvas[flat[chosen]]=color[chosen]
    supported=np.zeros(h*w,dtype=np.uint8)
    supported[flat[chosen]]=255
    # Presentation-only splat footprint, not new SOURCE pixels or verified mesh.
    # All offsets use one global per-pixel nearest-Z occlusion comparison.
    expanded_idx=[];expanded_depth=[];expanded_rgb=[]
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            sx=x+dx;sy=y+dy
            valid=(sx>=0)&(sx<w)&(sy>=0)&(sy<h)
            expanded_idx.append(sy[valid]*w+sx[valid])
            expanded_depth.append(depth[valid])
            expanded_rgb.append(color[valid])
    fi=np.concatenate(expanded_idx)
    dz=np.concatenate(expanded_depth)
    cols=np.concatenate(expanded_rgb)
    order=np.lexsort((dz,fi))
    ids,pos=np.unique(fi[order],return_index=True)
    canvas[ids]=cols[order[pos]]
    return canvas.reshape(h,w,3),supported.reshape(h,w)

def run(source:Path,out:Path,model_name:str,process_res:int):
    out.mkdir(parents=True,exist_ok=True)
    sources=[];paths=[]
    native_manifest_path=source/"native_video_extraction_manifest.json"
    from_native=native_manifest_path.is_file()
    provenance=json.loads(native_manifest_path.read_text()) if from_native else None
    for label,filename,frame in VIEWS:
        if from_native:
            entry=provenance["source_frames"][label]
            f=source/entry["decoded_source_png"]
            actual_frame=int(entry["source_native_index"])
            if sha(f)!=entry["decoded_png_sha256"]:
                raise RuntimeError("SOURCE_NATIVE_PNG_SHA_MISMATCH:"+label)
            if not provenance.get("source_original_mp4_SHA_verified"):
                raise RuntimeError("SOURCE_ORIGINAL_VIDEO_SHA_MISSING")
        else:
            f=source/filename;actual_frame=frame;entry={}
        if not f.is_file():raise RuntimeError("MISSING_SOURCE_FRAME:"+filename)
        im=cv2.imread(str(f))
        if im is None or im.shape[:2]!=(540,960):
            raise RuntimeError("INVALID_NATIVE_EXPORT:"+filename)
        sources.append(dict(camera_label=label,filename=f.name,
            native_video_frame_index=actual_frame,original_video_sha256=entry.get("source_video_sha256"),
            native_pts_s=entry.get("pts_time_s"),source_frame_sha256=sha(f),
            lossless_original_mp4_decode=from_native,
            image_pixels=[int(im.shape[1]),int(im.shape[0])],
            same_real_world_exposure_certified=False))
        paths.append(str(f))
    import torch
    from depth_anything_3.api import DepthAnything3
    torch.set_num_threads(3)
    t0=time.time()
    model=DepthAnything3.from_pretrained(model_name).to(device="cpu").eval()
    with torch.inference_mode():
        pred=model.inference(image=paths,process_res=process_res,
             process_res_method="upper_bound_resize",use_ray_pose=False)
    runtime=round(time.time()-t0,2)
    pts,rgb,ext,K,images=project_source_points(pred,stride=2)
    if len(pts)<5000:raise RuntimeError("EMPTY_JOINT_GEOMETRY")
    # Strictly a learned *unposed* scene; do not register it as NBA metric geometry.
    ref=0;R=ext[ref,:3,:3].astype(np.float64);t=ext[ref,:3,3].astype(np.float64)
    C=-R.T@t
    ref_points=pts[np.isfinite(pts).all(1)]
    pivot=np.median(ref_points,axis=0)
    hw=tuple(int(v) for v in images.shape[1:3])
    static=[];tiles=[];sweep_images=[]
    cam_centers=np.stack([-e[:3,:3].T@e[:3,3] for e in ext])
    toangle=lambda u: float(np.degrees(np.arctan2(u[0],u[2])))
    base=toangle(C-pivot)
    headings=[float((toangle(cc-pivot)-base+180)%360-180) for cc in cam_centers]
    for deg in sorted(set(ANGLES+DETAIL_ANGLES)):
        Q=rotation_y(deg)
        Rt=R@Q.T
        Ct=pivot+Q@(C-pivot)
        tt=-Rt@Ct
        rendered,mask=render(pts,rgb,Rt,tt,K[ref],hw)
        raw_frac=round(float(np.mean(mask>0)),6)
        diag=cv2.cvtColor(rendered,cv2.COLOR_RGB2BGR)
        if deg in DETAIL_ANGLES:
            resized=cv2.resize(diag,(3840,2160),interpolation=cv2.INTER_LANCZOS4)
            cv2.imwrite(str(out/f"amen732-unposed-da3-{deg:+04d}deg-3840x2160.jpg"),
                        resized,[cv2.IMWRITE_JPEG_QUALITY,88])
        cv2.imwrite(str(out/f"amen732-unposed-da3-{deg:+04d}deg-raw-support.png"),mask)
        label=f"MODEL ONLY | {deg} deg | support {raw_frac*100:.1f}% | NOT CERTIFIED"
        thumb=cv2.resize(diag,(480,270),interpolation=cv2.INTER_AREA)
        cv2.putText(thumb,f"{deg:+04d} deg", (12,24),cv2.FONT_HERSHEY_SIMPLEX,.7,(250,250,250),2)
        if deg in ANGLES:sweep_images.append(thumb)
        if deg in (0,5,10,15,20,25):
            tile=cv2.resize(diag,(1920,720),interpolation=cv2.INTER_LANCZOS4)
            cv2.putText(tile,label,(28,45),cv2.FONT_HERSHEY_SIMPLEX,.85,(220,220,240),2)
            tiles.append(tile)
        static.append(dict(angle_deg=deg,raw_reprojected_pixel_fraction=raw_frac,
             input_footage_reprojected=False,
             held_out_camera_validated=False, NBA_geometry_validated=False,
             ball_hand_contact_certified=False,
             novel_view_source_only_qa="DIAGNOSTIC_NOT_ACCEPTED"))
    sheet=np.vstack([np.hstack(tiles[i:i+2]) for i in range(0,6,2)])
    assert sheet.shape[:2]==(2160,3840)
    cv2.imwrite(str(out/"amen732-da3-six-angle-diagnostic-3840x2160.jpg"),
        sheet,[cv2.IMWRITE_JPEG_QUALITY,94])
    if len(sweep_images)==36:
        scan=np.vstack([np.hstack(sweep_images[i:i+6]) for i in range(0,36,6)])
        cv2.imwrite(str(out/"amen732-360deg-model-sweep-3840x2160.jpg"),cv2.resize(scan,(3840,2160),interpolation=cv2.INTER_LANCZOS4),[cv2.IMWRITE_JPEG_QUALITY,91])
    for a in static:
        a["nearest_predicted_source_view_degrees"]=round(min(abs((a["angle_deg"]-h+180)%360-180) for h in headings),2)
        a["model_camera_cone_30deg_candidate"]=a["nearest_predicted_source_view_degrees"]<=30
        a["presentation_method"]="3x3 global-Z surfel sampling; not source-qualified geometry"
    ray_vectors=cam_centers-pivot[None,:]
    ray_lengths=np.linalg.norm(ray_vectors,axis=1)
    ray_dirs=ray_vectors/np.maximum(ray_lengths[:,None],1e-6)
    source_pair_rays=[]
    for i in range(len(cam_centers)):
        for j in range(i+1,len(cam_centers)):
            angle=float(np.degrees(np.arccos(np.clip(ray_dirs[i]@ray_dirs[j],-1,1))))
            baseline=float(np.linalg.norm(cam_centers[i]-cam_centers[j]))
            source_pair_rays.append({"camera_a":VIEWS[i][0],"camera_b":VIEWS[j][0],
                "angular_separation_at_model_scene_pivot_degrees":round(angle,2),
                "camera_center_baseline_over_scene_radius":round(baseline/max(float(np.median(ray_lengths)),1e-6),3)})
    max_three_d_view_separation=max(x["angular_separation_at_model_scene_pivot_degrees"] for x in source_pair_rays)
    byangle={q["angle_deg"]:q for q in static}
    coverage={}
    for direct in (-1,1):
        contiguous=0
        for n in range(0,181,10):
            deg=(n*direct+180)%360-180
            q=byangle.get(deg)
            if q is None or not q["model_camera_cone_30deg_candidate"]:break
            contiguous=n
        coverage[str(direct)]={"candidate_arc_degrees":contiguous,
          "meaning":"geometric camera-cone heuristic only; not verified novel-view quality"}
    np.savez_compressed(out/"amen732-da3-uncalibrated-cameras.npz",
        extrinsics=ext,intrinsics=K,process_resolution=np.array(hw))
    meta=dict(schema="hoopvision.freeview.amen732.unposed_da3_diagnostic.v1",
        game_id=GAME,event_num=EVENT,model=model_name,processing_resolution=process_res,
        model_inference_mode="NO_INPUT_CAMERA_CALIBRATION",
        novel_view_renderer="3x3_depth_sorted_surfel_footprint_presentation_only",
        source_type=('SHA_VERIFIED_NATIVE_MP4_LOSSLESS_FRAME_DECODE' if from_native else SOURCE_TYPE),
        from_full_six_native_videos=bool(from_native),
        source_video_frame_selection_sha_verified=bool(from_native),
        frame_state=EVIDENCE,source_views=sources,
        input_view_count=len(paths),camera_pose_count=len(ext),
        depth_prediction_count=len(pred.depth),model_inference_elapsed_s=runtime,
        shared_geometry_sampled_points=len(pts),
        output_3840x2160=True,angles=static,full_360_diagnostic_sweep=True,
        estimated_source_camera_headings_deg=[round(h,2) for h in headings],
        model_camera_center_ray_pairs=source_pair_rays,
        largest_model_camera_ray_separation_deg=max_three_d_view_separation,
        contiguous_candidate_arc_each_direction=coverage,
        maximum_faithful_arc="UNKNOWN_NOT_INDEPENDENTLY_VALIDATED",
        source_support_status="NOT_VERIFIED",
        camera_metric_status="NOT_VERIFIED", first_contact="NOT_VERIFIED",
        artifact_status="DIAGNOSTIC_MODEL_RENDER_ONLY",
        certified_25deg_freeview=False,
        note="No direct RGB pixels prove newly visible surfaces. No model pixel counts as SOURCE support.")
    (out/"amen732-da3-sixview-research-qa.json").write_text(json.dumps(meta,indent=2)+"\n")
    print("AMEN732_UNPOSED_DA3_REAL_SIXVIEW_DIAGNOSTIC",json.dumps({
        "views":len(paths),"model":model_name,"points":len(pts),
        "timing_s":runtime,"candidate_arc":coverage,
        "raw_support_at_angles":[a["raw_reprojected_pixel_fraction"] for a in static],
        "certified":False}),flush=True)
    return meta

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--model",default=MODEL)
    p.add_argument("--process-res",type=int,default=336)
    a=p.parse_args();run(a.source,a.out,a.model,a.process_res)
