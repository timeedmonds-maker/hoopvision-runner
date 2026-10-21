"""Process licensed-feed chunks on ephemeral public CPU, upload directly to private gateway.

Never prints private job details, payload data, OIDC token, or gateway response.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from opaque_lane_client import identity_token, endpoint, fresh_id

def request_json(route, payload, request_id):
    token=identity_token()
    data=json.dumps(payload,separators=(",",":")).encode()
    req=urllib.request.Request(endpoint()+"/v1/"+route,data=data,method="POST",headers={
        "Authorization":"Bearer "+token,"Content-Type":"application/json",
        "X-Opaque-Request":request_id})
    with urllib.request.urlopen(req,timeout=30) as response:
        if response.status!=200: raise RuntimeError("gateway_rejected")
        if int(response.headers.get("Content-Length","0"))>25000:
            raise RuntimeError("gateway_response_too_large")
        return json.load(response)

def send_chunk(path,grant,request_id):
    archive=Path(path).read_bytes()
    if len(archive)>32*1024*1024: raise RuntimeError("chunk_oversize")
    if not isinstance(grant,str) or len(grant)>4000 or len(grant)<40:
        raise RuntimeError("invalid_grant")
    req=urllib.request.Request(endpoint()+"/v1/upload",data=archive,method="POST",headers={
        "Authorization":"Bearer "+identity_token(),
        "Content-Type":"application/octet-stream",
        "X-Opaque-Request":request_id,
        "X-Job-Grant":grant,
        "X-Payload-SHA256":hashlib.sha256(archive).hexdigest()
    })
    with urllib.request.urlopen(req,timeout=120) as response:
        if response.status!=200: raise RuntimeError("upload_failed")
        data=json.load(response)
    if data.get("status") not in ("SAVED","ALREADY_SAVED"):
        raise RuntimeError("archive_not_confirmed")

def run(max_chunks):
    for _ in range(max_chunks):
        request_id=fresh_id()
        answer=request_json("claim",{"schema":"opaque-feed-claim.v1","request_id":request_id},request_id)
        if answer.get("status")=="NO_WORK":
            print("OPAQUE_FEED_NO_WORK")
            return
        if answer.get("status")!="READY" or not isinstance(answer.get("job"),dict):
            raise RuntimeError("private_job_unavailable")
        with tempfile.TemporaryDirectory(prefix="ephemeral-feed-") as temp:
            path=Path(temp)
            jobfile=path/"job.json"
            jobfile.write_text(json.dumps(answer["job"]),encoding="utf-8")
            os.chmod(jobfile,0o600)
            result=subprocess.run(["node",str(Path(__file__).with_name("capture.mjs")),
                str(jobfile),str(path)],capture_output=True,timeout=900)
            if result.returncode:
                # Captured subprocess logs are intentionally never published.
                raise RuntimeError("capture_failed")
            send_chunk(path/"checkpoint.tar.gz",answer.get("grant"),request_id)
        print("OPAQUE_FEED_PRIVATE_UPLOAD_OK")
    print("OPAQUE_FEED_BOUNDED_LIMIT_REACHED")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--max-chunks",type=int,default=30)
    args=parser.parse_args()
    if args.self_test:
        from opaque_lane_contract import valid_request_id
        assert valid_request_id(fresh_id())
        print("OPAQUE_FEED_STATIC_PREFLIGHT_OK")
        return
    if not 1<=args.max_chunks<=80: raise RuntimeError("invalid_run_limit")
    run(args.max_chunks)

if __name__=="__main__":
    try:main()
    except Exception:
        print("OPAQUE_FEED_FAILED",file=sys.stderr)
        raise SystemExit(2)
