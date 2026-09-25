#!/usr/bin/env python3
import csv,json,sys
from pathlib import Path
from collections import Counter
root=Path(sys.argv[1])
def rows(p):
    with open(p,newline="") as f: return list(csv.DictReader(f))
obs=rows(root/"identity_segments/uniform_observations.csv")
segs=rows(root/"identity_segments/segments.csv")
assign=rows(root/"global_identity/identity_assignments.csv")
links=rows(root/"sam31/continuity_links.csv")
groups=rows(root/"sam31/continuity_groups.csv")
anchors=json.load(open(root/"semantic_anchors.json"))
pid=1641711

print("ANCHORS",json.dumps(anchors,indent=2))
print("ACCEPTED_SAM_LINKS")
for r in links:
    if str(r.get("accepted","")).lower() in {"true","1"}: print(json.dumps(r,sort_keys=True))
print("SAM_GROUPS",json.dumps(groups,indent=2))

for sid in (3,7,8,48,49):
    s=next((r for r in segs if int(float(r["segment_id"]))==sid),None)
    q=[r for r in obs if int(float(r["identity_segment_id"]))==sid]
    print("SEGMENT",sid,json.dumps(s,sort_keys=True) if s else None)
    print("CLUSTERS",dict(Counter(r.get("uniform_cluster","") for r in q)),"AMBIG",dict(Counter(r.get("ambiguous","") for r in q)))

print("DICK_ASSIGNMENTS")
for r in assign:
    if int(float(r.get("player_id") or -1))==pid and 8.5<=float(r["time_s"])<=12.5:
        print(json.dumps({k:r.get(k) for k in ("time_s","source_track_id","identity_segment_id","safe","global_margin","ambiguous","team")},sort_keys=True))

print("TRACK0_3_OBS")
for r in obs:
    if int(float(r["source_track_id"])) in {0,3} and 8.5<=float(r["time_s"])<=12.5:
        print(json.dumps({k:r.get(k) for k in ("time_s","source_track_id","identity_segment_id","uniform_cluster","cluster_conf","ambiguous","conf","x1","y1","x2","y2")},sort_keys=True))


print("TRACK2_3_COMPARISON")
for r in obs:
    if int(float(r["source_track_id"])) in {2,3} and 8.8<=float(r["time_s"])<=12.2:
        print(json.dumps({k:r.get(k) for k in ("time_s","source_track_id","identity_segment_id","uniform_cluster","cluster_conf","ambiguous","conf","x1","y1","x2","y2")},sort_keys=True))

print("TRACK2_3_ASSIGNMENTS")
for r in assign:
    if int(float(r["source_track_id"])) in {2,3} and 8.8<=float(r["time_s"])<=12.2:
        print(json.dumps({k:r.get(k) for k in ("time_s","player_id","source_track_id","identity_segment_id","safe","global_margin","ambiguous","team","evidence_conflict")},sort_keys=True))

print("TRACK2_3_SEGMENTS")
for r in segs:
    if int(float(r.get("source_track_id") or -1)) in {2,3}:
        end=float(r["end_s"]); start=float(r["start_s"])
        if end>=8.8 and start<=12.2:
            print(json.dumps(r,sort_keys=True))


print("TRACK3_OCR_EVIDENCE")
ocrp=root/"identity_ocr/ocr_evidence.json"
if ocrp.exists():
    raw=json.load(open(ocrp))
    for rec in raw:
        try: sid=int(float(rec.get("track_id")))
        except: continue
        if sid in {41,42,43,44,45,46,47,48,49,50}:
            print(json.dumps(rec,sort_keys=True))
print("TRACK3_TRACK_IDENTITY")
tip=root/"identity_ocr/track_identity.csv"
if tip.exists():
    for r in rows(tip):
        try: sid=int(float(r.get("track_id")))
        except: continue
        if sid in {41,42,43,44,45,46,47,48,49,50}:
            print(json.dumps(r,sort_keys=True))
