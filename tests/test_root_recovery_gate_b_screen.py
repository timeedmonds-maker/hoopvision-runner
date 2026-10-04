from tools.root_recovery_gate_b_screen import classify


def _event(**overrides):
    row={
        "event_id":"e1",
        "actor_player_id":1,
        "accepted_anchor":True,
        "rank1":{"path_id":"A:1","unresolved_rows":50},
        "event_time_owner_ids":[],
        "simultaneous_same_player_other_paths":[],
    }
    row.update(overrides)
    return row


def test_accepted_body_association_without_direct_root_evidence_fails_closed():
    got=classify(_event())
    assert got["screening_status"]=="DIRECT_ROOT_ELIGIBILITY_NOT_RETAINED"
    assert got["safe_new_root_candidate"] is False
    assert got["unique_unknown_rows_recoverable_if_independently_certified"]==0


def test_accepted_non_authorizing_event_is_not_counted_as_root_headroom():
    got=classify(_event(identity_authorizing=False))
    assert got["screening_status"]=="EVENT_ASSOCIATION_NOT_DIRECT_ROOT"
    assert got["safe_new_root_candidate"] is False
    assert got["source_direct_root_eligible"] is False


def test_direct_root_eligible_event_can_reach_shadow_candidate_gate():
    got=classify(_event(identity_authorizing=True))
    assert got["screening_status"]=="SAFE_NEW_ROOT_CANDIDATE_SHADOW_ONLY"
    assert got["safe_new_root_candidate"] is True
    assert got["unique_unknown_rows_recoverable_if_independently_certified"]==50
    assert got["identity_authorizing"] is False
