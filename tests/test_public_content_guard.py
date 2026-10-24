from tools.public_content_guard import scan

def test_clean_bridge_files_only():
    assert scan(["README.md", "runner_policy.json", "tools/public_content_guard.py"]) == []

def test_experiment_paths_fail():
    got = scan(["experiments/example.json"])
    assert ("FORBIDDEN_PATH_CLASS", "experiments/example.json") in got

def test_unknown_file_fails():
    got = scan(["notes/internal.txt"])
    assert ("NOT_ALLOWLISTED", "notes/internal.txt") in got

def test_reviewed_artifact_handoffs_are_pinned_and_guard_clean():
    from tools.public_content_guard import (
        REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA,
        REVIEWED_HANDOFF_CERT_GIT_BLOB_SHA,
    )
    from pathlib import Path
    import subprocess

    for rel, expected in {
        **REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA,
        **REVIEWED_HANDOFF_CERT_GIT_BLOB_SHA,
    }.items():
        assert Path(rel).is_file()
        assert subprocess.check_output(["git", "hash-object", rel], text=True).strip() == expected
    assert scan([
        *REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA,
        *REVIEWED_HANDOFF_CERT_GIT_BLOB_SHA,
    ]) == []