print("TRACK3_ALL_ASSIGNMENTS")
for r in assign:
    if int(float(r["source_track_id"]))==3 and 5.5<=float(r["time_s"])<=14.3:
        print(json.dumps({k:r.get(k) for k in ("time_s","player_id","source_track_id","identity_segment_id","safe","global_margin","ambiguous","team","evidence_conflict")},sort_keys=True))


print("SEGMENT36_IDENTITY_EVIDENCE")
ocrp=root/"identity_ocr/ocr_evidence.json"
if ocrp.exists():
    for rec in json.load(open(ocrp)):
        try: sid=int(float(rec.get("track_id")))
        except: continue
        if sid==36:
            print("OCR36",json.dumps(rec,sort_keys=True))
tip=root/"identity_ocr/track_identity.csv"
if tip.exists():
    for r in rows(tip):
        try: sid=int(float(r.get("track_id")))
        except: continue
        if sid==36:
            print("TRACK_ID36",json.dumps(r,sort_keys=True))
for r in assign:
    if int(float(r.get("identity_segment_id") or -1))==36:
        print("ASSIGN36",json.dumps({k:r.get(k) for k in ("time_s","player_id","player_name","jersey","source_track_id","identity_segment_id","safe","global_margin","ambiguous","team","direct_ocr","jersey_support")},sort_keys=True))


print("DEFENDER_TEMPORAL_GEOMETRY")
import math
bytime={}
for r in obs:
    t=round(float(r["time_s"]),4)
    bytime.setdefault(t,{})[int(float(r["source_track_id"]))]=r
def center(r):
    return ((float(r["x1"])+float(r["x2"]))*0.5,(float(r["y1"])+float(r["y2"]))*0.5)
def h(r): return max(1.0,float(r["y2"])-float(r["y1"]))
for cand in (0,2,3,4,10,12):
    vals=[]
    for t,m in sorted(bytime.items()):
        if 8.9<=t<=9.8 and 5 in m and cand in m:
            a=center(m[5]); b=center(m[cand])
            d=math.hypot(a[0]-b[0],a[1]-b[1])/max(1.0,0.5*(h(m[5])+h(m[cand])))
            vals.append((t,d,str(m[cand].get("ambiguous")),float(m[cand].get("cluster_conf") or 0)))
    if vals:
        ds=[x[1] for x in vals]
        print("CAND",cand,"N",len(vals),"MEAN",round(sum(ds)/len(ds),4),"MIN",round(min(ds),4),"MAX",round(max(ds),4),"SERIES",json.dumps(vals))


print("TRACK0_POSITIVE_PROVENANCE")
track0_segments=sorted({int(float(r["identity_segment_id"])) for r in obs if int(float(r["source_track_id"]))==0})
print("TRACK0_SEGMENT_IDS",track0_segments)
for r in assign:
    if int(float(r["source_track_id"]))==0 and int(float(r.get("player_id") or -1))==pid:
        print("DICK_TRACK0",json.dumps({k:r.get(k) for k in (
            "time_s","player_id","player_name","source_track_id","raw_source_track_id",
            "identity_segment_id","safe","global_margin","ambiguous",
            "positive_identity_evidence","positive_identity_evidence_propagated",
            "semantic_anchor","direct_ocr","jersey_support"
        )},sort_keys=True))
if ocrp.exists():
    for rec in json.load(open(ocrp)):
        try: sid=int(float(rec.get("track_id")))
        except: continue
        if sid in track0_segments:
            print("TRACK0_OCR",json.dumps(rec,sort_keys=True))
if tip.exists():
    for r in rows(tip):
        try: sid=int(float(r.get("track_id")))
        except: continue
        if sid in track0_segments:
            print("TRACK0_IDENTITY_ROW",json.dumps(r,sort_keys=True))
