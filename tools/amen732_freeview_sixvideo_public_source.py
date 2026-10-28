#!/usr/bin/env python3
"""Research-only uncalibrated six-video free-viewpoint NBA event proof.

Six independent OFFICIAL public angle videos are fetched ephemerally, three
neighbouring original frame sets are reconstructed in 3D, and a frozen unified
scene is rendered into two moving-camera MP4s. No private repository media,
SDK coordinates or other private data enters this public file. Videos and
diagnostic geometry must be stored only in a private output destination.
"""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,html,json,math,re,subprocess,time
import urllib.parse,urllib.request
from pathlib import Path
import cv2,numpy as np

GAME="0022600009"
EVENT=732
LABELS=("Broadcast","High Tight","Left Above Rim","Right Above Rim","Left Slash","Right Slash")
NOMINAL=(275,235,247,234,221,211)
MODEL="depth-anything/DA3-BASE"
HEADERS={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/131 Safari/537.36",
  "Referer":"https://clips.nba.com/","Accept":"*/*"}
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()
def http_get(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=50) as f:return f.read()
def join(base,path):
    p=urllib.parse.urlsplit(base);q=urllib.parse.urlsplit(urllib.parse.urljoin(base,path))
    return urllib.parse.urlunsplit(q._replace(query=q.query or p.query))
def get_views():
    page="https://clips.nba.com/?gameNo="+GAME+"&eventNum="+str(EVENT)+"&source=grs"
    html_source=http_get(page).decode("utf8","replace")
    available={}
    for m in re.finditer(r'<option\s+value="([^"]+)"([^>]*)>(.*?)</option>',
                         html_source,flags=re.I|re.S):
        u=html.unescape(m.group(1));k=re.sub('<[^>]+>','',html.unescape(m.group(3))).strip()
        if 'lrmedia.nba.com' in u and '.m3u8' in u:
            available[k]=u
    if not all(k in available for k in LABELS):
        raise RuntimeError("OFFICIAL_SIX_NATIVE_CAMERAS_NOT_PRESENT")
    return available
def parse_media(url,level=0):
    if level>3:raise RuntimeError("HLS_NEST_TOO_DEEP")
    lines=[s.strip() for s in http_get(url).decode("utf8","replace").splitlines() if s.strip()]
    variants=[]
    for i,s in enumerate(lines):
        if s.startswith("#EXT-X-STREAM-INF"):
            m=re.search(r'BANDWIDTH=(\d+)',s)
            for nxt in lines[i+1:]:
                if not nxt.startswith("#"):
                    variants.append((int(m.group(1)) if m else 0,join(url,nxt)));break
    if variants:return parse_media(max(variants)[1],level+1)
    init=[];segs=[]
    for s in lines:
        if s.startswith("#EXT-X-MAP:"):
            m=re.search(r'URI="([^"]+)"',s)
            if m:init.append(join(url,m.group(1)))
        elif not s.startswith("#"):segs.append(join(url,s))
    if len(segs)==0:raise RuntimeError("NO_NBA_HLS_VIDEO_SEGMENTS")
    return init+segs
def download_one(label,url,folder,ffmpeg):
    segments=parse_media(url)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        chunks=list(pool.map(http_get,segments))
    raw=folder/(label.lower().replace(" ","-")+".hls.part")
    with raw.open("wb") as out:
        for part in chunks:out.write(part)
    target=folder/(label.lower().replace(" ","-")+".mp4")
    subprocess.run([ffmpeg,"-nostdin","-y","-loglevel","error",
                    "-i",str(raw),"-map","0:v:0","-c:v","copy",
                    "-movflags","+faststart",str(target)],check=True)
    raw.unlink(missing_ok=True)
    cap=cv2.VideoCapture(str(target))
    if not cap.isOpened():raise RuntimeError("DECODE_FAILURE")
    n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if n<290 or width<600 or height<350:
        raise RuntimeError("UNEXPECTED_PUBLIC_NBA_SOURCE_FRAME_ENVELOPE")
    return target,{"label":label,"sha256":sha(target),"frame_count":n,
                   "resolution":[width,height]}
def get_frames(video,indices):
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise RuntimeError("SOURCE_VIDEO_READ_FAIL")
    frames={}
    for i in range(max(indices)+1):
        ok,im=cap.read()
        if not ok:raise RuntimeError("SOURCE_DECODE_MISSING_FRAME")
        if i in indices:frames[i]=im
    cap.release()
    return frames
