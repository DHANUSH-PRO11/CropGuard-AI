"""
Comprehensive API Endpoint and Authentication Test Suite for AgroNex
Tests auth, registration, JWT login, profile updates, schemes, weather, and crops history.
"""

import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app

class TestAgroNexAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_and_root(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("message", res_root.json())

    def test_02_auth_registration_and_validation(self):
        # Short password error
        short_res = self.client.post("/api/auth/register", json={
            "name": "Test User",
            "mobile": "9999900001",
            "password": "123"
        })
        self.assertEqual(short_res.status_code, 400)

        # Successful registration with globally unique mobile
        import uuid
        unique_mobile = f"99{uuid.uuid4().int % 100000000:08d}"
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Murugan",
            "mobile": unique_mobile,
            "email": f"farmer_{unique_mobile}@agronex.com",
            "password": "strongPassword123",
            "location": "Thanjavur, Tamil Nadu",
            "preferred_language": "ta"
        })
        self.assertEqual(reg_res.status_code, 200)
        user = reg_res.json()
        self.assertEqual(user["name"], "Murugan")
        self.assertEqual(user["mobile"], unique_mobile)

        # Duplicate registration error
        dup_res = self.client.post("/api/auth/register", json={
            "name": "Duplicate Murugan",
            "mobile": unique_mobile,
            "password": "strongPassword123"
        })
        self.assertEqual(dup_res.status_code, 400)

    def test_03_auth_login_flow(self):
        # Create a user to log in
        import uuid
        unique_mobile = f"91{uuid.uuid4().int % 100000000:08d}"
        self.client.post("/api/auth/register", json={
            "name": "Kavitha",
            "mobile": unique_mobile,
            "password": "farmerSecret999",
            "location": "Madurai"
        })

        # Invalid password
        bad_login = self.client.post("/api/auth/login", json={
            "username": unique_mobile,
            "password": "wrongPassword"
        })
        self.assertEqual(bad_login.status_code, 401)

        # Successful login
        good_login = self.client.post("/api/auth/login", json={
            "username": unique_mobile,
            "password": "farmerSecret999"
        })
        self.assertEqual(good_login.status_code, 200)
        body = good_login.json()
        self.assertIn("access_token", body)
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(body["user"]["mobile"], unique_mobile)

        # Test /api/auth/me with Bearer token
        token = body["access_token"]
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["mobile"], unique_mobile)

    def test_04_farmer_profile_get_and_update(self):
        # GET profile
        res = self.client.get("/api/profile/")
        self.assertEqual(res.status_code, 200)
        prof = res.json()
        self.assertIn("name", prof)
        self.assertIn("location", prof)

        # PUT profile update
        update_res = self.client.put("/api/profile/", json={
            "name": "Selvam",
            "farm_size": 4.5,
            "primary_crop": "Cotton, Groundnut",
            "location": "Salem, Tamil Nadu"
        })
        self.assertEqual(update_res.status_code, 200)
        updated = update_res.json()
        self.assertEqual(updated["name"], "Selvam")
        self.assertEqual(updated["farm_size"], 4.5)
        self.assertEqual(updated["primary_crop"], "Cotton, Groundnut")

    def test_05_schemes_endpoint(self):
        res = self.client.get("/api/schemes/")
        self.assertEqual(res.status_code, 200)
        schemes = res.json()
        self.assertGreaterEqual(len(schemes), 4)

        # Search filter
        search_res = self.client.get("/api/schemes/?search=kisan")
        self.assertEqual(search_res.status_code, 200)
        self.assertTrue(any("kisan" in s["name"].lower() for s in search_res.json()))

    def test_06_weather_forecast_endpoint(self):
        res = self.client.get("/api/weather/forecast?lat=11.0168&lon=76.9558")
        self.assertEqual(res.status_code, 200)
        w = res.json()
        self.assertTrue(w["success"])
        self.assertIn("current", w)
        self.assertIn("temperature", w["current"])
        self.assertIn("forecast", w)

    def test_07_crop_history_endpoint(self):
        res = self.client.get("/api/crops/history")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_08_agent_workflow_manifest(self):
        res = self.client.get("/api/agent/workflow")
        self.assertEqual(res.status_code, 200)
        manifest = res.json()
        self.assertEqual(manifest["workflow_id"], "agronex-farming-copilot")
        self.assertIn("nodes", manifest)

    def test_09_agent_chat_endpoint(self):
        res = self.client.post("/api/agent/chat", json={
            "message": "What is the best fertilizer schedule for paddy crops?",
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        chat_res = res.json()
        self.assertTrue(chat_res["success"])
        self.assertIn("recommendation", chat_res)

if __name__ == "__main__":
    unittest.main()
