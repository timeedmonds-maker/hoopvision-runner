from tools.public_content_guard import scan

def test_clean_bridge_files_only():
    assert scan(["README.md", "runner_policy.json", "tools/public_content_guard.py"]) == []

def test_experiment_paths_fail():
    got = scan(["experiments/example.json"])
    assert ("FORBIDDEN_PATH_CLASS", "experiments/example.json") in got

def test_unknown_file_fails():
    got = scan(["notes/internal.txt"])
    assert ("NOT_ALLOWLISTED", "notes/internal.txt") in got
