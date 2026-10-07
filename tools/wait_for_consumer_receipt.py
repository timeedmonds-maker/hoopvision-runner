#!/usr/bin/env python3
"""Wait for a public-safe receipt that the private pull consumer saw a request.

The receipt exposes only the already-public opaque request_id, a coarse consumer
admission status, and timestamp. It never exposes resolver/GPU/private result
state.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request


SCHEMA="hoopvision.public-consumer-receipt.v1"
SUCCESS={"CONSUMED"}
FAILURE={"REJECTED_UNREGISTERED","FAILED_TO_START_RESOLVER"}


def classify(doc:dict, request_id:str)->str:
    if doc.get("schema")!=SCHEMA:
        return "WAIT"
    if str(doc.get("request_id") or "")!=str(request_id):
        return "WAIT"
    status=str(doc.get("status") or "")
    if status in SUCCESS:
        return "SUCCESS"
    if status in FAILURE:
        return "FAILURE"
    return "WAIT"


def fetch_json(url:str)->dict:
    sep="&" if "?" in url else "?"
    req=urllib.request.Request(
        url+sep+"ts="+str(time.time_ns()),
        headers={"Cache-Control":"no-cache","User-Agent":"hoopvision-public-bridge/1"},
    )
    with urllib.request.urlopen(req,timeout=10) as resp:
        return json.loads(resp.read())


def wait(url:str,request_id:str,*,timeout_s:float=120.0,poll_s:float=5.0)->dict:
    deadline=time.monotonic()+float(timeout_s)
    last=None
    while time.monotonic()<deadline:
        try:
            doc=fetch_json(url)
            verdict=classify(doc,request_id)
            last=doc
            if verdict=="SUCCESS":
                return {"ready":True,"status":"CONSUMED","receipt":doc}
            if verdict=="FAILURE":
                return {"ready":False,"status":str(doc.get("status")),"receipt":doc}
        except Exception:
            pass
        time.sleep(float(poll_s))
    return {"ready":False,"status":"TIMEOUT_NO_MATCHING_CONSUMER_RECEIPT","receipt":last}


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",required=True)
    ap.add_argument("--request-id",required=True)
    ap.add_argument("--timeout-s",type=float,default=120.0)
    ap.add_argument("--poll-s",type=float,default=5.0)
    a=ap.parse_args()
    result=wait(a.url,a.request_id,timeout_s=a.timeout_s,poll_s=a.poll_s)
    safe={
        "ready":bool(result["ready"]),
        "status":result["status"],
        "request_id":a.request_id,
    }
    print("HOOPVISION_PUBLIC_CONSUMER_RECEIPT="+json.dumps(safe,sort_keys=True))
    if not result["ready"]:
        raise SystemExit(4)


if __name__=="__main__":
    main()
