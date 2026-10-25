#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ALLOWED_STATIC = {
    ".github/workflows/gamepulse-pr776-original-sdk-terminal-xyz.yml",  # reviewed: one real private NBA SDK game, original SHA, aggregate-only logs
    ".github/workflows/gamepulse-pr776-rockets-spurs-native-advanced.yml",  # reviewed: CPU, private original NBA source and private-only source publish
    ".github/workflows/gamepulse-pr776-season-search-provider-acceptance.yml",  # reviewed ephemeral private NBA source retrieval and aggregate-only QA
    ".github/workflows/gamepulse-pr776-acceptance-20261025.yml",  # reviewed CPU-only pinned SHA private fetch; no public data outputs
    ".github/workflows/gamepulse-wemby-defensive-position.yml",  # CPU-only original NBA source, private source/aggregated results only
    ".github/workflows/clip-lab-event80-direct-native-frozen.yml",  # audited CPU-only original NBA source, private SDK, final ringed MP4
    ".github/workflows/clip-lab-rockets-event80-frozen-render.yml",  # reviewed: exact frozen source SHA and private-only v3.1 MP4
    ".github/workflows/clip-lab-event80-delivery-smoke.yml",  # test fixture artifact only
    ".github/workflows/clip-lab-rockets-event80-hls.yml",  # reviewed: exact one-event private HLS CPU staging only
    ".github/workflows/clip-lab-rockets-event80-native.yml",  # reviewed: exact event native SDK SHA extraction, private only
    ".github/workflows/clip-lab-rockets-event80-frozen-cpu.yml",  # reviewed: original CPU frozen v3.1 detector, private QA only
    ".github/workflows/clip-lab-encrypted-event86-handoff.yml",
    "tools/clip_lab_public_handoff_cert.pem",
    ".github/workflows/clip-lab-artifact-handoff-smoke.yml",
    ".github/workflows/freeview-amen-732-4k-contact-diagnostic.yml",
    ".github/workflows/clip-lab-adams86-original-frozen-cpu-full20.yml",
    ".github/workflows/clip-lab-event86-view-quality-cpu.yml",
    ".github/workflows/clip-lab-adams86-xfg-source-quality.yml",
    ".github/workflows/clip-lab-adams86-original-frozen-cpu-tracker-probe.yml",
    ".github/workflows/clip-lab-rockets-spurs-adams-86-video-sync.yml",
    ".github/workflows/clip-lab-rockets-spurs-adams-86-native-video.yml",
    ".github/workflows/freeview-amen-732-final-seconds-recovery.yml",
    ".github/workflows/rockets-spurs-q1-sdk-recovery.yml",
    ".github/workflows/gamepulse-unresolved-official-onoff-watch.yml",
    "tools/licensed_feed/pbpstats_missing_onoff_fallback.py",
    ".github/workflows/gamepulse-pbpstats-missing-game-fallback.yml",
    ".github/workflows/gamepulse-28game-source-assemble.yml",
    ".github/workflows/gamepulse-28game-possession-tracking-crosswalk.yml",
    ".github/workflows/gamepulse-native-interactions-season-missing13.yml",
    ".github/workflows/gamepulse-two-game-chronology-acceptance.yml",
    ".github/workflows/gamepulse-universal-alignment-acceptance.yml",  # private-only CPU gate; universal source/clock/possession QA
    ".github/workflows/gamepulse-video-free-clock-season.yml",  # source-only daily CPU backfill; no video, no public player assets
    ".github/workflows/gamepulse-nba-official-advanced-ratings.yml",
    ".github/workflows/clip-lab-rockets-event80-hls.yml",
    ".github/workflows/gamepulse-native-interactions-partial-aggregate.yml",
    ".github/workflows/gamepulse-season-query-coverage-tests.yml",
    ".github/workflows/gamepulse-quarantined-native-labels.yml",
    ".github/workflows/gamepulse-unattributed-native-source.yml",
    ".github/workflows/gamepulse-unified-native-search.yml",
    ".github/workflows/gamepulse-native-interactions-0095-blueprint-quarantine.yml",
    "tools/licensed_feed/official_pbp_onoff_28.py",
    ".github/workflows/gamepulse-28game-native-pbp-onoff.yml",
    ".github/workflows/rockets-wemby-opponent-ppp.yml",
    ".github/workflows/freeview-amen-732-private-visual-panels.yml",
    ".github/workflows/freeview-amen-732-private-audio-sync.yml",
    ".github/workflows/freeview-amen-732-private-native.yml",
    ".github/workflows/gamepulse-season-backlog.yml",
    ".github/workflows/gamepulse-20261024-final-fastlane.yml",
    ".github/workflows/gamepulse-rockets-spurs-fusion-merge.yml",
    ".github/workflows/gamepulse-rockets-spurs-original-qa.yml",
    "tools/licensed_feed/verify_gameplay_0009.py",
    ".github/workflows/public-nba-gravity-onegame.yml",
    ".github/workflows/nba-blueprint-priority-private-acquire.yml",
    "public_nba_gravity_rockets_game1_2026_27.json",
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
    "tools/licensed_feed/live_discovery.mjs",
    "tools/licensed_feed/live_discovery.test.mjs",
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
    ".github/workflows/nba-ring-only-private-pilot.yml",
    ".github/workflows/nba-jabari616-camera-qa.yml",
    ".github/workflows/nba-jabari616-frozen-ring-cpu-qa.yml",
    ".github/workflows/nba-jabari616-constant-ring-render.yml",
    ".github/workflows/nba-jabari616-constant-ring-v2.yml",
    ".github/workflows/nba-jabari616-ring-export-to-chat.yml",
    ".github/workflows/nba-jabari616-ball-handler-media.yml",
    ".github/workflows/nba-jabari616-cumulative-five-rings.yml",
    ".github/workflows/nba-jabari616-frozen-v31-quality.yml",
    ".github/workflows/nba-jabari616-frozen-v31-efficient.yml",
    ".github/workflows/nba-jabari616-frozen-v31-pulse-dense.yml",
    ".github/workflows/nba-jabari616-cumulative-play12.yml",
    ".github/workflows/nba-jabari616-five-ring-public-preview.yml",
    ".github/workflows/nba-jabari616-frozen-v31-public-video.yml",
    ".github/workflows/nba-jabari616-cumulative-receivers.yml",
    ".github/workflows/gamepulse-pnr-feasibility.yml",
    ".github/workflows/rockets-pnr-unified-review-qa.yml",
    ".github/workflows/rockets-pnr-video-source-diagnostic.yml",
    ".github/workflows/rockets-pnr-0075-gamepulse-review.yml",
    ".github/workflows/rockets-all-defensive-pnr-analysis.yml",
    ".github/workflows/gamepulse-pnr-ui-preflight.yml",
    ".github/workflows/gamepulse-github-season.yml",
    ".github/workflows/gamepulse-live-cle-phi-20261022.yml",
    ".github/workflows/gamepulse-cavs-native-seek-diagnostic.yml",
    ".github/workflows/gamepulse-live-all-games.yml",
    "tools/licensed_feed/live_capture_cycle.mjs",
    "tools/licensed_feed/live_capture_cycle.test.mjs",
    "tools/licensed_feed/live_discovery.mjs",
    "tools/licensed_feed/live_discovery.test.mjs",
    ".github/workflows/gamepulse-final-fastlane.yml",
    ".github/workflows/gamepulse-rockets-finalize-safeguard.yml",
    ".github/workflows/gamepulse-20261022-slate-backfill.yml",
    ".github/workflows/gamepulse-20261022-targeted-retry.yml",
    ".github/workflows/gamepulse-source-ready-final10.yml",
    ".github/workflows/gamepulse-part6-fast.yml",
    ".github/workflows/gamepulse-14game-world-source-qa.yml",
    ".github/workflows/gamepulse-private-search-index.yml",
    ".github/workflows/gamepulse-16game-private-search.yml",
    ".github/workflows/gamepulse-denver-sdk-recovery.yml",
    ".github/workflows/gamepulse-denver-official-pbp.yml",
    ".github/workflows/gamepulse-16game-coverage-qa.yml",
    ".github/workflows/gamepulse-denver-source-ready-retry.yml",
    ".github/workflows/gamepulse-private-blueprint-fusion.yml",
    ".github/workflows/gamepulse-2026-source-evidence.yml",
    ".github/workflows/gamepulse-official-onoff-qa.yml",
    ".github/workflows/gamepulse-formal-pbp-14game.yml",
    ".github/workflows/rockets-three-player-touch-probe.yml",
    ".github/workflows/rockets-native-touch-ppp.yml",
    ".github/workflows/gamepulse-native-interactions-14game.yml",
    ".github/workflows/gamepulse-interaction-query.yml",
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
# These already-public, manually inspected CPU-only workflow definitions are
# pinned to exact Git blobs. New or edited workflows must be re-reviewed;
# the pin does not authorize source datasets, binaries or public results.
REVIEWED_WORKFLOW_GIT_BLOB_SHA = {
    ".github/workflows/clip-lab-frozen-ring-sprites.yml": "a002f86a91280330248438f837bb2d5e7c51d99c",  # inspected: only generated RGBA ring sprites and metadata uploaded
    ".github/workflows/clip-lab-rockets-219-hls.yml": "16d9d45f0d718271049b894adbdf8375b9d22b5d",
    ".github/workflows/clip-lab-rockets-new-double-346-hls.yml": "330309713345d92819ebf61f46ca39fc7d7df969",
    ".github/workflows/clip-lab-rockets-new-double-353-hls.yml": "0fe06a115dd1f2c18c74a1be28753f1d63d41a44",
    ".github/workflows/clip-lab-rockets-new-double-616-hls.yml": "6b3185d4281a537492472914901102668bd409de",
    ".github/workflows/durant-context-inspection.yml": "90af2d117e4206b44861283e95e0c9440eca90d1",
    ".github/workflows/gamepulse-rockets-durant-double-review-v4.yml": "f396fc7957b5a49f8b9abb38bbb309a17b1c1c1a",
    ".github/workflows/gamepulse-rockets-event616-double-fn.yml": "8490170f6437241f4098bf6f0bd853ed91726149",
    ".github/workflows/gamepulse-rockets-sengun-double-4ft.yml": "2fd90ab0271963a3cfb9bf64336d50bbb0c78ab7",
    ".github/workflows/gamepulse-rockets-sengun-double-4ft-v2.yml": "0b870d0e02b71eebcee3bc3a890fe24530dfee68",
    ".github/workflows/gamepulse-rockets-sengun-double-relaxed-v3.yml": "0a6caf4914853cb8487468c092a01f7c7bd0279c",
    ".github/workflows/gamepulse-rockets-sengun-hub-qa.yml": "e9a8a41ab0d8b6ecf390d2fb847a8d2351765dbe",
    ".github/workflows/nba-jabari616-ball-handler-media.yml": "779830fa72713804709cc6455a91c702586c784b",
    ".github/workflows/nba-jabari616-pulse-frozen-ring-render.yml": "e0e9621b82a6da6f31bf27cbeb71232403fd346b",
    ".github/workflows/gamepulse-wemby-advanced-boxscore-0022600009.yml": "0aab6eb3a993d9d6a88776bad4a233029748c7ef",
    ".github/workflows/nba-jabari616-ring-export-to-chat.yml": "f63f723f34e03b12723389b1e84b3eb6de5b4e6e",
    ".github/workflows/rockets-durant-double-team-clip-verification.yml": "2d9573e710d1ad19e7ee68a202f35a8775cb4503",
    ".github/workflows/rockets-durant-reviewed-halfcourt-v5.yml": "bdb6e1d1062dff439c19ca85c8191c71a9aaecc8",
    ".github/workflows/rockets-remaining-sengun-double-clips.yml": "8f2a1d85f88845732f1139740eede73604cbde2c",
}

