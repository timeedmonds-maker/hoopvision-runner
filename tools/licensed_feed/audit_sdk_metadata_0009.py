#!/usr/bin/env python3
"""Private SHA-verified inventory of original NBA SDK metadata for 0022600009.

This is a discovery-only source audit. No native positions, player identifiers,
event values, URLs or credentials enter public logs or artifacts. A metadata key
is not a certified clock alignment, possession, or live-play observation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

REPO = "timeedmonds-maker/104"
GAME = "0022600009"
TAG = "gamepulse-sdk-" + GAME
OUTPUT = "sdk-original-metadata-clock-inventory-0022600009.json"
PARTS = 13


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True,
                            timeout=240, check=False)
    if result.returncode:
        # stderr can contain private URLs and is intentionally never printed.
        raise RuntimeError("PRIVATE_GITHUB_COMMAND_FAILED_" + args[0].upper())
    return result.stdout


def category(key):
    key = re.sub(r"[^a-z0-9]", "", str(key).lower())
    if key in ("period", "quarter", "gameperiod", "periodnumber"):
        return "POSSIBLE_PERIOD"
    if "gameclock" in key or key in ("clockremaining", "periodclock"):
        return "POSSIBLE_NBA_GAME_CLOCK"
    if "shotclock" in key:
        return "POSSIBLE_SHOT_CLOCK"
    if key in ("nbaactionid", "nbaactionnumber", "actionid", "actionnumber",
               "eventid", "eventnumber", "ngsseventid", "playid"):
        return "POSSIBLE_EVENT_ID"
    if "possession" in key:
        return "POSSIBLE_POSSESSION"
    return None


def value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "other"


def add_keys(store, scope, item):
    if not isinstance(item, dict):
        return
    for key, value in item.items():
        if key == "positions":
            continue
        store[(scope, str(key), value_type(value))] += 1


def inventory():
    require(os.environ.get("GH_TOKEN"), "PRIVATE_TOKEN_UNAVAILABLE")
    release = json.loads(gh("api", f"repos/{REPO}/releases/tags/{TAG}"))
    require(release.get("tag_name") == TAG, "WRONG_RELEASE")
    assets = {a["name"]: a for a in release.get("assets", [])}
    expected = [f"sdk-part-{i:02d}.tar.gz" for i in range(PARTS)]
    sidecars = [f"sdk-part-{i:02d}.json" for i in range(PARTS)]
    require(set(expected + sidecars).issubset(assets), "MISSING_ORIGINAL_PARTS")
    key_types = Counter()
    counts = Counter()
    part_digests = {}
    with tempfile.TemporaryDirectory(prefix="private-original-metadata-") as temp:
        root = Path(temp)
        gh("release", "download", TAG, "--repo", REPO,
           "--pattern", "sdk-part-*.tar.gz", "--pattern", "sdk-part-*.json",
           "--dir", temp)
        for part_name, sidecar_name in zip(expected, sidecars):
            original = (root / part_name).read_bytes()
            sidecar_raw = (root / sidecar_name).read_bytes()
            original_sha = digest(original)
            require(assets[part_name].get("digest") == "sha256:" + original_sha,
                    "RELEASE_ORIGINAL_SHA256_MISMATCH")
            require(assets[sidecar_name].get("digest") == "sha256:" + digest(sidecar_raw),
                    "RELEASE_SIDECAR_SHA256_MISMATCH")
            sidecar = json.loads(sidecar_raw)
            require(sidecar.get("archive_sha256") == original_sha,
                    "SIDECAR_ORIGINAL_SHA256_MISMATCH")
            part_digests[part_name] = original_sha
            with tarfile.open(fileobj=io.BytesIO(original), mode="r:gz") as archive:
                manifest_file = archive.extractfile("manifest.json")
                require(manifest_file is not None, "ORIGINAL_MANIFEST_MISSING")
                manifest = json.load(manifest_file)
                require(manifest.get("game_id") == GAME and
                        manifest.get("observed") is True and
                        manifest.get("imputed") is False,
                        "ORIGINAL_SOURCE_SCOPE_OR_IMPUTATION_INVALID")
                counts["source_declared_successful_windows"] += int(
                    manifest.get("successful_windows", 0))
                add_keys(key_types, "manifest", manifest)
                slot_file = archive.extractfile("raw-slots.jsonl.gz")
                require(slot_file is not None, "ORIGINAL_RAW_SLOTS_MISSING")
                with gzip.GzipFile(fileobj=slot_file) as stream:
                    for line in stream:
                        if not line.strip():
                            continue
                        slot = json.loads(line)
                        require(isinstance(slot, dict) and
                                isinstance(slot.get("events"), list),
                                "INVALID_ORIGINAL_SLOT")
                        counts["original_raw_slots"] += 1
                        add_keys(key_types, "slot", slot)
                        for event in slot["events"]:
                            if not isinstance(event, dict):
                                counts["non_object_events"] += 1
                                continue
                            counts["original_events"] += 1
                            add_keys(key_types, "event", event)
                            metadata = event.get("metadata")
                            if not isinstance(metadata, dict):
                                counts["events_without_object_metadata"] += 1
                                continue
                            add_keys(key_types, "event.metadata", metadata)
                            frames = metadata.get("keyframes")
                            if not isinstance(frames, list):
                                counts["events_without_keyframe_list"] += 1
                                continue
                            for frame in frames:
                                if not isinstance(frame, dict):
                                    continue
                                counts["original_keyframes"] += 1
                                add_keys(key_types, "event.metadata.keyframes[]", frame)
                                # Coordinates are intentionally never inspected.
        rows = [{"scope": scope, "key": key, "type": typ, "observations": n,
                 "candidate_kind": category(key)}
                for (scope, key, typ), n in sorted(key_types.items())]
        candidates = [row for row in rows if row["candidate_kind"]]
        qa = {
            "schema": "gamepulse.private-original-sdk-metadata-clock-inventory.v1",
            "game_id": GAME,
            "source_release": TAG,
            "original_archive_sha256": part_digests,
            "original_parts_verified": PARTS,
            "counts": dict(sorted(counts.items())),
            "field_type_inventory": rows,
            "direct_clock_or_event_field_candidates": candidates,
            "discovery_state": ("DIRECT_METADATA_FIELD_CANDIDATES_UNVERIFIED"
                                if candidates else "NO_DIRECT_NATIVE_NBA_TIME_FIELD_SEEN"),
            "nba_clock_alignment_independently_certified": False,
            "gameplay_coverage_certified": False,
            "physical_possessions_certified": 0,
            "source_values_or_coordinates_published": False,
            "note": "Candidate names/types alone do not prove NBA-clock or event-ID correspondence."
        }
        destination = root / OUTPUT
        destination.write_text(json.dumps(qa, sort_keys=True, indent=2) + "\n")
        gh("release", "upload", TAG, str(destination), "--repo", REPO, "--clobber")
        fresh = json.loads(gh("api", f"repos/{REPO}/releases/tags/{TAG}"))
        matches = [a for a in fresh.get("assets", []) if a["name"] == OUTPUT]
        require(len(matches) == 1 and
                matches[0].get("digest") == "sha256:" + digest(destination.read_bytes()),
                "PRIVATE_QA_RELEASE_SHA256_READBACK_FAILED")
    print("ORIGINAL_SDK_METADATA_QA_PRIVATE_SHA_VERIFIED",
          "parts=13",
          "raw_slots=" + str(counts["original_raw_slots"]),
          "events=" + str(counts["original_events"]),
          "field_candidates=" + str(len(candidates)),
          "clock_certified=false",
          "physical_possessions_certified=0")


def self_test():
    assert category("gameClockTime") == "POSSIBLE_NBA_GAME_CLOCK"
    assert category("shot_clock") == "POSSIBLE_SHOT_CLOCK"
    assert category("ngssEventId") == "POSSIBLE_EVENT_ID"
    assert category("period") == "POSSIBLE_PERIOD"
    assert category("possessionId") == "POSSIBLE_POSSESSION"
    assert category("timestamp") is None
    assert category("lastTouch") is None
    assert value_type(True) == "bool"
    assert value_type(1) == "number"
    assert value_type({}) == "object"
    seen = Counter()
    add_keys(seen, "frame", {"positions": {"secret": [1, 2, 3]}, "timestamp": 1})
    assert len(seen) == 1 and ("frame", "timestamp", "number") in seen
    print("ORIGINAL_SDK_METADATA_SYNTHETIC_TESTS_PASS")


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        self_test()
    else:
        inventory()
