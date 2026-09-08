"""
Unit tests for FastAPI serverless web application (api/index.py).
Validates dashboard rendering, diagnostic endpoints, and online calculation engine.
"""

import io
import unittest
import pandas as pd
from fastapi.testclient import TestClient

from api.index import app


class TestServerlessAPI(unittest.TestCase):
    """Test suite for Vercel serverless API and web endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_dashboard_endpoint(self):
        """Tests that GET / serves the HTML dashboard successfully."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Shopee Agency Pro", response.text)
        self.assertIn("<!DOCTYPE html>", response.text)

    def test_health_endpoint(self):
        """Tests health check monitoring endpoint."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "online")
        self.assertEqual(data.get("platform"), "Vercel Serverless")

    def test_debug_endpoint(self):
        """Tests diagnostic endpoint for serverless environment inspection."""
        response = self.client.get("/api/debug")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("python_version", data)
        self.assertIn("temp_dir", data)

    def test_calculate_no_files_validation(self):
        """Tests that calculation without files returns 400 Bad Request."""
        response = self.client.post("/api/calculate")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)

    def test_calculate_with_sample_data(self):
        """Tests end-to-end calculation via API using in-memory Excel and CSV files."""
        drop_df = pd.DataFrame({
            "Tracking Number": ["SPXBR001", "SPXBR002"],
            "DOP Received Time": ["01/09/2026 09:00:00", "01/09/2026 10:00:00"],
            "DOP Outbound Time": ["01/09/2026 11:00:00", "01/09/2026 13:00:00"],
            "Tag": ["-", "Return/Refund"],
        })
        drop_buffer = io.BytesIO()
        drop_df.to_excel(drop_buffer, index=False)
        drop_buffer.seek(0)

        coll_df = pd.DataFrame({
            "Tracking Number": ["SPXBRCOL01", "SPXBRCOL02"],
            "Status": ["Collected", "Ready_For_Collection"],
        })
        coll_buffer = io.BytesIO()
        coll_df.to_csv(coll_buffer, index=False)
        coll_buffer.seek(0)

        files = {
            "dropoff_file": ("dropoff.xlsx", drop_buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "collection_file": ("collection.csv", coll_buffer, "text/csv"),
        }

        response = self.client.post("/api/calculate", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data.get("status"), "success")
        rev = data.get("revenue")
        self.assertIsNotNone(rev)
        self.assertEqual(rev.get("total_packages_moved"), 4)
        self.assertEqual(rev.get("return_count"), 1)
        self.assertEqual(rev.get("collection_count"), 2)

        lead = data.get("lead_time")
        self.assertIsNotNone(lead)
        self.assertEqual(lead.get("total_packages"), 2)
        self.assertEqual(lead.get("dispatched_packages"), 2)


if __name__ == "__main__":
    unittest.main()