def assemble_point_scene(pred):
    image=np.asarray(pred.processed_images)
    depth=np.asarray(pred.depth)
    E=np.asarray(pred.extrinsics);K=np.asarray(pred.intrinsics)
    if E.shape[1:]==(4,4):E=E[:,:3,:]
    if E.shape[1:]!=(3,4):raise RuntimeError("PREDICTED_POSE_INVALID")
    h,w=depth.shape[1:]
    yy,xx=np.mgrid[0:h:2,0:w:2]
    px=np.stack([xx.ravel(),yy.ravel(),np.ones(xx.size)],axis=1)
    xyzs=[];cols=[]
    for v in range(len(image)):
        z=depth[v,::2,::2].reshape(-1)
        valid=np.isfinite(z)&(z>0.00001)
        rays=px[valid]@np.linalg.inv(K[v]).T
        camera=rays*z[valid,None]
        xyz=(camera-E[v,:3,3])@E[v,:3,:3]
        col=image[v,::2,::2].reshape(-1,3)[valid]
        finite=np.isfinite(xyz).all(axis=1)
        xyzs.append(xyz[finite]);cols.append(col[finite])
    return np.concatenate(xyzs).astype(np.float32),np.concatenate(cols),E,K,(h,w)
def orbit_point_pivot(pred,K,E):
    v=4
    h,w=pred.depth.shape[1:]
    sample=pred.depth[v,int(.2*h):int(.65*h),int(.5*w):int(.7*w)]
    sample=sample[np.isfinite(sample)&(sample>0)]
    if sample.size<30:raise RuntimeError("EVENT_ACTOR_DEPTH_MISSING")
    z=float(np.median(sample))
    x=np.array([w*.59,h*.40,1.0])
    camera=np.linalg.inv(K[v])@x*z
    return (camera-E[v,:3,3])@E[v,:3,:3]
def yaw(deg):
    a=math.radians(deg);c,s=math.cos(a),math.sin(a)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]])
def render(points,colors,R,t,K,hw):
    h,w=hw;V=points@R.T+t
    valid=np.isfinite(V).all(axis=1)&(V[:,2]>0)
    V=V[valid];colors=colors[valid]
    proj=V@K.T;uv=proj[:,:2]/proj[:,2,None]
    ok=np.isfinite(uv).all(axis=1)
    xx=np.rint(uv[ok,0]).astype(int);yy=np.rint(uv[ok,1]).astype(int)
    zz=V[ok,2];rgb=colors[ok]
    outputs=[]
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            X=xx+dx;Y=yy+dy
            v=(X>=0)&(X<w)&(Y>=0)&(Y<h)
            outputs.append((Y[v]*w+X[v],zz[v],rgb[v]))
    ix=np.concatenate([p[0] for p in outputs]);depth=np.concatenate([p[1] for p in outputs])
    col=np.concatenate([p[2] for p in outputs])
    order=np.lexsort((depth,ix));idx,first=np.unique(ix[order],return_index=True)
    image=np.zeros((h*w,3),dtype=np.uint8);image[idx]=col[order[first]]
    return image.reshape(h,w,3)
def smooth(a,b,n,return_path):
    def easing(t):return .5-.5*math.cos(math.pi*t)
    if return_path:
        m=n//2
        return [a+(b-a)*easing(i/max(1,m-1)) for i in range(m)]+[
          b+(a-b)*easing(i/max(1,n-m-1)) for i in range(n-m)]
    return [a+(b-a)*easing(i/max(1,n-1)) for i in range(n)]
def make_orbit(out,name,points,colors,E,K,pivot,hw,angles,ffmpeg):
    p=out/(name+"_frames");p.mkdir(parents=True,exist_ok=True)
    v=4;R=E[v,:3,:3];t=E[v,:3,3];C=-R.T@t
    for i,deg in enumerate(angles):
        Q=yaw(deg);Rt=R@Q.T;Ct=pivot+Q@(C-pivot);tt=-Rt@Ct
        im=render(points,colors,Rt,tt,K[v],hw)
        bgr=cv2.cvtColor(im,cv2.COLOR_RGB2BGR)
        cv2.putText(bgr,"MODEL 6-VIEW 3D / UNVERIFIED", (5,18),
                    cv2.FONT_HERSHEY_SIMPLEX,.33,(255,255,255),1)
        cv2.putText(bgr,f"Camera yaw: {deg:+.1f}", (5,35),
                    cv2.FONT_HERSHEY_SIMPLEX,.32,(255,255,255),1)
        cv2.imwrite(str(p/f"f_{i:04d}.png"),bgr)
    dst=out/(name+"-3840x2160.mp4")
    subprocess.run([ffmpeg,"-nostdin","-y","-loglevel","error",
                    "-framerate","24","-i",str(p/"f_%04d.png"),
                    "-vf","scale=3840:2160:flags=lanczos",
                    "-c:v","libx264","-preset","veryfast","-crf","23",
                    "-pix_fmt","yuv420p","-movflags","+faststart",str(dst)],check=True)
    if dst.stat().st_size<10000:raise RuntimeError("EMPTY_RENDERED_MP4")
    return {"file":dst.name,"sha256":sha(dst),"size":dst.stat().st_size,
            "frames":len(angles),"yaw_range":[round(min(angles),2),round(max(angles),2)],
            "native_mp4_pixels_not_4k":True}
