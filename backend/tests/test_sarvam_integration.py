"""
Unit and Integration Tests for Sarvam AI Multimodal Pipeline (Code for a Billion / Bharat Agentic-AI)
Tests Sarvam Saaras v4 STT, Bulbul v3 TTS, and Sarvam-105B chat endpoints and agent integration.
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

class TestSarvamVoiceIntegration(unittest.TestCase):
    def setUp(self):
        self.assistant = AIAssistant()
        self.assistant.api_key = "test_sarvam_key_12345"
        self.assistant.client = MagicMock()

    def test_sarvam_saaras_stt_success(self):
        mock_response = MagicMock()
        mock_response.transcript = "தக்காளி இலையில் கரும்புள்ளி நோய் உள்ளது"
        mock_response.language_code = "ta-IN"
        self.assistant.client.speech_to_text.transcribe.return_value = mock_response

        fake_audio = b"RIFF....WAVEfmt ...."
        detected_lang, transcript = self.assistant.speech_to_text(fake_audio, filename="voice.wav")

        self.assertEqual(detected_lang, "ta-IN")
        self.assertEqual(transcript, "தக்காளி இலையில் கரும்புள்ளி நோய் உள்ளது")
        self.assertTrue(self.assistant.client.speech_to_text.transcribe.called)
        _, kwargs = self.assistant.client.speech_to_text.transcribe.call_args
        self.assertEqual(kwargs.get("model"), "saaras:v4")
        self.assertEqual(kwargs.get("mode"), "codemix")

    def test_sarvam_bulbul_tts_success(self):
        fake_b64 = "UklGRi4AAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
        mock_response = MagicMock()
        mock_response.audios = [fake_b64]
        self.assistant.client.text_to_speech.convert.return_value = mock_response

        audio_b64 = self.assistant.text_to_speech("இலைகளை உடனே அகற்றவும்.", language_code="ta-IN")

        self.assertIsNotNone(audio_b64)
        self.assertEqual(audio_b64, fake_b64)
        self.assertTrue(self.assistant.client.text_to_speech.convert.called)
        _, kwargs = self.assistant.client.text_to_speech.convert.call_args
        self.assertEqual(kwargs.get("model"), "bulbul:v3")
        self.assertEqual(kwargs.get("language_code"), "ta-IN")

    def test_sarvam_105b_chat_success(self):
        mock_choice = MagicMock()
        mock_choice.message.content = "இலைகளில் உள்ள பாதிக்கப்பட்ட பகுதிகளை கத்தரித்து அப்புறப்படுத்துங்கள்."
        mock_res = MagicMock()
        mock_res.choices = [mock_choice]
        self.assistant.client.chat.completions.return_value = mock_res

        reply = self.assistant.answer("தக்காளி இலை கருகுகிறது என்ன செய்வது?", language="ta")
        self.assertIn("பாதிக்கப்பட்ட", reply)
        self.assertTrue(self.assistant.client.chat.completions.called)
        _, kwargs = self.assistant.client.chat.completions.call_args
        self.assertEqual(kwargs.get("model"), "sarvam-105b-conversations")

    def test_agent_workflow_uses_sarvam_voice(self):
        mock_stt_resp = MagicMock()
        mock_stt_resp.transcript = "இன்று மழை பெய்யுமா?"
        mock_stt_resp.language_code = "ta-IN"
        self.assistant.client.speech_to_text.transcribe.return_value = mock_stt_resp

        mock_tts_resp = MagicMock()
        mock_tts_resp.audios = ["FAKE_SARVAM_AUDIO_B64"]
        self.assistant.client.text_to_speech.convert.return_value = mock_tts_resp

        mock_choice = MagicMock()
        mock_choice.message.content = "இன்று 20% மழை வாய்ப்பு மட்டுமே உள்ளது. உழவு பணிகளை தொடரலாம்."
        mock_chat_res = MagicMock()
        mock_chat_res.choices = [mock_choice]
        self.assistant.client.chat.completions.return_value = mock_chat_res

        agent = AgroNexAgent(assistant=self.assistant)
        result = agent.run(
            audio_bytes=b"sample_audio",
            latitude=11.0168,
            longitude=76.9558,
            language="ta"
        )

        self.assertTrue(result["success"])
        self.assertIn("sarvam_speech_to_text", result["tools_called"])
        self.assertIn("sarvam_bulbul_tts", result["tools_called"])
        self.assertNotIn("gnani_prisma_speech_to_text", result["tools_called"])
        self.assertNotIn("gnani_timbre_tts", result["tools_called"])

if __name__ == "__main__":
    unittest.main()
