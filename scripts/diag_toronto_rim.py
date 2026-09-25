#!/usr/bin/env python3
import cv2, json, os, sys
from pathlib import Path

root=Path(sys.argv[1])
source=root/"nextgen_mask/source_native.mp4"
app=Path("/srv/hoopvision/apps")
models=Path("/srv/hoopvision/models")
print("SOURCE",source,source.exists())
print("MODEL_CANDIDATES")
for p in [models/"rfdetr_m_640.onnx", Path("/models/rfdetr_m_640.onnx")]:
    print(str(p),p.exists(),p.stat().st_size if p.exists() else None)

# Locate the exact candidate app and object-eval source already used by prepared host.
cands=[]
for p in app.glob("**/build_kickout_semantic_anchors.py"):
    cands.append(p)
print("APP_BUILDERS",[str(x) for x in cands[-5:]])
builder=cands[-1] if cands else None
if builder is None:
    raise SystemExit("NO_BUILDER")
app_root=builder.parents[1]
for p in [Path("/opt/object-detection-eval/src"), Path("/srv/hoopvision/object-detection-eval/src"), app_root/"object-detection-eval/src"]:
    if p.exists():
        objsrc=p;break
else:
    # search bounded host roots, not the whole filesystem
    found=list(Path("/srv/hoopvision").glob("**/object_detection_eval/inference/detectors/rfdetr.py"))
    if not found: raise SystemExit("NO_OBJECT_EVAL")
    objsrc=found[-1].parents[4]
print("APP_ROOT",app_root)
print("OBJECT_EVAL_SRC",objsrc)
sys.path.insert(0,str(objsrc))
from object_detection_eval.inference.detectors.rfdetr import RFDETRDetector
model=next((p for p in [models/"rfdetr_m_640.onnx",Path("/models/rfdetr_m_640.onnx")] if p.exists()),None)
if model is None: raise SystemExit("NO_RFDETR_MODEL")
label={0:'basketball-unused',1:'ball',2:'ball-in-basket',3:'number',4:'player',5:'player-in-possession',6:'player-jump-shot',7:'player-layup-dunk',8:'player-shot-block',9:'referee',10:'rim'}
det=RFDETRDetector(model,label,confidence_threshold=.025,num_select=300,input_height=640,input_width=640,providers=["CUDAExecutionProvider","CPUExecutionProvider"])
cap=cv2.VideoCapture(str(source))
fps=float(cap.get(cv2.CAP_PROP_FPS) or 29.97)
print("FPS",fps)
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
        rows.append({"class":cid,"name":label[cid],"conf":round(float(d.confidence),6),
                     "xyxy":[round(x1,2),round(y1,2),round(x2,2),round(y2,2)],
                     "center":[round((x1+x2)/2,2),round((y1+y2)/2,2)]})
    rows.sort(key=lambda r:(r["class"],-r["conf"]))
    print("FRAME",json.dumps({"target_t":t,"frame":fr,"actual_t":fr/fps,"W":W,"H":H,"detections":rows},sort_keys=True))
cap.release()
