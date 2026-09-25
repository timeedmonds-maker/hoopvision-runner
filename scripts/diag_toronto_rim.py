#!/usr/bin/env python3
import cv2, csv, json, math, os, sys
import numpy as np
from pathlib import Path

root=Path(sys.argv[1])
source=root/"nextgen_mask/source_native.mp4"
app=Path("/srv/hoopvision/apps")
models=Path("/srv/hoopvision/models")
print("SOURCE",source,source.exists())
print("MODEL_CANDIDATES")
for p in [Path("/models/rfdetr_m_640.onnx")]:
    print(str(p),p.exists(),p.stat().st_size if p.exists() else None)

# The diagnostic runs inside the same cached production image with the exact
# candidate app mounted at /opt/hoopvision and prepared model cache at /models.
app_root=Path("/opt/hoopvision")
objsrc=Path("/opt/object-detection-eval/src")
print("APP_ROOT",app_root,app_root.exists())
print("OBJECT_EVAL_SRC",objsrc,objsrc.exists())
sys.path.insert(0,str(objsrc))
from object_detection_eval.inference.detectors.rfdetr import RFDETRDetector
model=Path("/models/rfdetr_m_640.onnx")
if not model.exists(): model=None
if model is None: raise SystemExit("NO_RFDETR_MODEL")
label={0:'basketball-unused',1:'ball',2:'ball-in-basket',3:'number',4:'player',5:'player-in-possession',6:'player-jump-shot',7:'player-layup-dunk',8:'player-shot-block',9:'referee',10:'rim'}
det=RFDETRDetector(model,label,confidence_threshold=.025,num_select=300,input_height=640,input_width=640,providers=["CUDAExecutionProvider","CPUExecutionProvider"])
cap=cv2.VideoCapture(str(source))
fps=float(cap.get(cv2.CAP_PROP_FPS) or 29.97)
print("FPS",fps)

# Accepted court calibration from the retained run.  court_frames.json stores
# image->court homographies keyed by tracker-analysis frame; court_scale_attempts
# supplies the corresponding source-native timestamps.
court_frames_path=root/"nextgen_mask/court_frames.json"
court_scale_path=root/"nextgen_mask/court_scale_attempts.csv"
cal=[]
if court_frames_path.exists() and court_scale_path.exists():
    court_frames=json.load(open(court_frames_path))
    with open(court_scale_path,newline="") as fh:
        scale_rows=list(csv.DictReader(fh))
    frame_to_time={int(float(r["frame"])):float(r["time_s"]) for r in scale_rows}
    for rec in court_frames:
        Hm=rec.get("H")
        fr=int(rec.get("frame",-1))
        if Hm is not None and fr in frame_to_time:
            cal.append((frame_to_time[fr],fr,np.asarray(Hm,dtype=float)))
print("ACCEPTED_CALIBRATIONS",[(round(t,6),fr) for t,fr,_ in cal])
LEFT_RIM=np.asarray([160.0,762.0],dtype=float)
RIGHT_RIM=np.asarray([2705.0,762.0],dtype=float)

def project(H,x,y):
    p=cv2.perspectiveTransform(
        np.asarray([[[float(x),float(y)]]],dtype=np.float64),
        np.asarray(H,dtype=np.float64),
    )[0,0]
    return np.asarray(p,dtype=float)

for t in [9.1703,9.3038,9.4373,9.5707,9.7042,9.7709,10.1713]:
    fr=int(round(t*fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES,fr)
    ok,img=cap.read()
    if not ok:
        print("FRAME_FAIL",t,fr);continue
    H,W=img.shape[:2]
    rows=[]
    for d in det.predict(img):
        cid=int(d.class_id)
        if cid not in {1,2,6,7,10}: continue
        b=d.bbox
        x1,y1,x2,y2=b.x*W,b.y*H,(b.x+b.w)*W,(b.y+b.h)*H
        rec={"class":cid,"name":label[cid],"conf":round(float(d.confidence),6),
             "xyxy":[round(x1,2),round(y1,2),round(x2,2),round(y2,2)],
             "center":[round((x1+x2)/2,2),round((y1+y2)/2,2)]}
        if cid==10 and cal:
            actual_t=fr/fps
            ht,hf,Hm=min(cal,key=lambda z:abs(z[0]-actual_t))
            dt=abs(ht-actual_t)
            # Only call this accepted court evidence when calibration is
            # contemporaneous with the detector frame, never extrapolated.
            if dt<=0.12:
                cp=project(Hm,(x1+x2)/2,(y1+y2)/2)
                dl=float(np.linalg.norm(cp-LEFT_RIM))
                dr=float(np.linalg.norm(cp-RIGHT_RIM))
                rec.update({
                    "court_cal_time_s":round(ht,6),
                    "court_cal_dt_s":round(dt,6),
                    "court_xy_cm":[round(float(cp[0]),2),round(float(cp[1]),2)],
                    "left_rim_dist_cm":round(dl,2),
                    "right_rim_dist_cm":round(dr,2),
                    "nearest_canonical_rim":"left" if dl<dr else "right",
                    "canonical_rim_margin_cm":round(abs(dl-dr),2),
                })
        rows.append(rec)
    rows.sort(key=lambda r:(r["class"],-r["conf"]))
    print("FRAME",json.dumps({"target_t":t,"frame":fr,"actual_t":fr/fps,"W":W,"H":H,"detections":rows},sort_keys=True))
cap.release()