print("TRACK0_SAM_GROUP_ROWS")
for r in groups:
    try: sid=int(float(r.get("identity_segment_id")))
    except: continue
    if sid in track0_segments:
        print(json.dumps(r,sort_keys=True))


print("TRACK2_3_ACTION_ASSOCIATIONS")
assocp=root/"semantic_anchors.associations.csv"
if not assocp.exists():
    print("NO_ASSOCIATIONS_FILE",str(assocp))
else:
    assoc=rows(assocp)
    for r in assoc:
        try:
            tid=int(float(r.get("source_track_id") or -1))
            t=float(r.get("time_s") or -1)
        except Exception:
            continue
        if tid in {2,3} and 8.5<=t<=10.2:
            print(json.dumps(r,sort_keys=True))
    print("TRACK2_3_ACTION_SUMMARY")
    for tid in (2,3):
        q=[]
        for r in assoc:
            try:
                if int(float(r.get("source_track_id") or -1))==tid and 8.5<=float(r.get("time_s") or -1)<=10.2:
                    q.append(r)
            except Exception:
                pass
        print("TRACK",tid,"ROWS",len(q),
              "CLASS_COUNTS",dict(Counter(str(r.get("det_class")) for r in q)),
              "STRONG_ROWS",sum(1 for r in q if int(float(r.get("det_class") or -1)) in {1,6,7}),
              "POSSESSION_ROWS",sum(1 for r in q if int(float(r.get("det_class") or -1))==5),
              "BALL_ROWS",sum(1 for r in q if int(float(r.get("det_class") or -1))==1),
              "JUMPSHOT_ROWS",sum(1 for r in q if int(float(r.get("det_class") or -1))==6),
              "LAYUP_ROWS",sum(1 for r in q if int(float(r.get("det_class") or -1))==7))


print("COURT_MODEL_SOURCE_HINTS")
court_src=Path("/opt/nbacv/src/nbacv/court.py")
if court_src.exists():
    for idx,line in enumerate(court_src.read_text(errors="replace").splitlines(),1):
        low=line.lower()
        if any(k in low for k in ("2800","1500","court","keypoint","world","template","canonical")):
            if len(line)<500:
                print(f"COURT_SRC {idx}: {line}")
else:
    print("COURT_SOURCE_MISSING",str(court_src))

print("TRACK2_3_COURT_PROJECTION")
cfp=root/"nextgen_mask/court_frames.json"
csp=root/"nextgen_mask/court_scale_attempts.csv"
if not cfp.exists() or not csp.exists():
    print("COURT_ARTIFACT_MISSING",cfp.exists(),csp.exists())
else:
    court_frames=json.load(open(cfp))
    scale_rows=rows(csp)
    frame_to_time={int(float(r["frame"])):float(r["time_s"]) for r in scale_rows}
    cal=[]
    for r in court_frames:
        H=r.get("H")
        fr=int(r.get("frame", -1))
        if H is not None and fr in frame_to_time:
            cal.append((frame_to_time[fr],fr,H))
    print("COURT_CALIBRATED",len(cal),"FIRST_LAST",
          None if not cal else (cal[0][0],cal[-1][0]))
    def proj(H,x,y):
        a=H[0][0]*x+H[0][1]*y+H[0][2]
        b=H[1][0]*x+H[1][1]*y+H[1][2]
        w=H[2][0]*x+H[2][1]*y+H[2][2]
        return (a/w,b/w) if abs(w)>1e-9 else None
    for target_t in (9.3038,9.637466666666668,9.770933333333334):
        if not cal:
            break
        ht,hf,H=min(cal,key=lambda z:abs(z[0]-target_t))
        print("COURT_H",target_t,"USES",ht,"FRAME",hf,"DT",abs(ht-target_t))
        for tid in (5,2,3):
            cand=[]
            for r in obs:
                try:
                    if int(float(r["source_track_id"]))==tid:
                        cand.append((abs(float(r["time_s"])-target_t),r))
                except Exception:
                    pass
            if not cand:
                print("COURT_POINT",target_t,tid,"NO_OBS"); continue
            _,r=min(cand,key=lambda z:z[0])
            x=(float(r["x1"])+float(r["x2"]))*0.5
            y=float(r["y2"])
            p=proj(H,x,y)
            print("COURT_POINT",target_t,"TRACK",tid,
                  "OBS_T",r["time_s"],"PX",(round(x,3),round(y,3)),
                  "COURT",None if p is None else (round(p[0],3),round(p[1],3)),
                  "AMBIG",r.get("ambiguous"))


