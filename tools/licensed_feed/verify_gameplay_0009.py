#!/usr/bin/env python3
"""Rockets-Spurs 0022600009: private original-source temporal QA, not tracking certification.

All licensed coordinates stay in ephemeral runner memory. Only aggregate QA is
uploaded to private 104. 13 successful SDK chunks are not evidence of gameplay.
"""
from __future__ import annotations
from bisect import bisect_left
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

GAME = "0022600009"
REPO = "timeedmonds-maker/104"
TAG = "gamepulse-sdk-" + GAME
TIPOFF = int(datetime(2026, 10, 24, 1, 30, tzinfo=timezone.utc).timestamp() * 1000)
BEGIN = TIPOFF - 600_000
PARTS = 13
SLOT_MS = 5_000
PART_WINDOWS = 300
EXPECTED_WINDOWS = 3720
OUTPUT = "gameplay-QA-original-0022600009.json"


def gh(*args):
    # The shared private-release token may hit transient GitHub secondary limits.
    # One bulk asset download avoids 27 separate release API listings.
    import time
    for attempt in range(6):
        result = subprocess.run(["gh", *args], text=True, capture_output=True, timeout=240)
        if result.returncode == 0:
            return result.stdout
        detail = (result.stderr or "").lower()
        category = ("rate_limit" if "rate limit" in detail or "too many requests" in detail
                    else "not_found" if "404" in detail or "not found" in detail
                    else "authorization" if "401" in detail or "403" in detail
                    else "network" if any(s in detail for s in ("timeout", "connection", "tls"))
                    else "other")
        # Never print stderr, paths, source frames, signed URLs or tokens.
        print("ORIGINAL_QA_PRIVATE_GITHUB_FAILURE", args[0], category,
              "attempt", attempt + 1, flush=True)
        if category not in ("rate_limit", "network") or attempt == 5:
            raise RuntimeError("private_github_" + category)
        time.sleep(min(90, 15 * (attempt + 1)))
    raise RuntimeError("private_github_retries_exhausted")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unix_ms(value):
    if not isinstance(value, str):
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def nearest_gap(sorted_stamps, target):
    if not sorted_stamps:
        return None
    i = bisect_left(sorted_stamps, target)
    return min(abs(sorted_stamps[j] - target)
               for j in (i - 1, i) if 0 <= j < len(sorted_stamps))


def independent_nba():
    """Prefer live NBA originals; fall back to an explicitly labelled private derivative.

    The fallback is *not* a fresh independent-source verification. It supplies
    quarter action timestamps for gap diagnostics when NBA CDN blocks runner
    egress, but must never upgrade the original-source certification gate.
    """
    from verify_gameplay import official
    status = "unverified"
    periods = {p: [] for p in range(1, 5)}
    try:
        box = official("boxscore/boxscore_" + GAME + ".json").get("game") or {}
        if str(box.get("gameId")) == GAME and str(box.get("gameStatus")) == "3":
            status = "final"
    except Exception:
        pass
    try:
        game = official("playbyplay/playbyplay_" + GAME + ".json").get("game") or {}
        if str(game.get("gameId")) == GAME:
            for action in game.get("actions", []):
                if not isinstance(action, dict):
                    continue
                period = action.get("period")
                if period not in periods:
                    continue
                stamp = unix_ms(action.get("timeActual"))
                if stamp is not None:
                    periods[period].append(stamp)
    except Exception:
        pass
    if status == "final" and all(periods.values()):
        return status, periods, "LIVE_NBA_OFFICIAL"

    # Only a private canonical 104 artifact is allowed here. No public data,
    # licensed positions, or original action payloads enter public logs.
    import base64
    path = f"gamepulse/fusion/official_pbp_timing/games/{GAME}.json"
    try:
        response = json.loads(gh("api", f"repos/{REPO}/contents/{path}?ref=main"))
        raw = base64.b64decode(response["content"])
        # Check GitHub's content-addressed blob before trusting the payload.
        blob_sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob_sha != response.get("sha"):
            raise RuntimeError("private_nba_reference_blob_sha_mismatch")
        reference = json.loads(raw)
        provenance = reference.get("source_provenance") or {}
        actions = reference.get("actions") or []
        qa = reference.get("qa") or {}
        if (reference.get("game_id") != GAME or
            provenance.get("nba_pbp_url") !=
                f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{GAME}.json" or
            not isinstance(provenance.get("nba_pbp_sha256"), str) or
            len(provenance["nba_pbp_sha256"]) != 64 or
            qa.get("nba_score_reconciled_to_boxscore") is not True or
            qa.get("nba_actions_with_formal_utc") != len(actions) or
            reference.get("official_final", {}).get("home", {}).get("score") != 110 or
            reference.get("official_final", {}).get("away", {}).get("score") != 114):
            raise RuntimeError("private_nba_reference_provenance_invalid")
        stored = {p: [] for p in range(1, 5)}
        for action in actions:
            period = action.get("period")
            stamp = action.get("official_timeActual_utc_ms")
            if period in stored and isinstance(stamp, int):
                stored[period].append(stamp)
        if not all(stored.values()):
            raise RuntimeError("private_nba_reference_periods_missing")
        return "final", stored, "PRIVATE_NBA_PBP_DERIVED_NOT_FRESH"
    except Exception as exc:
        # Do not suppress malformed evidence; this is a diagnostic fallback.
        print("PRIVATE_NBA_REFERENCE_FALLBACK_UNAVAILABLE", type(exc).__name__)
        return status, periods, "LIVE_NBA_INCOMPLETE"


