from tools.wait_for_consumer_receipt import classify


def test_matching_consumed_receipt_succeeds():
    assert classify({
        "schema":"hoopvision.public-consumer-receipt.v1",
        "request_id":"req-abc12345",
        "status":"CONSUMED",
    },"req-abc12345")=="SUCCESS"


def test_other_request_is_ignored():
    assert classify({
        "schema":"hoopvision.public-consumer-receipt.v1",
        "request_id":"req-other",
        "status":"CONSUMED",
    },"req-abc12345")=="WAIT"


def test_rejected_unregistered_is_failure():
    assert classify({
        "schema":"hoopvision.public-consumer-receipt.v1",
        "request_id":"req-abc12345",
        "status":"REJECTED_UNREGISTERED",
    },"req-abc12345")=="FAILURE"


def test_unknown_status_is_not_treated_as_success():
    assert classify({
        "schema":"hoopvision.public-consumer-receipt.v1",
        "request_id":"req-abc12345",
        "status":"RESOLVER_FINISHED",
    },"req-abc12345")=="WAIT"