print("GUARDING_GEOMETRY_ALL_CANDIDATES")
# NBA court coordinates from the same nbacv BasketballCourtConfiguration used
# by the production homography: 2865 x 1524 cm, rim centers 160 cm from each baseline.
LEFT_HOOP=(160.0,762.0)
RIGHT_HOOP=(2705.0,762.0)
CANDS=(0,2,3,4,10,12)
SHOOTER=5

def bottom(r):
    return ((float(r["x1"])+float(r["x2"]))*0.5,float(r["y2"]))
def nearest_obs(tid,t):
    q=[]
    for r in obs:
        try:
            if int(float(r["source_track_id"]))==tid:
                q.append((abs(float(r["time_s"])-t),r))
        except Exception:
            pass
    return min(q,key=lambda z:z[0]) if q else (999,None)

if cfp.exists() and csp.exists() and cal:
    # Probe each genuinely calibrated time rather than extrapolating a homography.
    for ht,hf,H in cal:
        print("CALIBRATED_GUARD_FRAME",ht,"FRAME",hf)
        sd,sr=nearest_obs(SHOOTER,ht)
        if sr is None or sd>0.12:
            print("NO_SHOOTER_NEAR_CAL",sd)
            continue
        sp=proj(H,*bottom(sr))
        print("SHOOTER_COURT",SHOOTER,"OBS_T",sr["time_s"],"COURT",tuple(round(x,3) for x in sp))
        for tid in CANDS:
            dd,r=nearest_obs(tid,ht)
            if r is None or dd>0.12:
                continue
            cp=proj(H,*bottom(r))
            rec={"track":tid,"obs_t":float(r["time_s"]),"ambiguous":str(r.get("ambiguous")),
                 "court":[round(cp[0],3),round(cp[1],3)]}
            for label,hoop in (("left",LEFT_HOOP),("right",RIGHT_HOOP)):
                vx,vy=hoop[0]-sp[0],hoop[1]-sp[1]
                vn=math.hypot(vx,vy)
                ux,uy=vx/vn,vy/vn
                dx,dy=cp[0]-sp[0],cp[1]-sp[1]
                along=dx*ux+dy*uy
                lateral=abs(-dx*uy+dy*ux)
                rec[label+"_along_cm"]=round(along,3)
                rec[label+"_lateral_cm"]=round(lateral,3)
                rec[label+"_basket_dist_cm"]=round(math.hypot(hoop[0]-cp[0],hoop[1]-cp[1]),3)
                rec[label+"_cos_to_basket"]=round(along/max(1e-9,math.hypot(dx,dy)),5)
            print("GUARD_COURT",json.dumps(rec,sort_keys=True))

