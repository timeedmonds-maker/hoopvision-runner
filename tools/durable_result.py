#!/usr/bin/env python3
"""Parse HoopVision durable result payloads without conflating execution and qualification."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def benchmark(payload: dict) -> dict:
    return _dict(payload.get("benchmark"))


def benchmark_result(payload: dict) -> dict:
    return _dict(benchmark(payload).get("result"))


def execution_status(payload: dict) -> str:
    top = str(payload.get("status") or "").upper()
    if top in {"FAILED", "CANCELLED", "COMPLETED"}:
        return top
    if top == "SUCCESS":  # recognised legacy terminal spelling
        return "COMPLETED"

    b = benchmark(payload)
    q = _dict(b.get("qualification"))
    terminal = str(q.get("terminal_status") or "").upper()
    if terminal in {"FAILED", "CANCELLED", "COMPLETED"}:
        return terminal

    if b.get("ok") is True:
        return "COMPLETED"
    if b.get("ok") is False:
        return "FAILED"
    return "UNKNOWN"


def qualification_status(payload: dict) -> str:
    b = benchmark(payload)
    q = _dict(b.get("qualification"))
    value = q.get("qualification_status")
    if value is not None:
        return str(value).upper()

    result = benchmark_result(payload)
    gate = _dict(result.get("single_run_foundation_gate"))
    if gate.get("status") is not None:
        return str(gate.get("status")).upper()

    # Qualification is deliberately not inferred from execution completion.
    return "UNKNOWN"


def final_video(payload: dict) -> str:
    nested = benchmark_result(payload).get("final_video")
    if nested:
        return str(nested)
    legacy = payload.get("final_video")
    return "" if legacy is None else str(legacy)


def validate_final_video(uri: str, allowed_bucket: str | None) -> str:
    if not uri:
        return ""
    if not uri.startswith("gs://"):
        raise ValueError("final_video is not a gs:// URI")
    if allowed_bucket:
        prefix = f"gs://{allowed_bucket}/"
        if not uri.startswith(prefix):
            raise ValueError("final_video is outside the authorised bucket")
        obj = uri[len(prefix):]
        if not obj or obj.startswith("/") or ".." in obj.split("/"):
            raise ValueError("final_video has an invalid object path")
    return uri


def classification(payload: dict) -> str:
    status = execution_status(payload)
    raw = json.dumps(payload, sort_keys=True)
    if status == "FAILED":
        if "TimeoutError" in raw:
            return "APPLICATION_TIMEOUT_NO_AUTORETRY"
        return "TERMINAL_FAILURE_DIAGNOSE_BEFORE_RETRY"
    if status == "CANCELLED":
        return "CANCELLED_NO_AUTORETRY"
    if status == "COMPLETED":
        return "COMPLETED_AWAIT_ACCEPTANCE_EVIDENCE"
    return "UNKNOWN_DIAGNOSE_BEFORE_RETRY"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--field",
        required=True,
        choices=["execution_status", "qualification_status", "final_video", "classification"],
    )
    ap.add_argument("--allowed-bucket")
    args = ap.parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("durable result must be a JSON object")
        if args.field == "execution_status":
            value = execution_status(payload)
        elif args.field == "qualification_status":
            value = qualification_status(payload)
        elif args.field == "classification":
            value = classification(payload)
        else:
            value = validate_final_video(final_video(payload), args.allowed_bucket)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"durable-result parse error: {exc}", file=sys.stderr)
        return 2
    print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
