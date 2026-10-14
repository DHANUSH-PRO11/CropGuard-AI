"""
AgroNex Agent Workflow Automated Test Suite
Validates the end-to-end AgentFoundry workflow, multimodal routing,
weather-risk integration, uncertainty gatekeeping, and bilingual reasoning.
"""

import sys
import unittest
import numpy as np
from PIL import Image
import io
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.agent.agronex_agent import AgroNexAgent
from services.ai.disease_detector import DiseaseDetector
from services.weather_service import WeatherService
from config.database import get_supabase

def create_mock_leaf_image(width=224, height=224, is_green=True) -> bytes:
    """Creates in-memory JPEG bytes of a synthetic leaf for testing."""
    color = (40, 160, 50) if is_green else (180, 180, 180)
    arr = np.full((height, width, 3), color, dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

class TestAgroNexAgentWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = AgroNexAgent()

    def test_01_text_query_with_weather_routing(self):
        """Validates that a weather/spray question triggers meteorological routing and returns spray advisory."""
        result = self.agent.run(
            query="Can I spray protective fungicide on my crops today?",
            latitude=11.0168,
            longitude=76.9558,
            language="en"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "completed")
        self.assertIn("open_meteo_weather_service", result["tools_called"])
        self.assertIn("sarvam_agricultural_reasoner", result["tools_called"])
        self.assertIsNotNone(result["spray_advisory"])
        self.assertGreater(len(result["recommendation"]), 20)
        self.assertGreater(len(result["execution_trace"]), 4)

    def test_02_tamil_language_synthesis(self):
        """Validates that Tamil queries produce grounded Tamil guidance and TTS audio."""
        result = self.agent.run(
            query="இன்று மழை வருமா, உரம் இடலாமா?",
            latitude=11.0168,
            longitude=76.9558,
            language="ta"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["language"], "ta")
        self.assertIsNotNone(result["recommendation"])
        # Should have generated audio or fallen back cleanly
        self.assertIn("voice_synthesis", [node["node"] for node in result["execution_trace"]])

    def test_03_multimodal_image_diagnosis(self):
        """Validates that supplying a leaf image triggers EfficientNetV2 and uncertainty gatekeeping."""
        image_bytes = create_mock_leaf_image(224, 224, is_green=True)
        result = self.agent.run(
            query="Please identify this condition",
            image_bytes=image_bytes,
            image_filename="synthetic_test_leaf.jpg",
            latitude=11.0168,
            longitude=76.9558,
            language="en"
        )
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["crop_prediction"])
        self.assertIn("crop", result["crop_prediction"])
        self.assertIn("condition", result["crop_prediction"])
        self.assertIn("confidence", result["crop_prediction"])
        self.assertIn("efficientnet_v2_disease_detector", result["tools_called"])
        self.assertIn("requires_expert_confirmation", result)

    def test_04_uncertainty_gatekeeper(self):
        """Validates that low-confidence results trigger requires_expert_confirmation."""
        # Non-leaf grey image
        image_bytes = create_mock_leaf_image(224, 224, is_green=False)
        result = self.agent.run(
            image_bytes=image_bytes,
            image_filename="non_leaf.jpg",
            language="en"
        )
        self.assertTrue(result["success"])
        # Quality check should detect low foliage or low confidence
        pred = result["crop_prediction"]
        self.assertIsNotNone(pred)
        self.assertTrue(
            result["requires_expert_confirmation"] or pred["status"] == "Uncertain" or pred["quality_status"] != "Passed"
        )

    def test_05_offline_supabase_resilience(self):
        """Validates that missing Supabase credentials does not crash the workflow."""
        result = self.agent.run(
            query="General farm inquiry",
            db_client=None, # explicitly test with offline/None database
            language="en"
        )
        self.assertTrue(result["success"])
        persistence_node = next(n for n in result["execution_trace"] if n["node"] == "persistence")
        self.assertIn(persistence_node["status"], ["completed", "offline_fallback"])

    def test_06_spray_window_logic(self):
        """Validates that the spray advisory evaluates meteorological safety."""
        result = self.agent.run(
            query="Check spray window",
            latitude=11.0168,
            longitude=76.9558,
            language="en"
        )
        self.assertTrue(result["success"])
        self.assertIn(result["spray_advisory"], [
            "DO NOT SPRAY: High chance of rainfall (>60%). Chemical wash-off hazard.",
            "CAUTION SPRAYING: High winds (>25 km/h). Severe spray drift hazard.",
            "SAFE SPRAY WINDOW: Low wind and minimal rain probability in immediate 24h.",
            "Favorable for field operations."
        ])

if __name__ == "__main__":
    unittest.main()