print("RELATIVE_MOTION_ALL_CANDIDATES")
for tid in CANDS:
    pts=[]
    for t,m in sorted(bytime.items()):
        if not (9.3038-0.001<=t<=9.7709+0.001):
            continue
        if SHOOTER not in m or tid not in m:
            continue
        if str(m[tid].get("ambiguous","")).lower() in {"true","1"}:
            continue
        sx,sy=bottom(m[SHOOTER]); cx,cy=bottom(m[tid])
        scale=max(1.0,0.5*(h(m[SHOOTER])+h(m[tid])))
        pts.append((t,(cx-sx)/scale,(cy-sy)/scale))
    if len(pts)<3:
        continue
    rel_steps=[]
    angles=[]
    radii=[]
    for t,x,y in pts:
        radii.append(math.hypot(x,y))
        angles.append(math.atan2(y,x))
    for a,b in zip(pts,pts[1:]):
        dt=max(1e-6,b[0]-a[0])
        rel_steps.append(math.hypot(b[1]-a[1],b[2]-a[2])/dt)
    # unwrap angle locally for a compact guarding-direction stability measure
    angle_steps=[]
    for a,b in zip(angles,angles[1:]):
        d=(b-a+math.pi)%(2*math.pi)-math.pi
        angle_steps.append(abs(d))
    n=len(radii); mt=sum(p[0] for p in pts)/n; mr=sum(radii)/n
    den=sum((p[0]-mt)**2 for p in pts)
    slope=(sum((p[0]-mt)*(r-mr) for p,r in zip(pts,radii))/den) if den>0 else 0.0
    std=(sum((r-mr)**2 for r in radii)/n)**0.5
    print("REL_MOTION",tid,
          "N",n,
          "MEAN_R",round(mr,4),
          "STD_R",round(std,4),
          "RANGE_R",round(max(radii)-min(radii),4),
          "SLOPE_R_PER_S",round(slope,4),
          "MEAN_REL_SPEED",round(sum(rel_steps)/len(rel_steps),4),
          "MEAN_ANGLE_STEP_RAD",round(sum(angle_steps)/len(angle_steps),4),
          "SERIES",json.dumps([[round(t,4),round(x,4),round(y,4)] for t,x,y in pts]))


print("RIM_ATTACK_DIRECTION_CPU_PROBE")
try:
    import cv2, os
    sys.path.insert(0,"/opt/object-detection-eval/src")
    from object_detection_eval.inference.detectors.rfdetr import RFDETRDetector
    model_path=Path("/srv/hoopvision/models/cache/rfdetr_m_640.onnx")
    source_path=root/"nextgen_mask/source_native.mp4"
    if not model_path.exists():
        print("RIM_PROBE_NO_MODEL",str(model_path))
    elif not source_path.exists():
        print("RIM_PROBE_NO_SOURCE",str(source_path))
    elif not cal:
        print("RIM_PROBE_NO_CALIBRATION")
    else:
        detector=RFDETRDetector(
            model_path,
            {0:'basketball-unused',1:'ball',2:'ball-in-basket',3:'number',4:'player',
             5:'player-in-possession',6:'player-jump-shot',7:'player-layup-dunk',
             8:'player-shot-block',9:'referee',10:'rim'},
            confidence_threshold=.025,
            num_select=300,
            input_height=640,
            input_width=640,
            providers=["CPUExecutionProvider"],
        )
        cap=cv2.VideoCapture(str(source_path))
        for ht,hf,H in cal:
            # court_frames frame numbering is source-native frame numbering here.
            cap.set(cv2.CAP_PROP_POS_FRAMES,int(hf))
            ok,img=cap.read()
            if not ok:
                print("RIM_PROBE_FRAME_READ_FAIL",ht,hf)
                continue
            dets=detector.predict(img)
            print("RIM_PROBE_FRAME",ht,hf,"DETS",len(dets))
            for d in dets:
                cid=int(d.class_id)
                if cid not in {1,2,10}:
                    continue
                bb=detector_box(d,img.shape[1],img.shape[0])
                # Rim/ball center is the meaningful image point.
                x=float((bb[0]+bb[2])*.5); y=float((bb[1]+bb[3])*.5)
                cp=proj(H,x,y)
                dl=math.hypot(cp[0]-LEFT_HOOP[0],cp[1]-LEFT_HOOP[1])
                dr=math.hypot(cp[0]-RIGHT_HOOP[0],cp[1]-RIGHT_HOOP[1])
                print("RIM_PROBE_DET",json.dumps({
                    "time_s":ht,"frame":hf,"class_id":cid,
                    "confidence":round(float(d.confidence),6),
                    "px":[round(x,3),round(y,3)],
                    "court":[round(cp[0],3),round(cp[1],3)],
                    "left_rim_dist_cm":round(dl,3),
                    "right_rim_dist_cm":round(dr,3),
                    "nearest_canonical_rim":"left" if dl<dr else "right",
                    "rim_distance_margin_cm":round(abs(dl-dr),3),
                },sort_keys=True))
        cap.release()
