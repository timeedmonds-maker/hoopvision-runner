#!/usr/bin/env python3
"""Fail-closed readiness check for the public HoopVision request bridge.

This script is intentionally safe for the public repository.  It never reads or
prints private infrastructure identifiers, credentials, source, data or result
state.  It only verifies that a recently refreshed public-safe heartbeat says a
private-pull consumer is alive and compatible with the current bridge contract.

Absence/staleness means BLOCKED, not "queue anyway".
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


SCHEMA = "hoopvision.public-consumer-heartbeat.v1"
CONTRACT = "public_outbox_private_pull.v1"
FORBIDDEN_KEYS = {
    "project",
    "project_id",
    "bucket",
    "bucket_name",
    "region",
    "zone",
    "service_account",
    "service_account_email",
    "job",
    "job_name",
    "url",
    "endpoint",
    "token",
    "secret",
    "credential",
    "repository_token",
    "private_repo",
    "internal_topology",
}


def _parse_time(value: str) -> dt.datetime:
    v = str(value).strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    t = dt.datetime.fromisoformat(v)
    if t.tzinfo is None:
        raise ValueError("heartbeat timestamp must be timezone-aware")
    return t.astimezone(dt.timezone.utc)


def check(path: str | Path, *, max_age_s: int = 900, now: dt.datetime | None = None) -> dict:
    p = Path(path)
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    if not p.exists():
        return {
            "schema": "hoopvision.public-bridge-preflight.v1",
            "ready": False,
            "status": "BLOCKED_NO_CONSUMER_HEARTBEAT",
            "heartbeat_age_s": None,
        }

    try:
        doc = json.loads(p.read_text())
    except Exception:
        return {
            "schema": "hoopvision.public-bridge-preflight.v1",
            "ready": False,
            "status": "BLOCKED_INVALID_CONSUMER_HEARTBEAT_JSON",
            "heartbeat_age_s": None,
        }

    forbidden = sorted(k for k in doc if str(k).lower() in FORBIDDEN_KEYS)
    if forbidden:
        return {
            "schema": "hoopvision.public-bridge-preflight.v1",
            "ready": False,
            "status": "BLOCKED_HEARTBEAT_PRIVACY_VIOLATION",
            "heartbeat_age_s": None,
            "forbidden_field_count": len(forbidden),
        }

    if doc.get("schema") != SCHEMA:
        status = "BLOCKED_HEARTBEAT_SCHEMA_MISMATCH"
    elif doc.get("consumer_contract") != CONTRACT:
        status = "BLOCKED_HEARTBEAT_CONTRACT_MISMATCH"
    elif doc.get("status") != "READY":
        status = "BLOCKED_CONSUMER_NOT_READY"
    else:
        status = None

    try:
        observed = _parse_time(doc.get("observed_at_utc"))
        age = max(0.0, (now - observed).total_seconds())
    except Exception:
        observed = None
        age = None
        status = status or "BLOCKED_HEARTBEAT_TIMESTAMP_INVALID"

    if status is None and age is not None and age > float(max_age_s):
        status = "BLOCKED_CONSUMER_HEARTBEAT_STALE"

    ready = status is None
    return {
        "schema": "hoopvision.public-bridge-preflight.v1",
        "ready": bool(ready),
        "status": "READY" if ready else status,
        "heartbeat_age_s": None if age is None else round(float(age), 3),
        "consumer_contract": doc.get("consumer_contract"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heartbeat", default="bridge_consumer_heartbeat.json")
    ap.add_argument("--max-age-s", type=int, default=900)
    args = ap.parse_args()

    result = check(args.heartbeat, max_age_s=args.max_age_s)
    print("HOOPVISION_PUBLIC_BRIDGE_PREFLIGHT=" + json.dumps(result, sort_keys=True))
    if not result["ready"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
