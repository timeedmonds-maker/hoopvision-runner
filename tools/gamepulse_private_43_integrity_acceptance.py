#!/usr/bin/env python3
"""Private-only 43+ game warehouse integrity acceptance. No source frames are printed.

This validates manifest membership and SHA-256 of materialized per-game views.
It deliberately does NOT certify gameplay, a physical possession, clock/video PTS,
or independent SDK player/team identity.
"""
import argparse
import hashlib
import json
from pathlib import Path

CAT = "gamepulse/catalog/2026-27-auto-refresh-provisional.json"
FUSION = "gamepulse/fusion/index/index.json"
TRACK = "gamepulse/fusion/tracking_onoff/index.json"
PBP = "gamepulse/fusion/official_pbp_timing/index-2026-27-through-20261025.json"
PROVIDER = "gamepulse/fusion/onoff/index-2026-27-through-20261025.json"
STATUS = "gamepulse/fusion/status.json"
ROCKETS_QA = "gamepulse/fusion/qa/0022600009_original_gameplay_source_qa.json"
OUTPUT = "gamepulse/fusion/qa/season43_integrity_acceptance.json"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(root, rel):
    full = root / rel
    return json.loads(full.read_bytes()), sha(full.read_bytes())


def same_games(expected, *indexes):
    for ix in indexes:
        if set(ix["games"]) != expected:
            raise RuntimeError("SEASON_MANIFEST_GAME_SET_MISMATCH")


def score_reconciled(qa):
    """Recognize both source-verified NBA terminal-score QA representations."""
    return (qa.get("nba_score_reconciled_to_boxscore") is True or
            qa.get("official_terminal_score_reconciled") == 1)


