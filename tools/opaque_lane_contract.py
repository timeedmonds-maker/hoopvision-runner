# Opaque lane preflight: request identifiers remain the only public metadata.
import re

OPAQUE_ID = re.compile(r'^req-[0-9a-f]{32}$')

def valid_request_id(value):
    return isinstance(value, str) and OPAQUE_ID.fullmatch(value) is not None
