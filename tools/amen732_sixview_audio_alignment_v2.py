#!/usr/bin/env python3
"""Original six NBA video audio: bounded multi-edge native-timing alignment.

Produces source/time metadata only; never copies original frames, audio samples,
or signed source URLs into public QA. Video time origins are independent.
Audio similarity can propose *coarse* offsets but CANNOT certify hand-ball
contact or a single physical exposure. False matches remain explicit.
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfiltfilt, correlate

LABELS=("Broadcast","High Tight","Left Above Rim","Right Above Rim","Left Slash","Right Slash")
GAME="0022600009"; EVENT=732
SAMPLE_RATE=8000; ENVELOPE_HZ=100; MAX_LAG_S=5.0
BROADCAST_SEED_S=9.1041
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for p in iter(lambda:f.read(1<<20),b""):h.update(p)
    return h.hexdigest()
def audio_decode(src,ffmpeg):
    # No audio is an informative result, not permission to invent sync.
    r=subprocess.run([ffmpeg,"-nostdin","-v","error","-i",str(src),"-map","0:a:0",
        "-ac","1","-ar",str(SAMPLE_RATE),"-f","f32le","-"],
        capture_output=True,timeout=35)
    if r.returncode!=0 or len(r.stdout)<80000:
        return None
    x=np.frombuffer(r.stdout,dtype="<f4").copy()
    if not np.isfinite(x).all():return None
    if np.std(x)<1e-6:return None
    sos=butter(3,[250,2600],btype="bandpass",fs=SAMPLE_RATE,output="sos")
    y=sosfiltfilt(sos,x).astype(np.float32)
    # Silence and camera-specific background frequencies become low weight.
    n=SAMPLE_RATE//ENVELOPE_HZ
    y=y[:len(y)//n*n].reshape(-1,n)
    env=np.sqrt(np.mean(y*y,axis=1)+1e-10)
    # Sound-event novelty, not absolute loudness/volume differences.
    env=np.log1p(40*env)
    env-=np.median(env)
    q=np.percentile(abs(env),90)
    env=np.clip(env/max(q,1e-5),-4,4)
    return env.astype(np.float32)
def pairwise(a,b,search=MAX_LAG_S):
    # lag>0 means observed audio in b is later than matching audio in a:
    # camera B native timestamp = camera A timestamp + lag.
    c=correlate(b,a,mode="full",method="fft")
    lags=np.arange(-(len(a)-1),len(b),dtype=int)
    ok=(np.abs(lags)<=int(search*ENVELOPE_HZ))
    lags=lags[ok];cc=c[ok]
    if not len(cc):return None
    order=np.argsort(cc)[::-1]
    nmin=int(ENVELOPE_HZ*4.0)
    best=None
    for k in order[:60]:
        lag=int(lags[k])
        aa=max(0,-lag);bb=max(0,lag)
        n=min(len(a)-aa,len(b)-bb)
        if n<nmin:continue
        x=a[aa:aa+n].astype(float);y=b[bb:bb+n].astype(float)
        x-=x.mean();y-=y.mean()
        corr=float(np.dot(x,y)/max(np.linalg.norm(x)*np.linalg.norm(y),1e-9))
        if best is None or corr>best[1]:
            best=(lag,corr,n)
    if best is None:return None
    lag,corr,n=best
    # Match uniqueness, exclude correlated alternatives within 0.2 seconds.
    excl=np.abs(lags-lag)>=int(.20*ENVELOPE_HZ)
    alternative=float(np.max(cc[excl])) if np.any(excl) else float(cc.min())
    best_raw=float(cc[np.argmin(abs(lags-lag))])
    contrast=(best_raw-alternative)/max(abs(best_raw),1e-5)
    return {"relative_b_audio_delay_s":round(lag/ENVELOPE_HZ,4),
        "pearson_r":round(corr,5),"peak_contrast":round(float(contrast),5),
        "overlap_s":round(n/ENVELOPE_HZ,3),
        "tentative":True,"accepted_edge":bool(corr>=0.40 and contrast>=0.05)}
def solve_graph(labels,edges):
    n=len(labels); A=[];b=[];w=[]
    for e in edges:
        if not e.get("accepted_edge"):continue
        row=np.zeros(n-1)
        ia=labels.index(e["camera_a"]); ib=labels.index(e["camera_b"])
        if ia!=0:row[ia-1]-=1
        if ib!=0:row[ib-1]+=1
        A.append(row);b.append(e["relative_b_audio_delay_s"])
        w.append(max(e["pearson_r"],.01)**2)
    if not A:return {"connected":False,"solved_camera_count":1,"reason":"NO_ACCEPTED_AUDIO_EDGES"}
    A=np.stack(A);b=np.array(b);w=np.array(w)
    from collections import deque
    adj={k:set() for k in labels}
    for e in edges:
        if e.get("accepted_edge"):
            adj[e["camera_a"]].add(e["camera_b"]);adj[e["camera_b"]].add(e["camera_a"])
    seen={labels[0]};Q=deque([labels[0]])
    while Q:
        for nxt in adj[Q.popleft()]:
            if nxt not in seen:seen.add(nxt);Q.append(nxt)
    if len(seen)!=n:
        return {"connected":False,"solved_camera_count":len(seen),
                "reason":"CAMERA_AUDIO_GRAPH_DISCONNECTED",
                "unconnected_cameras":[x for x in labels if x not in seen]}
    weights=np.sqrt(w)[:,None]
    sol=np.linalg.lstsq(weights*A,weights[:,0]*b,rcond=None)[0]
    pred=A@sol;err=pred-b
    offsets=np.r_[0,sol]
    return {"connected":True,"solved_camera_count":n,
        "relative_audio_delay_vs_broadcast_s":{k:round(float(v),4) for k,v in zip(labels,offsets)},
        "pairwise_residual_median_ms":round(float(np.median(abs(err)))*1000,2),
        "pairwise_residual_max_ms":round(float(np.max(abs(err)))*1000,2),
        "cycle_consistency_40ms_pass":bool(np.max(abs(err))<=.04),
        "audio_alignment_status":"COARSE_UNCERTIFIED_NOT_EXPOSURE_TRUTH"}
def qa(root,ffmpeg,seed):
    f=root/"source_manifest.json";p=root/"native_presentation_timestamps.json"
    manifest=json.loads(f.read_text());pts=json.loads(p.read_text())
    assert manifest["event"]["game_id"]==GAME and int(manifest["event"]["event_num"])==EVENT
    files={d["label"]:d for d in manifest["feeds"]}
    audios={};sources=[]
    for label in LABELS:
        rec=files[label];video=root/rec["file"]
        if not video.is_file():raise RuntimeError("SOURCE_VIDEO_MISSING_"+label)
        h=digest(video)
        if h!=rec["native_media_sha256"]:raise RuntimeError("SOURCE_VIDEO_SHA_INVALID_"+label)
        if pts[label]["clip_sha256"]!=h:raise RuntimeError("SOURCE_PTS_HASH_INVALID_"+label)
        audios[label]=audio_decode(video,ffmpeg)
        sources.append({"camera":label,"source_mp4_sha256":h,
                        "native_frame_count":len(pts[label]["frames"]),
                        "original_audio_detected":audios[label] is not None})
    edges=[]
    for i,a in enumerate(LABELS):
        for b in LABELS[i+1:]:
            r=pairwise(audios[a],audios[b]) if audios[a] is not None and audios[b] is not None else None
            edges.append({"camera_a":a,"camera_b":b,**(r or {"accepted_edge":False,"reason":"AUDIO_MISSING_OR_NO_MATCH"})})
    fitted=solve_graph(list(LABELS),edges)
    candidates={}
    if fitted.get("connected") and fitted.get("cycle_consistency_40ms_pass"):
        for label,lag in fitted["relative_audio_delay_vs_broadcast_s"].items():
            times=np.array([float(r["pts_time_s"]) for r in pts[label]["frames"]])
            target=seed+lag
            idx=int(np.argmin(abs(times-target)))
            candidates[label]={"frame_index":idx,"native_pts_s":round(float(times[idx]),6),
                "model_audio_aligned_exposure_target_pts_s":round(target,6),
                "nearest_frame_time_residual_ms":round(1000*float(times[idx]-target),2),
                "certified_same_exposure":False}
    return {"schema":"hoopvision.freeview.amen732.sixview_audio_proposed_sync.v2",
        "game_id":GAME,"event_num":EVENT,"source_cameras":sources,
        "input_original_native_full_mp4_count":6,
        "broadcast_candidate_pts_s":seed,"audio_pipeline":"250-2600Hz event-envelope 100Hz; FFT six-view pairwise cross-correlation; weighted cycle graph",
        "pairwise_edge_count":len(edges),"accepted_edges":sum(e["accepted_edge"] for e in edges),
        "edges":edges,"graph":fitted,"provisional_frame_candidates":candidates,
        "actual_first_hand_ball_touch_certified":False,
        "same_physical_exposure_certified":False,
        "camera_optics_certified":False,
        "model_3d_source_reprojection_certified":False,
        "next_gate":"Compare actor/ball/source pixels over candidate frames and certify clock/frame before any free-view reconstruction"}
def selftest():
    rng=np.random.default_rng(11);x=rng.standard_normal(1400)
    x=np.convolve(x,np.ones(9)/9,mode="same")
    offsets=[0,15,-40,57,-12,22]
    vals={}
    for n,o in zip(LABELS,offsets):
        v=np.zeros_like(x)
        if o>=0:v[o:]=x[:len(x)-o]
        else:v[:o]=x[-o:]
        vals[n]=v+0.003*rng.standard_normal(len(x))
    got=[]
    for i,a in enumerate(LABELS):
        for b in LABELS[i+1:]:
            m=pairwise(vals[a],vals[b],5)
            assert m and abs(100*m["relative_b_audio_delay_s"]-(offsets[LABELS.index(b)]-offsets[LABELS.index(a)]))<=1,(a,b,m)
            got.append(dict(camera_a=a,camera_b=b,**m))
    g=solve_graph(list(LABELS),got)
    assert g["connected"] and g["cycle_consistency_40ms_pass"],g
    print("AMEN732_SIXVIEW_AUDIO_DELAY_SIGN_AND_CYCLE_SYNTHETIC_PASS")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path);p.add_argument("--out",type=Path)
    p.add_argument("--ffmpeg",default="ffmpeg")
    p.add_argument("--broadcast-seed",type=float,default=BROADCAST_SEED_S)
    p.add_argument("--selftest",action="store_true")
    a=p.parse_args()
    if a.selftest:selftest();return
    if not a.source or not a.out:p.error("--source and --out required")
    result=qa(a.source,a.ffmpeg,a.broadcast_seed)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print("AMEN732_SIXVIEW_REAL_MP4_AUDIO_GRAPH",result["graph"]["reason"] if "reason" in result["graph"] else "CONNECTED",
        "accepted_edges",result["accepted_edges"],"camera_count",result["graph"]["solved_camera_count"],
        "cycle_ms",result["graph"].get("pairwise_residual_max_ms"),
        "certified",result["same_physical_exposure_certified"],flush=True)
if __name__=="__main__":main()
