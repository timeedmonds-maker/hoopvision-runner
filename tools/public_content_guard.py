#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ALLOWED_STATIC = {
    "README.md",
    "PUBLIC_CONTENT_POLICY.md",
    "runner_policy.json",
    "bridge_consumer_heartbeat.json",
    "bridge_consumer_receipt.json",
    "bridge_execution_status.json",
    "bridge_result_summary.json",
    "tools/public_bridge_preflight.py",
    "tools/wait_for_consumer_receipt.py",
    "tools/public_content_guard.py",
    ".github/workflows/gamepulse-github-private-pilot.yml",
    "tools/licensed_feed/browser.js",
    "tools/licensed_feed/capture.mjs",
    "tools/licensed_feed/capture.test.mjs",
    "tools/licensed_feed/github_private_release.mjs",
    "tools/licensed_feed/github_private_release.test.mjs",
    "tools/licensed_feed/index.html",
    "tools/licensed_feed/package.json",
    "tools/licensed_feed/season_core.mjs",
    "tools/licensed_feed/season_core.test.mjs",
    "tools/licensed_feed/sdk_slot.mjs",
    "tools/licensed_feed/sdk_slot.test.mjs",
    "tools/licensed_feed/season_private_release.mjs",
    "tools/licensed_feed/verify_gameplay.py",
    ".github/workflows/gamepulse-gameplay-audit.yml",
    ".github/workflows/gamepulse-defender-spacing-qa.yml",
    ".github/workflows/gamepulse-rockets-private-clip-pilot.yml",
    ".github/workflows/gamepulse-pnr-feasibility.yml",
    ".github/workflows/rockets-pnr-unified-review-qa.yml",
    ".github/workflows/rockets-pnr-video-source-diagnostic.yml",
    ".github/workflows/rockets-pnr-0075-gamepulse-review.yml",
    ".github/workflows/rockets-all-defensive-pnr-analysis.yml",
    ".github/workflows/gamepulse-pnr-ui-preflight.yml",
    ".github/workflows/gamepulse-github-season.yml",
    ".github/workflows/gamepulse-final-fastlane.yml",
    ".github/workflows/gamepulse-rockets-finalize-safeguard.yml",
    ".github/workflows/gamepulse-20261022-slate-backfill.yml",
    ".github/workflows/gamepulse-20261022-targeted-retry.yml",
    ".github/workflows/gamepulse-source-ready-final10.yml",
    ".github/workflows/gamepulse-part6-fast.yml",
    ".github/workflows/gamepulse-14game-world-source-qa.yml",
    ".github/workflows/gamepulse-private-search-index.yml",
    ".github/workflows/gamepulse-private-blueprint-fusion.yml",
    ".github/workflows/gamepulse-blueprint-14-backfill.yml",
    "tests/test_consumer_receipt_waiter.py",
    "tests/test_public_bridge_preflight.py",
    "tests/test_public_content_guard.py",
    ".github/workflows/run.yml",
    ".github/workflows/public-bridge-preflight-tests.yml",
    ".github/workflows/public-content-guard.yml",
    ".github/workflows/validate-public-bridge.yml",
    ".github/workflows/oneoff-sanitize-history.yml",
    ".github/workflows/post-sanitize-public-audit.yml",
    ".github/workflows/dispatch-oidc.yml",
}
ALLOWED_PREFIXES = {"bridge_outbox/"}
FORBIDDEN_PREFIXES = {
    "experiments/",
    "experiment_results/",
    "prepared/",
    "models/",
    "checkpoints/",
    "fixtures/",
    "datasets/",
}
FORBIDDEN_EXT = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm",
    ".pt", ".pth", ".onnx", ".engine", ".safetensors",
    ".csv", ".parquet", ".npz", ".npy", ".pkl", ".pickle",
}
TEXT_PATTERNS = [
    ("GCS_URI", re.compile(r"gs://", re.I)),
    ("SERVICE_ACCOUNT", re.compile(r"iam\.gserviceaccount\.com", re.I)),
    ("GCP_PROJECT_STYLE_ID", re.compile(r"\bproject-[a-z0-9][a-z0-9-]{4,}\b", re.I)),
    ("ACTIONS_ARTIFACT_UPLOAD", re.compile(r"actions/upload-artifact@", re.I)),
    ("DIRECT_PRIVATE_REPO_CHECKOUT", re.compile(r"repository:\s*[^\n]+/104\b", re.I)),
    ("MEDIA_SOURCE_URL", re.compile(r"(youtube\.com/watch|clips\.nba\.com)", re.I)),
]
REQUEST_RE = re.compile(r"^req-[0-9a-f]{32}$")

def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"])
    return [x.decode() for x in out.split(b"\0") if x]

def violation(code: str, path: str) -> tuple[str, str]:
    return (code, path)

def scan(paths: list[str]) -> list[tuple[str, str]]:
    bad: list[tuple[str, str]] = []
    for rel in paths:
        p = Path(rel)
        if any(rel.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            bad.append(violation("FORBIDDEN_PATH_CLASS", rel))
            continue
        if p.suffix.lower() in FORBIDDEN_EXT:
            bad.append(violation("FORBIDDEN_FILE_TYPE", rel))
            continue
        if rel not in ALLOWED_STATIC and not any(rel.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            bad.append(violation("NOT_ALLOWLISTED", rel))
            continue
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bad.append(violation("NON_TEXT_FILE", rel))
            continue
        # The guard contains literal detection patterns by design; do not
        # flag its own source for defining those patterns.
        if rel != "tools/public_content_guard.py":
            for code, rx in TEXT_PATTERNS:
                if rx.search(text):
                    bad.append(violation(code, rel))
    rid = Path("REQUEST_ID")
    if rid.exists():
        value = rid.read_text().strip()
        if value and not REQUEST_RE.fullmatch(value):
            bad.append(violation("SEMANTIC_OR_INVALID_REQUEST_ID", "REQUEST_ID"))
    return sorted(set(bad))

def main() -> int:
    bad = scan(tracked_files())
    if bad:
        for code, path in bad:
            print(f"PUBLIC_CONTENT_GUARD_FAIL code={code} path={path}")
        return 3
    print("PUBLIC_CONTENT_GUARD_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