except Exception as exc:
    print("RIM_PROBE_ERROR",type(exc).__name__,repr(exc))


print("SAM31_PLAN_TRACK3")
planp=root/"sam31/sam31_plan.json"
if planp.exists():
    plan=json.load(open(planp))
    for rec in plan:
        seeds=rec.get("seeds") or []
        cand={int(x) for x in (rec.get("candidate_segment_ids") or [])}
        seed_sids={int(x.get("identity_segment_id")) for x in seeds if x.get("identity_segment_id") is not None}
        seed_tids={int(x.get("source_track_id")) for x in seeds if x.get("source_track_id") is not None}
        if seed_sids & {46,47,48} or cand & {46,47,48} or 3 in seed_tids:
            print(json.dumps(rec,sort_keys=True))
else:
    print("NO_SAM31_PLAN")

print("AMBIGUITY_WINDOWS_TRACK3")
awp=root/"sam31/ambiguity_windows.json"
if awp.exists():
    aw=json.load(open(awp))
    print("AMBIGUITY_WINDOW_COUNT",aw.get("window_count"),"TRIGGERS",aw.get("trigger_sample_count"))
    for rec in aw.get("windows") or []:
        pairs=[tuple(int(v) for v in p) for p in (rec.get("track_pairs") or [])]
        if any(3 in p for p in pairs) or (float(rec.get("start_s",999))<=11.97 and float(rec.get("end_s",-1))>=9.30):
            print(json.dumps(rec,sort_keys=True))
else:
    print("NO_AMBIGUITY_WINDOWS")


print("SAM31_RUNTIME_SOURCE_PROBE")
for p in (Path("/srv/hoopvision/src/screen_tracker_nextgen/sam31_ambiguity_continuity.py"),Path("/opt/hoopvision/screen_tracker_nextgen/sam31_ambiguity_continuity.py"),Path("/srv/hoopvision/screen_tracker_nextgen/sam31_ambiguity_continuity.py")):
    print("SAM31_SOURCE_CANDIDATE",str(p),p.exists())
    if p.exists():
        txt=p.read_text(errors="replace")
        print("SAM31_SOURCE_HAS_LEGACY_SAME_SKIP", "if not same.empty:" in txt)
        print("SAM31_SOURCE_HAS_SAME_SEGMENT_FIX", "same_segment=same[" in txt)

print("EXACT_CANDIDATE_RUN_PROBE_V2")
import glob, os
prefix="0b1290c674a3"
roots=sorted(glob.glob("/srv/hoopvision/runs/*"+prefix+"*"), reverse=True)
print("EXACT_CANDIDATE_RUNS", roots[:5])
for rr in roots[:1]:
    art=Path(rr)/"artifacts"
    print("EXACT_CANDIDATE_SELECTED",rr)
    for rel in ("sam31/sam31_plan.json","sam31/sam31_qa.json","sam31/accepted_links.json","identity_segments/segments.csv"):
        p=art/rel; print("EXACT_FILE",rel,p.exists(),p.stat().st_size if p.exists() else -1)
        if p.exists() and p.suffix==".json":
            try:
                obj=json.loads(p.read_text())
                print("EXACT_JSON",rel,json.dumps(obj)[:12000])
            except Exception as e: print("EXACT_JSON_ERROR",rel,repr(e))
