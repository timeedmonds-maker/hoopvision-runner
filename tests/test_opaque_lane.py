import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from opaque_lane_contract import valid_request_id
from opaque_lane_client import fresh_id, endpoint
from unittest.mock import patch

class TestOpaqueLane(unittest.TestCase):
    def test_random_opaque_ids_only(self):
        value=fresh_id()
        self.assertTrue(valid_request_id(value))
        self.assertFalse(valid_request_id("game-0022600001"))
        self.assertFalse(valid_request_id("req-123"))
        self.assertFalse(valid_request_id("req-"+"x"*32))
    def test_gateway_must_be_https_without_injected_uri_fields(self):
        with patch.dict("os.environ",{"LICENSED_FEED_PRIVATE_GATEWAY":"https://api.example.test"}):
            self.assertEqual(endpoint(),"https://api.example.test")
        for url in ["http://api.example.test","https://user:pw@api.example.test",
                    "https://api.example.test/?secret=x","file:///tmp/file"]:
            with patch.dict("os.environ",{"LICENSED_FEED_PRIVATE_GATEWAY":url}):
                with self.assertRaises(ValueError): endpoint()
    def test_public_workflow_never_uploads_artifacts(self):
        root=pathlib.Path(__file__).resolve().parents[1]
        wf=root/".github/workflows/opaque-licensed-feed.yml"
        if wf.exists():
            body=wf.read_text()
            self.assertNotIn("upload-artifact",body)
            self.assertNotIn("actions/cache",body)
            self.assertNotIn("repository: ",body)
            self.assertIn("id-token: write",body)
            self.assertIn("contents: read",body)
    def test_existing_opaque_bridge_unchanged(self):
        root=pathlib.Path(__file__).resolve().parents[1]
        policy=(root/"runner_policy.json").read_text()
        self.assertIn('"opaque_request_only": true',policy)
        self.assertIn('"private_data_allowed": false',policy)

if __name__=="__main__":unittest.main()