def frame_position_presence(positions):
    """Player and ball keys must coexist in one original SDK frame."""
    return (any(pid != "ball" for pid in positions), "ball" in positions)


def observed_slot_diagnostic(player_stamps, ball_stamps, first_ms, last_ms):
    """Count original position-bearing 5s bins; never infer missing observations.

    Official action UTC bounds define a diagnostic span, not gameplay possession
    boundaries or proof that every intervening slot contains live game action.
    """
    if (not isinstance(first_ms, int) or not isinstance(last_ms, int)
            or last_ms < first_ms):
        return {"status": "NO_OFFICIAL_ACTION_SPAN", "certified": False}
    lo = max(0, (first_ms - BEGIN) // SLOT_MS)
    hi = min(EXPECTED_WINDOWS - 1, (last_ms - BEGIN) // SLOT_MS)
    if hi < lo:
        return {"status": "OFFICIAL_ACTION_SPAN_OUTSIDE_CAPTURE", "certified": False}
    def bins(stamps):
        return {(t - BEGIN) // SLOT_MS for t in stamps
                if isinstance(t, int) and BEGIN <= t < BEGIN + EXPECTED_WINDOWS * SLOT_MS
                and lo <= (t - BEGIN) // SLOT_MS <= hi}
    players, ball = bins(player_stamps), bins(ball_stamps)
    both = players & ball
    longest_missing = run = 0
    for slot in range(lo, hi + 1):
        run = 0 if slot in both else run + 1
        longest_missing = max(longest_missing, run)
    return {
        "status": "OBSERVED_TEMPORAL_BINS_ONLY",
        "certified": False,
        "official_action_span_5s_bins": hi - lo + 1,
        "bins_with_original_player_positions": len(players),
        "bins_with_original_ball_position": len(ball),
        "bins_with_both_player_and_ball": len(both),
        "bins_without_both": hi - lo + 1 - len(both),
        "longest_consecutive_bins_without_both": longest_missing,
    }


def audit():
    release = json.loads(gh("api", f"repos/{REPO}/releases/tags/{TAG}"))
    assets = {a["name"]: a for a in release.get("assets", [])}
    expected = ["sdk-COMPLETE.json"] + [
        f"sdk-part-{p:02d}.{ext}" for p in range(PARTS)
        for ext in ("json", "tar.gz")]
    if not set(expected) <= set(assets):
        raise RuntimeError("private_release_assets_missing")
    timestamps = set()
    player_timestamps = set()
    ball_timestamps = set()
    same_frame_player_ball_timestamps = set()
    part_qa = []
    total_windows = 0
    with tempfile.TemporaryDirectory(prefix="gp-original-qa-") as folder:
        root = Path(folder)
        gh("release", "download", TAG, "--repo", REPO,
           "--pattern", "sdk-COMPLETE.json",
           "--pattern", "sdk-part-*.json",
           "--pattern", "sdk-part-*.tar.gz", "--dir", folder)
        for part in range(PARTS):
            stem = f"sdk-part-{part:02d}"
            names = (stem + ".json", stem + ".tar.gz")
            for name in names:
                data = (root / name).read_bytes()
                if assets[name].get("digest") != "sha256:" + digest(data):
                    raise RuntimeError("release_asset_sha256_mismatch")
            sidecar = json.loads((root / names[0]).read_text())
            archive = (root / names[1]).read_bytes()
            if sidecar.get("archive_sha256") != digest(archive):
                raise RuntimeError("checkpoint_sidecar_sha256_mismatch")
            count = PART_WINDOWS if part < 12 else 120
            begin = BEGIN + part * PART_WINDOWS * SLOT_MS
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
                manifest = json.load(tar.extractfile("manifest.json"))
                for field in ("game_id", "start_ms", "successful_windows",
                              "frames_with_players", "frames_with_ball",
                              "empty_windows"):
                    if sidecar.get(field) != manifest.get(field):
                        raise RuntimeError("checkpoint_manifest_sidecar_mismatch")
                if (manifest.get("game_id") != GAME or
                        manifest.get("start_ms") != begin or
                        manifest.get("successful_windows") != count or
                        manifest.get("observed") is not True or
                        manifest.get("imputed") is not False):
                    raise RuntimeError("checkpoint_identity_or_window_invalid")
                n_frames = 0
                n_player = 0
                n_ball = 0
                with gzip.open(io.BytesIO(tar.extractfile("frames.jsonl.gz").read()),
                               "rt", encoding="utf-8") as stream:
                    for line in stream:
                        if not line.strip():
                            continue
                        frame = json.loads(line)
                        stamp = frame.get("timestamp")
                        pos = frame.get("positions")
                        if (not isinstance(stamp, int) or
                                not TIPOFF - 3_600_000 <= stamp <= TIPOFF + 8 * 3_600_000 or
                                not isinstance(pos, dict)):
                            raise RuntimeError("invalid_source_frame")
                        n_frames += 1
                        timestamps.add(stamp)
                        has_player, has_ball = frame_position_presence(pos)
                        if has_player:
                            n_player += 1
                            player_timestamps.add(stamp)
                        if has_ball:
                            n_ball += 1
                            ball_timestamps.add(stamp)
                        if has_player and has_ball:
                            # Same original source frame, not merely a shared 5s bin.
                            same_frame_player_ball_timestamps.add(stamp)
                if (n_frames != manifest.get("unique_keyframes") or
                        n_player != manifest.get("frames_with_players") or
                        n_ball != manifest.get("frames_with_ball")):
                    raise RuntimeError("original_source_frame_count_mismatch")
                part_qa.append({"part": part, "planned_windows": count,
                                "empty_windows": manifest.get("empty_windows"),
                                "source_frames": n_frames,
                                "frames_with_players": n_player,
                                "frames_with_ball": n_ball})
                total_windows += count
            for name in names:
                (root / name).unlink()
        complete_name = "sdk-COMPLETE.json"
        marker = (root / complete_name).read_bytes()
        if assets[complete_name].get("digest") != "sha256:" + digest(marker):
            raise RuntimeError("completion_marker_sha256_mismatch")
        complete = json.loads(marker)
        if (complete.get("game_id") != GAME or complete.get("parts") != PARTS or
                complete.get("successful_windows") != EXPECTED_WINDOWS or
                total_windows != EXPECTED_WINDOWS):
            raise RuntimeError("completion_marker_count_invalid")

    official_status, official_periods, reference_origin = independent_nba()
    sorted_players = sorted(player_timestamps)
    quarter_qa = {}
    for period, times in official_periods.items():
        gaps = [nearest_gap(sorted_players, t) for t in times]
        quarter_qa[str(period)] = {
            "independent_nba_actions_with_utc": len(times),
            "actions_with_observed_player_frame_within_30s":
                sum(g is not None and g <= 30_000 for g in gaps),
            "actions_with_observed_player_frame_within_60s":
                sum(g is not None and g <= 60_000 for g in gaps),
            "first_action_nearest_player_frame_gap_ms":
                nearest_gap(sorted_players, min(times)) if times else None,
            "last_action_nearest_player_frame_gap_ms":
                nearest_gap(sorted_players, max(times)) if times else None,
        }
    # Diagnostic only: compare source-bearing bins with original NBA action spans.
    # An observed bin can still be stoppage time; no interpolation or certification.
    quarter_observed_slots = {
        str(period): observed_slot_diagnostic(
            player_timestamps, ball_timestamps,
            min(times) if times else None, max(times) if times else None)
        for period, times in official_periods.items()
    }
    entire_capture_slots = observed_slot_diagnostic(
        player_timestamps, ball_timestamps, BEGIN,
        BEGIN + EXPECTED_WINDOWS * SLOT_MS - 1)
    # A player and ball in separate frames within one 5s bin is NOT
    # a jointly observed original source frame. Keep this stricter diagnostic
    # separate from the pre-existing coarse-bin screen; neither certifies play.
    same_frame_quarter_bins = {
        str(period): observed_slot_diagnostic(
            same_frame_player_ball_timestamps,
            same_frame_player_ball_timestamps,
            min(times) if times else None, max(times) if times else None)
        for period, times in official_periods.items()
    }
    same_frame_capture_bins = observed_slot_diagnostic(
        same_frame_player_ball_timestamps,
        same_frame_player_ball_timestamps,
        BEGIN, BEGIN + EXPECTED_WINDOWS * SLOT_MS - 1)
    q4 = quarter_qa["4"]
    source_verified = (total_windows == EXPECTED_WINDOWS and
                       len(player_timestamps) > 100 and len(ball_timestamps) > 50)
    temporal_supported = (source_verified and reference_origin == "LIVE_NBA_OFFICIAL" and
        official_status == "final" and
        all(quarter_qa[str(p)]["actions_with_observed_player_frame_within_60s"] > 0
            for p in range(1, 5)) and
        q4["last_action_nearest_player_frame_gap_ms"] is not None and
        q4["last_action_nearest_player_frame_gap_ms"] <= 120_000)
    return {
        "schema": "gamepulse-original-gameplay-temporal-qa.v1",
        "game_id": GAME,
        "source_release": TAG,
        "source_parts_sha256_verified": PARTS,
        "source_windows_sha256_verified": total_windows,
        "observed_unique_position_timestamps": len(timestamps),
        "observed_unique_player_timestamps": len(player_timestamps),
        "observed_unique_ball_timestamps": len(ball_timestamps),
        "first_player_timestamp_ms": min(player_timestamps) if player_timestamps else None,
        "last_player_timestamp_ms": max(player_timestamps) if player_timestamps else None,
        "original_source_part_qa": part_qa,
        "independent_nba_final_status": official_status,
        "nba_action_reference_origin": reference_origin,
        "nba_action_reference_is_fresh_original": reference_origin == "LIVE_NBA_OFFICIAL",
        "independent_nba_quarter_action_coverage": quarter_qa,
        "observed_original_source_5s_bin_diagnostics": {
            "entire_capture": entire_capture_slots,
            "official_quarter_action_spans": quarter_observed_slots,
            "interpretation": "Original position-bearing 5s timestamp bins, NOT "
                "scheduled SDK success slots, continuous gameplay, identity, "
                "shot-release timing or possession certification.",
        },
        "observed_original_same_frame_player_ball": {
            "unique_source_timestamps_with_both_position_keys":
                len(same_frame_player_ball_timestamps),
            "entire_capture_5s_bins": same_frame_capture_bins,
            "official_quarter_action_spans_5s_bins": same_frame_quarter_bins,
            "interpretation": "Both player and ball position keys appear in the "
                "same original source frame, not merely within one 5s bin. "
                "These are diagnostic source observations, not continuous "
                "gameplay, possession, or video timing certification.",
        },
        "temporal_source_coverage": "SUPPORTED" if temporal_supported else "INCONCLUSIVE",
        "tracking_gameplay_certified": False,
        "independent_player_team_id_certified": False,
        "possession_lineup_chain_certified": False,
        "video_pts_certified": False,
        "limitations": (
            "13 SDK parts and 3720 planned five-second slots do not prove 3720 "
            "gameplay observations. Quarter proximity is to official action UTC, "
            "not shot-release/video PTS. Missing positions are never imputed. "
            "Frame accuracy, independent identity, all-possession continuity "
            "and complete game-play coverage require separate original-source QA."
        ),
    }


def original_qa_blocker_codes(report):
    """Categorical diagnostics only; never expose original frames or timestamps."""
    codes = []
    if report.get("nba_action_reference_origin") != "LIVE_NBA_OFFICIAL":
        codes.append("FRESH_NBA_ACTION_SOURCE_NOT_VERIFIED")
    if report.get("independent_nba_final_status") != "final":
        codes.append("OFFICIAL_FINAL_NOT_VERIFIED")
    quarters = report.get("independent_nba_quarter_action_coverage") or {}
    for period in ("1", "2", "3", "4"):
        q = quarters.get(period) or {}
        if not q.get("independent_nba_actions_with_utc"):
            codes.append(f"Q{period}_NBA_UTC_ABSENT")
        elif not q.get("actions_with_observed_player_frame_within_60s"):
            codes.append(f"Q{period}_PLAYER_FRAME_NEAR_ACTION_ABSENT")
    q4 = quarters.get("4") or {}
    gap = q4.get("last_action_nearest_player_frame_gap_ms")
    if gap is None:
        codes.append("Q4_END_PLAYER_FRAME_UNVERIFIED")
    elif gap > 120_000:
        codes.append("Q4_END_PLAYER_FRAME_GT_120S")
    if report.get("observed_unique_player_timestamps", 0) <= 100:
        codes.append("OBSERVED_PLAYER_SOURCE_INSUFFICIENT")
    if report.get("observed_unique_ball_timestamps", 0) <= 50:
        codes.append("OBSERVED_BALL_SOURCE_INSUFFICIENT")
    if not (report.get("observed_original_same_frame_player_ball") or {}).get(
            "unique_source_timestamps_with_both_position_keys", 0):
        codes.append("OBSERVED_SAME_FRAME_PLAYER_BALL_ABSENT")
    return codes or ["TEMPORAL_SCREEN_PASSED_FULL_TRACKING_UNCERTIFIED"]


def private_qa_payload(data, current_sha=None):
    """Build a private-only, fail-closed GitHub contents update."""
    import base64
    report = json.loads(data)
    if (report.get("game_id") != GAME or
            report.get("source_parts_sha256_verified") != PARTS or
            report.get("source_windows_sha256_verified") != EXPECTED_WINDOWS or
            any(report.get(key) is not False for key in (
                "tracking_gameplay_certified",
                "independent_player_team_id_certified",
                "possession_lineup_chain_certified",
                "video_pts_certified"))):
        raise RuntimeError("private_qa_snapshot_certification_gate_invalid")
    payload = {
        "branch": "main",
        "message": "data(gamepulse): publish SHA-verified Rockets original gameplay QA (not certified)",
        "content": base64.b64encode(data).decode("ascii"),
    }
    if current_sha is not None:
        payload["sha"] = current_sha
    return payload


def publish_private_qa_snapshot(data):
    """Mirror only the aggregate QA to private 104 for searchable audit checks.

    Licensed original frames and per-frame positions never enter the public
    repository, logs or artifacts. This snapshot cannot promote certification.
    """
    import base64
    path = "gamepulse/fusion/qa/0022600009_original_gameplay_source_qa.json"
    endpoint = f"repos/{REPO}/contents/{path}"
    check = subprocess.run(
        ["gh", "api", endpoint + "?ref=main"], text=True,
        capture_output=True, timeout=120)
    current_sha = None
    if check.returncode == 0:
        current = json.loads(check.stdout)
        current_sha = current["sha"]
        existing = base64.b64decode(current["content"])
        if existing == data:
            return
    elif not any(x in (check.stderr or "").lower()
                 for x in ("404", "not found")):
        raise RuntimeError("private_qa_snapshot_preflight_failed")
    payload = private_qa_payload(data, current_sha)
    write = subprocess.run(
        ["gh", "api", "-X", "PUT", endpoint, "--input", "-"],
        input=json.dumps(payload), text=True, capture_output=True, timeout=120)
    if write.returncode:
        raise RuntimeError("private_qa_snapshot_write_failed")
    published = json.loads(gh("api", endpoint + "?ref=main"))
    raw = base64.b64decode(published["content"])
    blob_sha = hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()
    if raw != data or published.get("sha") != blob_sha:
        raise RuntimeError("private_qa_snapshot_readback_failed")


def main():
    report = audit()
    report["original_source_qa_blockers"] = original_qa_blocker_codes(report)
    with tempfile.TemporaryDirectory(prefix="gp-qa-readback-") as folder:
        root = Path(folder)
        local = root / OUTPUT
        local.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        expected_sha = digest(local.read_bytes())
        gh("release", "upload", TAG, str(local), "--repo", REPO, "--clobber")
        check = root / "readback"
        check.mkdir()
        gh("release", "download", TAG, "--repo", REPO,
           "--pattern", OUTPUT, "--dir", str(check))
        if digest((check / OUTPUT).read_bytes()) != expected_sha:
            raise RuntimeError("private_qa_readback_sha256_mismatch")
        publish_private_qa_snapshot(local.read_bytes())
    print("PRIVATE_ORIGINAL_GAMEPLAY_QA_SAVED", report["temporal_source_coverage"])
    for code in report["original_source_qa_blockers"]:
        print("ORIGINAL_QA_BLOCKER", code)
    print("TRACKING_GAMEPLAY_CERTIFIED_FALSE")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # No private data, signed URLs, raw frames, or tokens in public logs.
        print("PRIVATE_ORIGINAL_GAMEPLAY_QA_BLOCKED", type(exc).__name__)
        raise SystemExit(2)
