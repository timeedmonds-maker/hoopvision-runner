"""Authenticated opaque request transport; no private metadata in public records."""
import json
import os
import secrets
import urllib.parse
import urllib.request
from .opaque_lane_contract import valid_request_id

AUDIENCE = "hoopvision-licensed-feed.v1"

def fresh_id():
    return "req-" + secrets.token_hex(16)

def identity_token():
    source = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    url = source + "&" + urllib.parse.urlencode({"audience": AUDIENCE})
    req = urllib.request.Request(url, headers={"Authorization": "bearer " + token})
    with urllib.request.urlopen(req, timeout=15) as result:
        jwt = json.load(result).get("value")
    if not isinstance(jwt, str) or jwt.count(".") != 2:
        raise ValueError("identity_unavailable")
    return jwt

def endpoint():
    raw = os.environ["LICENSED_FEED_PRIVATE_GATEWAY"]
    url = urllib.parse.urlsplit(raw)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("invalid_private_gateway")
    return raw.rstrip("/")

def authorized_request(route, request_id, payload):
    if not valid_request_id(request_id):
        raise ValueError("bad_request_id")
    if route not in ("claim", "upload"):
        raise ValueError("bad_route")
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(endpoint() + "/v1/" + route, data=body, method="POST",
        headers={"Authorization": "Bearer " + identity_token(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as result:
        return json.load(result)
