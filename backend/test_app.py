"""Small API smoke tests that run without pytest or model downloads."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
import app as app_module  # noqa: E402


class SwasthyaApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        app_module.DATA_DIR = self.temp_dir.name
        app_module.DB_PATH = os.path.join(self.temp_dir.name, "test.db")
        app_module.init_db()
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_history_rejects_invalid_limit(self):
        response = self.client.get("/api/history?limit=not-a-number")
        self.assertEqual(response.status_code, 400)

    def test_history_export_returns_csv(self):
        response = self.client.get("/api/history/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.content_type)
        self.assertIn("created_at,sentiment,mood", response.get_data(as_text=True))


    @patch.object(
        app_module.analyzer,
        "analyze",
        return_value={
            "sentiment": "positive",
            "mood": 80,
            "confidence": 0.9,
            "engine": "test",
        },
    )
    def test_analysis_persists_and_clear_history_removes_entries(self, _mock_analyze):
        response = self.client.post("/api/analyze", json={"text": "I feel good today"})
        self.assertEqual(response.status_code, 200)

        history = self.client.get("/api/history")
        self.assertEqual(len(history.get_json()), 1)
        entry_id = history.get_json()[0]["id"]

        deleted = self.client.delete(f"/api/history/{entry_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.get_json()["deleted"], entry_id)
        self.assertEqual(self.client.get("/api/history").get_json(), [])

        missing = self.client.delete(f"/api/history/{entry_id}")
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
