import unittest

from tools.durable_result import (
    classification,
    execution_status,
    final_video,
    qualification_status,
    validate_final_video,
)


class DurableResultTests(unittest.TestCase):
    def test_current_completed_nested_payload(self):
        p = {
            "benchmark": {
                "ok": True,
                "qualification": {
                    "terminal_status": "COMPLETED",
                    "qualification_status": "UNKNOWN",
                },
                "result": {
                    "final_video": "gs://bucket/runs/run-1/final/video.mp4",
                    "single_run_foundation_gate": {"status": "UNKNOWN"},
                },
            }
        }
        self.assertEqual(execution_status(p), "COMPLETED")
        self.assertEqual(qualification_status(p), "UNKNOWN")
        self.assertEqual(classification(p), "COMPLETED_AWAIT_ACCEPTANCE_EVIDENCE")
        self.assertEqual(final_video(p), "gs://bucket/runs/run-1/final/video.mp4")

    def test_legacy_success_and_top_level_video(self):
        p = {"status": "SUCCESS", "final_video": "gs://bucket/runs/old/video.mp4"}
        self.assertEqual(execution_status(p), "COMPLETED")
        self.assertEqual(final_video(p), "gs://bucket/runs/old/video.mp4")

    def test_failed_timeout(self):
        p = {"status": "FAILED", "error": "TimeoutError: stage exceeded limit"}
        self.assertEqual(execution_status(p), "FAILED")
        self.assertEqual(classification(p), "APPLICATION_TIMEOUT_NO_AUTORETRY")

    def test_completed_does_not_become_qualified(self):
        p = {"benchmark": {"ok": True, "qualification": {"terminal_status": "COMPLETED"}}}
        self.assertEqual(execution_status(p), "COMPLETED")
        self.assertEqual(qualification_status(p), "UNKNOWN")

    def test_authorised_bucket_validation(self):
        uri = "gs://bucket/runs/run-1/final/video.mp4"
        self.assertEqual(validate_final_video(uri, "bucket"), uri)
        with self.assertRaises(ValueError):
            validate_final_video("gs://other/runs/run-1/final/video.mp4", "bucket")
        with self.assertRaises(ValueError):
            validate_final_video("gs://bucket/../other/video.mp4", "bucket")


if __name__ == "__main__":
    unittest.main()
