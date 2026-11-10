"""
Unit and Integration Tests for Gnani AI Voice Pipeline (Great Indian AI Challenge)
Tests Gnani Prisma v3.0 STT and Gnani Timbre v3.0 TTS endpoints and agent integration.
"""

import unittest
from unittest.mock import patch, MagicMock
import base64
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.ai.ai_assistant import AIAssistant
from services.agent.agronex_agent import AgroNexAgent

class TestGnaniVoiceIntegration(unittest.TestCase):
    def setUp(self):
        self.assistant = AIAssistant()
        self.assistant.gnani_api_key = "test_gnani_key_12345"

    @patch("services.ai.ai_assistant.requests.post")
    def test_gnani_prisma_stt_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "transcript": "தக்காளி இலையில் கரும்புள்ளி நோய் உள்ளது",
            "detected_language_code": "ta-IN",
            "model": "prisma-v3.0"
        }
        mock_post.return_value = mock_response

        fake_audio = b"RIFF....WAVEfmt ...."
        detected_lang, transcript = self.assistant.speech_to_text(fake_audio, filename="voice.wav")

        self.assertEqual(detected_lang, "ta-IN")
        self.assertEqual(transcript, "தக்காளி இலையில் கரும்புள்ளி நோய் உள்ளது")
        self.assertTrue(mock_post.called)
        call_args, call_kwargs = mock_post.call_args
        self.assertEqual(call_args[0], "https://api.vachana.ai/stt/v3")
        self.assertEqual(call_kwargs["headers"]["X-API-Key-ID"], "test_gnani_key_12345")

    @patch("services.ai.ai_assistant.requests.post")
    def test_gnani_timbre_tts_success(self, mock_post):
        fake_wav = b"RIFF_FAKE_WAV_BYTES_FOR_TTS"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_wav
        mock_post.return_value = mock_response

        audio_b64 = self.assistant.text_to_speech("இலைகளை உடனே அகற்றவும்.", language_code="ta-IN")

        self.assertIsNotNone(audio_b64)
        decoded = base64.b64decode(audio_b64)
        self.assertEqual(decoded, fake_wav)
        self.assertTrue(mock_post.called)
        call_args, call_kwargs = mock_post.call_args
        self.assertEqual(call_args[0], "https://api.vachana.ai/api/v1/tts/inference")
        self.assertEqual(call_kwargs["headers"]["X-API-Key-ID"], "test_gnani_key_12345")
        self.assertEqual(call_kwargs["json"]["model"], "timbre-v3.0")

    @patch("services.ai.ai_assistant.requests.post")
    def test_agent_workflow_uses_gnani_voice(self, mock_post):
        mock_stt_resp = MagicMock()
        mock_stt_resp.status_code = 200
        mock_stt_resp.json.return_value = {
            "success": True,
            "transcript": "இன்று மழை பெய்யுமா?",
            "detected_language_code": "ta-IN"
        }

        mock_tts_resp = MagicMock()
        mock_tts_resp.status_code = 200
        mock_tts_resp.content = b"WAV_AUDIO"

        def side_effect(url, **kwargs):
            if "stt" in url:
                return mock_stt_resp
            return mock_tts_resp

        mock_post.side_effect = side_effect

        agent = AgroNexAgent(assistant=self.assistant)
        result = agent.run(
            audio_bytes=b"sample_audio",
            latitude=11.0168,
            longitude=76.9558,
            language="ta"
        )

        self.assertTrue(result["success"])
        self.assertIn("gnani_prisma_speech_to_text", result["tools_called"])
        self.assertIn("gnani_timbre_tts", result["tools_called"])

if __name__ == "__main__":
    unittest.main()