# Two reviewed, immutable handoff workflows may upload only their audited
# artifacts. In particular, the encrypted handoff's recipient certificate must
# also remain byte-for-byte pinned: changing the recipient would expose the
# private source bundle to an unintended decryptor.
REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA = {
    ".github/workflows/clip-lab-artifact-handoff-smoke.yml": "c82cd5194d384e32acd1bf0cb42a0064e5703af7",
    ".github/workflows/clip-lab-encrypted-event86-handoff.yml": "4fb87ada769b0422c24afae0a60470c0d04bae3b",
}
REVIEWED_HANDOFF_CERT_GIT_BLOB_SHA = {
    "tools/clip_lab_public_handoff_cert.pem": "b3e84c69c35e061580dd3a4e6201c07f4adbdc19",
}

REVIEWED_MEDIA_SOURCE_WORKFLOWS = {
    ".github/workflows/clip-lab-rockets-219-hls.yml",
    ".github/workflows/clip-lab-rockets-new-double-346-hls.yml",
    ".github/workflows/clip-lab-rockets-new-double-353-hls.yml",
    ".github/workflows/clip-lab-rockets-new-double-616-hls.yml",
    ".github/workflows/rockets-durant-double-team-clip-verification.yml",
    ".github/workflows/rockets-remaining-sengun-double-clips.yml",
}
REVIEWED_PUBLIC_MP4_EXPORT_WORKFLOWS = {
    ".github/workflows/clip-lab-event80-direct-native-frozen.yml",  # one final QA-approved annotated MP4, never private source/tracking
    ".github/workflows/clip-lab-rockets-event80-frozen-render.yml",  # ONLY QA-approved ringed MP4 artifact
    ".github/workflows/clip-lab-event80-delivery-smoke.yml",  # harmless test fixture upload
    ".github/workflows/nba-jabari616-ball-handler-media.yml",
    ".github/workflows/nba-jabari616-ring-export-to-chat.yml",
    ".github/workflows/nba-jabari616-cumulative-receivers.yml",
}
# Reviewed immutable sprite export produces only generated RGBA PNG atlases and metadata;
# no source positions, tracking frames, or raw private SDK observations are uploaded.
REVIEWED_PUBLIC_SPRITE_EXPORT_WORKFLOWS = {
    ".github/workflows/clip-lab-frozen-ring-sprites.yml",
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
        if rel not in ALLOWED_STATIC and rel not in REVIEWED_WORKFLOW_GIT_BLOB_SHA and not any(rel.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            bad.append(violation("NOT_ALLOWLISTED", rel))
            continue
        if not p.is_file():
            continue
        pinned_sha = (
            REVIEWED_WORKFLOW_GIT_BLOB_SHA.get(rel)
            or REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA.get(rel)
            or REVIEWED_HANDOFF_CERT_GIT_BLOB_SHA.get(rel)
        )
        if pinned_sha:
            current = subprocess.check_output(["git", "hash-object", rel], text=True).strip()
            if current != pinned_sha:
                bad.append(violation("REVIEWED_WORKFLOW_OR_CERT_CHANGED", rel))
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
                # User-authorised publication of ONE rendered NBA clip, never
                # raw tracking or canonical private database records.
                if (code == "ACTIONS_ARTIFACT_UPLOAD" and
                    (rel in REVIEWED_PUBLIC_MP4_EXPORT_WORKFLOWS
                     or rel in REVIEWED_PUBLIC_SPRITE_EXPORT_WORKFLOWS
                     or rel in REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA)):
                    continue
                # Existing exact-blob NBA clip locator workflows contain the
                # public clips.nba.com origin, never signed media URLs.
                if (code == "MEDIA_SOURCE_URL" and
                    rel in REVIEWED_MEDIA_SOURCE_WORKFLOWS and
                    all(m.group(0).lower() == "clips.nba.com"
                        for m in rx.finditer(text))):
                    continue
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
