#!/usr/bin/env python3
"""Source-only match: archived native NBA JPEG references to reacquired HLS MP4s.

Find true source-frame correspondences with full-frame grayscale + gradient NCC;
never assume equal frame numbers or PTS origins. A 2-frame consistent fit is
required per camera. Only aggregate metrics and source frame indices may go to
public runner logs; original JPEG pixels and videos stay private/ephemeral.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np

G="0022600009"; EV=732
PAIRS={
 "Broadcast":(272,275),
 "High Tight":(228,235),
 "Left Above Rim":(239,247),
 "Right Above Rim":(231,234),
 "Left Slash":(213,221),
 "Right Slash":(203,211)
}
SIZE=(192,108)
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def embed(im):
 if im is None or im.shape[0]<300 or im.shape[1]<400:
  raise RuntimeError("SOURCE_FRAME_INVALID")
 g=cv2.cvtColor(cv2.resize(im,SIZE,interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY)
 g=g.astype(np.float32)/255.0
 # Low-frequency appearance and edges are both necessary. Raw mean brightness
 # and global contrast change with HLS encoder but cannot determine matching.
 gx=cv2.Sobel(g,cv2.CV_32F,1,0,ksize=3)
 gy=cv2.Sobel(g,cv2.CV_32F,0,1,ksize=3)
 a=np.r_[g.ravel(),gx.ravel()*0.25,gy.ravel()*0.25]
 a-=a.mean()
 a/=max(float(np.linalg.norm(a)),1e-8)
 return a
def decode_embeddings(path):
 cap=cv2.VideoCapture(str(path))
 if not cap.isOpened():raise RuntimeError("FRESH_VIDEO_DECODE_FAILED")
 v=[]; indices=[]
 idx=0
 while True:
  ok,im=cap.read()
  if not ok:break
  v.append(embed(im));indices.append(idx);idx+=1
 cap.release()
 if len(v)<300:raise RuntimeError("FRESH_VIDEO_TOO_SHORT")
 return np.stack(v,axis=0),indices
def candidate_scores(ref,video):
 s=video@ref
 best=np.argsort(s)[::-1][:10]
 result=[]
 for k in best:
  if not result or all(abs(int(k)-x["new_frame"])>4 for x in result):
   result.append({"new_frame":int(k),"pixel_structure_ncc":round(float(s[k]),5)})
  if len(result)>=3:break
 if len(result)<2:
  alt=np.argsort(s)[::-1]
  for k in alt:
   if all(abs(int(k)-x["new_frame"])>4 for x in result):
    result.append({"new_frame":int(k),"pixel_structure_ncc":round(float(s[k]),5)})
    break
 return result
def compare(fresh,refs,out):
 d=json.loads((fresh/"source_manifest.json").read_text())
 pts=json.loads((fresh/"native_presentation_timestamps.json").read_text())
 assert d["event"]["game_id"]==G and int(d["event"]["event_num"])==EV
 feed={x["label"]:x for x in d["feeds"]}
 rows={}
 for label,(f0,f1) in PAIRS.items():
  video_path=fresh/feed[label]["file"]]
  h=sha(video_path)
  assert h==feed[label]["native_media_sha256"]==pts[label]["clip_sha256"]
  embeddings,indices=decode_embeddings(video_path)
  key=label.lower().replace(" ","-")
  targets=[]
  for i in (f0,f1):
   source=refs/f"amen732-native-{key}-f{i}.jpg"
   if not source.is_file():raise RuntimeError("ORIGINAL_REFERENCE_JPEG_MISSING:"+source.name)
   ref=cv2.imread(str(source),cv2.IMREAD_COLOR)
   candidates=candidate_scores(embed(ref),embeddings)
   best=candidates[0]
   targets.append({"original_archived_jpeg_filename":source.name,
      "archived_jpeg_sha256":sha(source),
      "original_archived_frame_number":i,
      "matched_fresh_frame":best["new_frame"],
      "fresh_native_pts_s":float(pts[label]["frames"][best["new_frame"]]["pts_time_s"]),
      "normalized_pixel_structure_ncc":best["pixel_structure_ncc"],
      "next_separated_candidates":candidates[1:]})
  a,b=targets
  deltas=[x["matched_fresh_frame"]-x["original_archived_frame_number"] for x in targets]
  gap=(b["matched_fresh_frame"]-a["matched_fresh_frame"])-(f1-f0)
  high_enough=all(t["normalized_pixel_structure_ncc"]>=0.84 for t in targets)
  pair_consistent=abs(gap)<=1
  distinct=abs(b["fresh_native_pts_s"]-a["fresh_native_pts_s"])>0.06
  eligible=bool(high_enough and pair_consistent and distinct)
  rows[label]={"fresh_video_sha256":h,"original_reference_count":2,
    "archived_to_fresh_frame_offsets":deltas,
    "same_clip_sequence_temporal_gap_error_frames":gap,
    "matches":targets,
    "two_independent_visual_correspondences_pass":eligible,
    "rejection_reasons":[x for cond,x in [
     (high_enough,"LOW_IMAGE_CORRELATION"),
     (pair_consistent,"PAIR_FRAME_GAP_INCONSISTENT"),
     (distinct,"DUPLICATE_OR_NONSPACED_FRAME_MATCH")]
     if not cond]}
  print("CAMERA_ARCHIVE_TO_FRESH_IMAGE_MATCH",
    label.replace(" ","_"),
    "refs",[(x["original_archived_frame_number"],x["matched_fresh_frame"],
             x["normalized_pixel_structure_ncc"]) for x in targets],
    "delta",deltas,
    "pairgap",gap,
    "pass",eligible,flush=True)
 count=sum(x["two_independent_visual_correspondences_pass"] for x in rows.values())
 report={"schema":"hoopvision.freeview.amen732.archived_to_fresh_visual_content.v1",
  "game_id":G,"event_num":EV,"camera_count":6,
  "reference_jpegs_total":12,"method":"NCC of grayscale+spatial-gradient native frame versus every fresh decoded HLS video frame",
  "source_data":"private original archived source JPEG; current fresh official 6 HLS MP4s",
  "all_six_media_files_sha_equal_to_archive":False,
  "full_frame_pixel_correspondences_accepted_camera_count":count,
  "all_six_video_version_frame_maps_verified":count==6,
  "camera_results":rows,
  "same_physical_instant_certified":False,
  "first_hand_ball_contact_certified":False,
  "multi_view_surface_reconstruction_certified":False,
  "eligible_to_share_old_frame_observations_with_fresh_mp4s":count==6}
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(report,indent=2)+"\n")
 print("SIX_CAMERA_ARCHIVE_TO_FRESH_PIXELS",count,"of 6",
    "source_version_crosswalk_certified",report["all_six_video_version_frame_maps_verified"],flush=True)
def selftest():
 import tempfile
 x=np.random.default_rng(5).random((540,960,3))
 im=(x*255).astype(np.uint8)
 e=embed(im)
 assert abs(float(e@e)-1)<1e-4
 arr=np.stack([embed(np.roll(im,d,axis=1)) for d in (80,40,0,20,60)])
 assert int(np.argmax(arr@e))==2
 print("SOURCE_ARCHIVE_PIXEL_NCC_INDEXING_SYNTHETIC_PASS")
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--fresh",type=Path)
 p.add_argument("--archived-jpegs",type=Path)
 p.add_argument("--out",type=Path)
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 if a.selftest:selftest()
 else:
  if not(a.fresh and a.archived_jpegs and a.out):
   p.error("--fresh --archived-jpegs --out required")
  compare(a.fresh,a.archived_jpegs,a.out)
