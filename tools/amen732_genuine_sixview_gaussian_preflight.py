#!/usr/bin/env python3
"""Freeze original Amen/Wemby event 732 six-angle images for a TRUE Gaussian model.

No model inference here. Ensure every native source image, original/fresh frame
index and content SHA matches the certified private release; prepare [0,1] RGB
six-image tensor required by AnySplat official inference API. Fail closed on
missing frames, shape, range, or archival crosswalk. Output remains PRIVATE.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np

VIEW_ORDER=("Broadcast","High Tight","Left Above Rim","Right Above Rim","Left Slash","Right Slash")
GAME="0022600009"
MODEL_SIZE=(448,252)
SOURCE_SIZE=(960,540)
def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as p:
  for block in iter(lambda:p.read(1<<20),b""):h.update(block)
 return h.hexdigest()
def process(rgb):
 if rgb.shape!=(540,960,3) or rgb.dtype!=np.uint8:
  raise RuntimeError("SIX_VIEW_ORIGINAL_RGB_MUST_BE_960x540")
 result=cv2.resize(rgb,MODEL_SIZE,interpolation=cv2.INTER_AREA).astype(np.float32)/255.
 result=np.moveaxis(result,2,0)
 if not(np.isfinite(result).all() and result.min()>=0 and result.max()<=1):
  raise RuntimeError("ANYSPLAT_MODEL_INPUT_MUST_BE_FLOAT_RGB_0_TO_1")
 return result
def run(manifest_path,images_dir,crosswalk_path,out):
 manifest=json.loads(manifest_path.read_text())
 cross=json.loads(crosswalk_path.read_text())
 if manifest["event"]["game_id"]!=GAME or int(manifest["event"]["event_num"])!=732:
  raise RuntimeError("INCORRECT_EVENT")
 if cross["full_frame_pixel_correspondences_accepted_camera_count"]!=6:
  raise RuntimeError("SIX_INPUT_CROSSWALK_NOT_CERTIFIED")
 if not cross["all_six_video_version_frame_maps_verified"]:
  raise RuntimeError("ORIGINAL_FRESH_VERSIONS_NOT_MATCHED")
 entries=manifest["single_frozen_scene"]["image_input_order"]
 assert len(entries)==6
 inp=[];actual=[]
 for view,entry in zip(VIEW_ORDER,entries):
  if entry["label"]!=view or entry["fresh_source_native_frame_idx"]-entry["archived_native_frame_idx"]!=90:
   raise RuntimeError("FROZEN_CAMERA_SOURCE_ORDER_OR_90_FRAME_MAP_INVALID")
  x=cross["camera_results"][view]
  if not x["two_independent_visual_correspondences_pass"]:
   raise RuntimeError("PER_CAMERA_ARCHIVE_VISUAL_FAIL:"+view)
  if any(y!=90 for y in x["archived_to_fresh_frame_offsets"]):
   raise RuntimeError("PER_CAMERA_FRAME_SHIFT_INCONSISTENT:"+view)
  f=images_dir/entry["image_asset_filename"]
  if not f.is_file() or digest(f)!=entry["image_sha256"]:
   raise RuntimeError("SOURCE_ORIGINAL_PNG_SHA_MISMATCH:"+view)
  bgr=cv2.imread(str(f),cv2.IMREAD_COLOR)
  if bgr is None or bgr.shape!=(540,960,3):
   raise RuntimeError("UNEXPECTED_NATIVE_PIXEL_INPUT:"+view)
  arr=process(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
  inp.append(arr)
  actual.append({"label":view,"source_png":f.name,"verified_sha256":digest(f),
    "native_dimensions":list(SOURCE_SIZE),
    "archived_frame_index":entry["archived_native_frame_idx"],
    "fresh_frame_index":entry["fresh_source_native_frame_idx"],
    "model_input_range":[float(arr.min()),float(arr.max())],
    "image_contrast_std":round(float(np.std(arr)),4)})
 stack=np.stack(inp).astype(np.float16)
 assert stack.shape==(6,3,252,448)
 out.mkdir(parents=True,exist_ok=True)
 pack=out/"amen732_real_sixview_anysplat_0to1_448x252.npz"
 np.savez_compressed(pack,images=stack)
 with np.load(pack) as verify:
  assert verify["images"].shape==(6,3,252,448)
  assert np.isfinite(verify["images"]).all()
 qa={"schema":"hoopvision.freeview.amen732.genuine_sixview_gaussian_model_preflight.v1",
   "game_id":GAME,"event_num":732,
   "input_camera_count":6,
   "archived_source_frame_images_per_camera_verified":2,
   "all_12_archived_vs_fresh_pixel_correspondences_pass":True,
   "all_archived_to_fresh_frame_deltas":90,
   "input_original_native_image_count":6,
   "native_resolution":[960,540],
   "model_input_shape":[6,3,252,448],
   "model_input_channels":"RGB",
   "model_input_normalization":"float16_range_0_to_1_not_minus1_to_1",
   "upcoming_model":"AnySplat published feed-forward unposed 3D Gaussian; actual reconstruction GPU unexecuted",
   "model_tensor_private_asset":pack.name,
   "model_tensor_sha256":digest(pack),
   "inputs":actual,
   "anysplat_true_cuda_gaussian_rasterizer_executed":False,
   "independent_heldout_silhouette_qa_pass":False,
   "actual_first_touch_certified":False,
   "novel_view_movie_accepted":False,
   "no_model_generated_pixels_are_claimed":True}
 (out/"amen732_real_sixview_gaussian_preflight_qa.json").write_text(json.dumps(qa,indent=2)+"\n")
 print("AMEN732_SHA_VERIFIED_SIXVIEW_MODEL_INPUT_PASS",
   "cameras",len(actual),"tensor",stack.shape,
   "native_archive_fresh_delta",90,"model_inference_executed",False,flush=True)
def selftest():
 x=np.random.default_rng(22).integers(0,255,size=(540,960,3),dtype=np.uint8)
 out=process(x)
 assert out.shape==(3,252,448)
 assert 0<=out.min()<out.max()<=1
 assert abs(float(out.mean())-.5)<.02
 print("GAUSSIAN_SOURCE_RGB_NORMALIZATION_AND_DIMENSION_UNIT_PASS")
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--manifest",type=Path)
 p.add_argument("--source-pngs",type=Path)
 p.add_argument("--crosswalk",type=Path)
 p.add_argument("--out",type=Path)
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 if a.selftest:selftest()
 else:
  if not(a.manifest and a.source_pngs and a.crosswalk and a.out):
   p.error("--manifest, --source-pngs, --crosswalk and --out required")
  run(a.manifest,a.source_pngs,a.crosswalk,a.out)
