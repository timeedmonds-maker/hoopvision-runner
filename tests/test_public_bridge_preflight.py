from __future__ import annotations

import datetime as dt
import json

from tools.public_bridge_preflight import check


NOW = dt.datetime(2026, 10, 5, 0, 0, tzinfo=dt.timezone.utc)


def _write(tmp_path, doc):
    p = tmp_path / "heartbeat.json"
    p.write_text(json.dumps(doc))
    return p


def test_missing_heartbeat_blocks(tmp_path):
    got = check(tmp_path / "missing.json", now=NOW)
    assert got["ready"] is False
    assert got["status"] == "BLOCKED_NO_CONSUMER_HEARTBEAT"


def test_fresh_ready_heartbeat_passes(tmp_path):
    p = _write(
        tmp_path,
        {
            "schema": "hoopvision.public-consumer-heartbeat.v1",
            "consumer_contract": "public_outbox_private_pull.v1",
            "status": "READY",
            "observed_at_utc": "2026-10-04T23:55:00Z",
        },
    )
    got = check(p, max_age_s=900, now=NOW)
    assert got["ready"] is True
    assert got["status"] == "READY"


def test_stale_heartbeat_blocks(tmp_path):
    p = _write(
        tmp_path,
        {
            "schema": "hoopvision.public-consumer-heartbeat.v1",
            "consumer_contract": "public_outbox_private_pull.v1",
            "status": "READY",
            "observed_at_utc": "2026-10-04T23:00:00Z",
        },
    )
    got = check(p, max_age_s=900, now=NOW)
    assert got["ready"] is False
    assert got["status"] == "BLOCKED_CONSUMER_HEARTBEAT_STALE"


def test_future_dated_heartbeat_blocks(tmp_path):
    p = _write(
        tmp_path,
        {
            "schema": "hoopvision.public-consumer-heartbeat.v1",
            "consumer_contract": "public_outbox_private_pull.v1",
            "status": "READY",
            "observed_at_utc": "2099-01-01T00:00:00Z",
        },
    )
    got = check(p, max_age_s=900, now=NOW)
    assert got["ready"] is False
    assert got["status"] == "BLOCKED_HEARTBEAT_TIMESTAMP_INVALID"


def test_privacy_sensitive_fields_are_rejected(tmp_path):
    p = _write(
        tmp_path,
        {
            "schema": "hoopvision.public-consumer-heartbeat.v1",
            "consumer_contract": "public_outbox_private_pull.v1",
            "status": "READY",
            "observed_at_utc": "2026-10-04T23:59:00Z",
            "project_id": "must-never-be-public",
        },
    )
    got = check(p, now=NOW)
    assert got["ready"] is False
    assert got["status"] == "BLOCKED_HEARTBEAT_PRIVACY_VIOLATION"