def main(out):
    import imageio_ffmpeg,torch
    from depth_anything_3.api import DepthAnything3
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    out.mkdir(parents=True,exist_ok=True)
    native=out/"private_source_runtime";native.mkdir(exist_ok=True)
    t0=time.time()
    options=get_views()
    videos=[]
    for label in LABELS:
        path,qa=download_one(label,options[label],native,ffmpeg)
        videos.append((path,qa))
        print("PUBLIC_NBA_NATIVE_VIDEO_DECODED",label,qa["frame_count"],flush=True)
    torch.set_num_threads(3)
    model=DepthAnything3.from_pretrained(MODEL).to("cpu").eval()
    cache={}
    for i,(path,qa) in enumerate(videos):
        ids=[NOMINAL[i]-3,NOMINAL[i],NOMINAL[i]+3]
        cache[i]=get_frames(path,ids)
    stages=[];freezepose=None
    for shift in (-3,0,3):
        files=[];local_record=[]
        for i in range(6):
            frame=NOMINAL[i]+shift
            p=native/(f"camera{i}-frame{frame}.png")
            cv2.imwrite(str(p),cache[i][frame])
            files.append(str(p))
            local_record.append({"camera_label":LABELS[i],"frame":frame,"sha256":sha(p)})
        with torch.inference_mode():
            prediction=model.inference(image=files,process_res=448,
                    process_res_method="upper_bound_resize",use_ray_pose=False)
        pts,cols,E,K,hw=assemble_point_scene(prediction)
        assert len(E)==6 and len(pts)>10000
        camera_centers=np.stack([-e[:3,:3].T@e[:3,3] for e in E])
        pivot=np.median(pts,axis=0)
        bearings=camera_centers-pivot;bearings/=np.maximum(np.linalg.norm(bearings,axis=1,keepdims=True),1e-6)
        separation=max(float(np.degrees(np.arccos(np.clip(bearings[i]@bearings[j],-1,1))))
            for i in range(6) for j in range(i+1,6))
        stages.append({"source_frame_relative_offset":shift,"source_frames":local_record,
              "predicted_3d_points":len(pts),"camera_count":len(E),
              "estimated_camera_ray_spread_deg":round(separation,2)})
        if shift==0:freezepose=(pts,cols,E,K,orbit_point_pivot(prediction,K,E),hw)
        print("SIX_NBA_VIDEOS_JOINT_3D_TEMPORAL_STAGE",shift,len(pts),flush=True)
    pts,cols,E,K,pivot,hw=freezepose
    outputs=[
      make_orbit(out,"amen732-sixvideo-unposed-170deg",pts,cols,E,K,pivot,hw,smooth(-90,80,96,True),ffmpeg),
      make_orbit(out,"amen732-sixvideo-unposed-360deg",pts,cols,E,K,pivot,hw,smooth(-180,180,96,False),ffmpeg)]
    qa={"schema":"hoopvision.amen732.public_official_sixvideo_freeview.v1",
       "game_id":GAME,"event_num":EVENT,"source":"OFFICIAL_NBA_SIX_NATIVE_HLS_CAMERA_VIDEOS",
       "original_source_count":6,"video_sha256":[qa["sha256"] for _,qa in videos],
       "native_source_frames_evaluated":18,"time_strata":stages,
       "precalibration_supplied":False,"model":MODEL,
       "moving_camera_mp4_outputs":outputs,"codec_delivery":[3840,2160],
       "time_s":round(time.time()-t0,2),
       "same_physical_instant_verified":False,
       "real_contact_frame_certified":False,
       "max_physically_faithful_arc_deg":None,
       "scientific_status":"DIAGNOSTIC_ONLY_NO_VALIDATED_FREEVIEW",
       "original_source_and_video_outputs_public":False}
    (out/"amen732-six-native-public-source-research-qa.json").write_text(json.dumps(qa,indent=2)+"\n")
    print("SIX_OFFICIAL_NBA_VIDEOS_3D_MP4_RENDER_EXECUTED",
          len(outputs),"unverified",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    args=p.parse_args();main(args.out)