def validate(root):
    docs = {}
    digests = {}
    for path in (CAT, FUSION, TRACK, PBP, PROVIDER, STATUS, ROCKETS_QA):
        docs[path], digests[path] = read(root, path)
    catalog, fusion, tracking, pbp, provider = (docs[k] for k in
        (CAT, FUSION, TRACK, PBP, PROVIDER))
    status, qa = docs[STATUS], docs[ROCKETS_QA]
    ids = set(catalog["games"])
    if (catalog.get("season") != "2026-27" or
            catalog.get("game_count") != len(ids) or len(ids) < 43):
        raise RuntimeError("VERIFIED_SEASON_COUNT_INCONSISTENT")
    same_games(ids, fusion, tracking, pbp, provider)
    if (pbp["game_count"] != len(ids) or provider["game_count"] != len(ids) or
            provider.get("complete_43") is not True or
            provider.get("missing_new_games") or
            provider.get("prior_36_preserved") is not True):
        raise RuntimeError("PROVIDER_FORTY_THREE_SOURCE_INCOMPLETE")
    if (fusion.get("contains_raw_XYZ") is not False or
            tracking.get("no_fabrication") is not True or
            tracking.get("certified_possessions") != 0 or
            provider.get("native_possession_chain_certified") is not False):
        raise RuntimeError("SCIENTIFIC_QA_PROMOTION_OR_RAW_PUBLIC_VIEW")
    if (status.get("games") != len(ids) or
            status.get("official_pbp_verified_games") != len(ids) or
            status.get("nba_provider_onoff_verified_games") != len(ids) or
            status.get("official_pbp_index") != PBP or
            status.get("nba_provider_onoff_index") != PROVIDER or
            status.get("independently_certified_full_possession_chains") != 0):
        raise RuntimeError("CANONICAL_STATUS_NOT_CURRENT")
    for game in catalog["games"].values():
        if (game.get("index_state") != "VERIFIED_ARCHIVE_INDEX" or
                not game.get("source_signature")):
            raise RuntimeError("UNVERIFIED_SDK_ARCHIVE")
    total_shots = total_frames = total_complete = total_xman = 0
    for gid in sorted(ids):
        fi = fusion["games"][gid]
        tv = tracking["games"][gid]
        pi = pbp["games"][gid]
        oi = provider["games"][gid]
        fpath = "gamepulse/fusion/index/games/" + gid + ".json"
        tpath = "gamepulse/fusion/tracking_onoff/games/" + gid + ".json"
        ppath = "gamepulse/fusion/official_pbp_timing/games/" + gid + ".json"
        opath = "gamepulse/fusion/onoff/games/" + gid + ".json"
        if (fi.get("path") != fpath or tv.get("path") != tpath or
                pi.get("source_file") != ppath or oi.get("path") != opath):
            raise RuntimeError("UNTRUSTED_GAME_VIEW_PATH")
        fview, fd = read(root, fpath)
        tview, _ = read(root, tpath)
        pview, _ = read(root, ppath)
        oview, od = read(root, opath)
        if (fi.get("sha256") != fd or oi.get("sha256") != od or
                any(v.get("game_id") != gid for v in (fview, tview, pview, oview))):
            raise RuntimeError("GAME_VIEW_SOURCE_SHA_OR_ID_MISMATCH")
        if (fi.get("shot_rows") != len(fview.get("shots", [])) or
                tv.get("records") != len(tview.get("lineups", [])) or
                tv.get("sampled_5v5") != tview.get("eligible_complete_5v5_samples")):
            raise RuntimeError("PER_GAME_COUNTS_MISMATCH")
        if (pi.get("action_records") != len(pview.get("actions", [])) or
                pview.get("source_provenance", {}).get("nba_pbp_sha256") !=
                pi.get("source_pbp_sha256") or
                not score_reconciled(pview.get("qa", {}))):
            raise RuntimeError("OFFICIAL_NBA_PBP_PROVENANCE_MISMATCH")
        if (oview.get("source_qa", {}).get("official_source") !=
                "NBA_TEAM_PLAYER_ONOFF_SUMMARY_AND_TEAM_DASH_LINEUPS" or
                oview.get("source_qa", {}).get("player_onoff_conflicts") != 0):
            raise RuntimeError("NBA_PROVIDER_ONOFF_SOURCE_NOT_RECONCILED")
        if tv.get("certified_possessions") != 0:
            raise RuntimeError("PHYSICAL_POSSESSION_CERTIFICATION_UNSUPPORTED")
        total_shots += fi["shot_rows"]
        total_frames += fi["observed_tracking_frames"]
        total_complete += fi["exact_5v5_frames"]
        total_xman += tv["records"]
    if (total_shots != status["shots"] or
            total_frames != status["tracking_frames"] or
            total_complete != status["exact_5v5_frames"] or
            total_xman != status["xman_index_rows"] or
            total_complete != tracking["native_5v5_samples"] or
            total_xman != tracking["xman_onoff_rows"]):
        raise RuntimeError("PRIVATE_WAREHOUSE_TOTALS_MISMATCH")
    if (fusion["games"]["0022600009"]["shot_rows"] != 155 or
            tracking["games"]["0022600009"]["records"] != 577 or
            qa.get("game_id") != "0022600009" or
            qa.get("source_parts_sha256_verified") != 13 or
            qa.get("source_windows_sha256_verified") != 3720 or
            any(qa.get(k) is not False for k in (
                "tracking_gameplay_certified", "independent_player_team_id_certified",
                "possession_lineup_chain_certified", "video_pts_certified"))):
        raise RuntimeError("ROCKETS_ORIGINAL_QA_PROVENANCE_INVALID")
    return {
        "schema": "gamepulse.private-season43-source-index-integrity.v1",
        "state": "SEASON43_SOURCE_INDEX_SHA_ACCEPTED_PHYSICAL_QA_INCOMPLETE",
        "game_count": len(ids),
        "source_index_sha256": {p: digests[p] for p in
            (CAT, FUSION, TRACK, PBP, PROVIDER, STATUS, ROCKETS_QA)},
        "per_game_views_sha256_verified": {
            "blueprint_fusion": len(ids), "nba_provider_onoff": len(ids)},
        "per_game_views_source_checked": {
            "tracking_onoff": len(ids), "official_nba_pbp": len(ids)},
        "totals": {"blueprint_shots": total_shots, "observed_tracking_frames": total_frames,
                   "exact_5v5_frames": total_complete, "xman_lineups": total_xman},
        "rockets_0022600009": {
            "blueprint_shots": 155, "lineup_rows": 577,
            "original_temporal_source_qa": qa.get("temporal_source_coverage"),
            "fresh_original_nba_action_source": qa.get("nba_action_reference_is_fresh_original"),
            "tracking_gameplay_certified": False,
            "independent_player_team_id_certified": False,
            "possession_lineup_chain_certified": False, "video_pts_certified": False},
        "certified_physical_possessions": 0,
        "limitations": "SDK source archival integrity and searchable source-joined views are not independent gameplay, player ID, clock, video or physical possession certification."
    }


def selftest():
    expected = {"a", "b"}
    same_games(expected, {"games": {"a": 1, "b": 2}})
    try:
        same_games(expected, {"games": {"a": 1}})
    except RuntimeError:
        pass
    else:
        raise AssertionError("different source membership must fail")
    assert sha(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert score_reconciled({"nba_score_reconciled_to_boxscore": True})
    assert score_reconciled({"official_terminal_score_reconciled": 1})
    assert not score_reconciled({"official_terminal_score_reconciled": 0})
    print("PUBLIC_SYNTHETIC_SOURCE_INTEGRITY_TEST_PASSED")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        if args.root is None:
            ap.error("--root is required")
        report = validate(args.root)
        dest = args.root / OUTPUT
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
        if not dest.exists() or dest.read_bytes() != raw:
            dest.write_bytes(raw)
        print("PRIVATE_43_SEASON_SOURCE_INDEX_SHA_ACCEPTED", report["game_count"])
        print("ORIGINAL_GAMEPLAY_AND_PHYSICAL_POSSESSION_NOT_CERTIFIED")
