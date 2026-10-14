import io
import logging
import os
import re
from pathlib import Path
from dotenv import load_dotenv
try:
    from sarvamai import SarvamAI
except ImportError:
    SarvamAI = None

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are AgroNex, an AI agricultural copilot for smallholder and commercial farmers.

CORE PRINCIPLES & SAFETY RULES:
1. Grounded Agricultural Reasoning: Base your advice strictly on provided factual observations (crop disease model output, quality checks, and real-time weather metrics). Never fabricate weather data or invented disease conditions.
2. Model Prediction vs. Diagnosis: Always distinguish an AI visual observation from a certified agronomist diagnosis. If confidence is uncertain (<60%) or image quality is degraded, explicitly advise the farmer to verify with a local Krishi Vigyan Kendra (KVK) or agricultural extension officer before expensive interventions.
3. Weather-Integrated Spray Window:
   - If rain (>60% probability or >5mm) is forecasted within the next 24-48 hours, warn against spraying chemical pesticides/fungicides because rain will wash them off into runoff and waste money.
   - If high wind (>25 km/h) is present, warn of spray drift hazard.
4. Responsible Plant Protection: Prioritize cultural and bio-control methods (proper spacing, removing infected debris, neem oil, Trichoderma viride) before recommending chemical options. Never fabricate chemical dosages or unverified proprietary brand mixtures.
5. Communication Style: Conversational, empathetic, and direct (3-5 concise sentences). Provide clear, actionable bullet points for immediate farmer steps.
6. Language: Respond in the farmer's preferred language (Tamil, English, or natural Tamil-English code-mix commonly used by Tamil Nadu farmers)."""

class AIAssistant:
    def __init__(self):
        # Load SARVAM_API_KEY from backend/.env or root .env
        base_dir = Path(__file__).resolve().parents[2]
        load_dotenv(dotenv_path=base_dir / ".env")
        load_dotenv(dotenv_path=base_dir / "backend" / ".env")

        self.api_key = os.environ.get("SARVAM_API_KEY")
        if not self.api_key:
            for candidate in [base_dir / ".env", base_dir / "backend" / ".env"]:
                if candidate.exists():
                    for line in candidate.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line.startswith("SARVAM_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                self.api_key = val
                                break
                if self.api_key:
                    break

        if self.api_key and SarvamAI is not None:
            self.client = SarvamAI(api_subscription_key=self.api_key)
        else:
            self.client = None
            if not SarvamAI:
                logger.warning("sarvamai package is not installed; AI assistant features will operate in fallback mode.")


    def clean_for_tts(self, text: str) -> str:
        """Strip markdown symbols (asterisks, hashtags, bullets) so TTS reads smoothly."""
        clean = re.sub(r'[*_~`#]', '', text)
        clean = re.sub(r'^\s*[-+*]\s+', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'\n+', ' ', clean).strip()
        return clean

    def _format_context_block(self, context: dict) -> str:
        """Serializes crop diagnosis and real-time weather into an authoritative grounding block."""
        if not context:
            return ""

        parts = ["\n--- AUTHORITATIVE GROUNDING DATA (REAL-TIME SENSORS & MODELS) ---"]
        if "crop" in context or "condition" in context:
            crop_name = context.get("crop", "Unknown Crop")
            cond = context.get("condition", "Healthy")
            conf = context.get("confidence", 0.0)
            status = context.get("status", "Evaluated")
            quality = context.get("quality_status", "Passed")
            parts.append(f"- Crop: {crop_name}")
            parts.append(f"- Visual Model Observation: {cond} ({conf:.1f}% confidence, Status: {status})")
            parts.append(f"- Leaf Image Quality Gate: {quality}")
            if context.get("warning_message"):
                parts.append(f"- Image Warning: {context.get('warning_message')}")

        if "weather" in context and isinstance(context["weather"], dict):
            w = context["weather"]
            curr = w.get("current", {})
            parts.append(f"- Local Weather: Temp {curr.get('temperature', 'N/A')}°C, Humidity {curr.get('humidity', 'N/A')}%, Wind {curr.get('wind_speed', 'N/A')} km/h, Rain {curr.get('precipitation', 0)} mm")
            if w.get("alerts"):
                alerts_str = "; ".join([a.get("message_en", a.get("alert_type", "")) for a in w["alerts"]])
                parts.append(f"- Active Agricultural Weather Alerts: {alerts_str}")

        if "spray_advisory" in context:
            parts.append(f"- Spray Window Feasibility: {context['spray_advisory']}")

        if "schemes" in context and isinstance(context["schemes"], list):
            sch_items = []
            for s in context["schemes"][:3]:
                sch_items.append(f"{s.get('name')}: {s.get('benefits')}")
            parts.append(f"- Matched Government Schemes: {'; '.join(sch_items)}")

        parts.append("----------------------------------------------------------------\n")
        return "\n".join(parts)

    def _generate_fallback_response(self, question: str, language: str, context: dict = None) -> str:
        """Deterministic, grounded agricultural response if Sarvam AI is offline or key missing."""
        is_tamil = language == "ta"
        crop = context.get("crop", "பயிர்" if is_tamil else "crop") if context else ("பயிர்" if is_tamil else "crop")
        cond = context.get("condition", "ஆரோக்கியமானது" if is_tamil else "Healthy") if context else ""
        weather = context.get("weather", {}) if context else {}
        alerts = weather.get("alerts", []) if isinstance(weather, dict) else []
        schemes = context.get("schemes", []) if context and isinstance(context.get("schemes"), list) else []

        if schemes:
            sch = schemes[0]
            if is_tamil:
                return (
                    f"அரசு விவசாய திட்டம் வழிகாட்டல்:\n"
                    f"• திட்டம்: {sch.get('name_ta', sch.get('name'))}\n"
                    f"• பயன்கள்: {sch.get('benefits_ta', sch.get('benefits'))}\n"
                    f"• தகுதி: {sch.get('eligibility_ta', sch.get('eligibility'))}\n"
                    f"• கூடுதல் விவரம் & விண்ணப்பிக்க: {sch.get('source')}"
                )
            else:
                return (
                    f"Government Agricultural Scheme Guidance:\n"
                    f"• Scheme: {sch.get('name')}\n"
                    f"• Benefits: {sch.get('benefits')}\n"
                    f"• Eligibility: {sch.get('eligibility')}\n"
                    f"• Official Portal: {sch.get('source')}"
                )

        if is_tamil:
            lines = [f"அக்ரோநெக்ஸ் விவசாய வழிகாட்டல்:"]
            if cond:
                clean_cond = cond.replace('_', ' ')
                lines.append(f"• கண்டறியப்பட்ட நிலை: {crop} - {clean_cond}.")
            if alerts:
                lines.append(f"• வானிலை எச்சரிக்கை: {alerts[0].get('message_ta', 'மழை வாய்ப்பு உள்ளது, பூச்சிக்கொல்லி தெளிப்பதை தவிர்க்கவும்.')}")
            lines.append("• பரிந்துரை: பாதிக்கப்பட்ட இலைகளை உடனே அகற்றவும். இயற்கை வேப்ப எண்ணெய் (3%) தெளிக்கவும்.")
            lines.append("• துல்லியமான உறுதிப்படுத்தலுக்கு அருகிலுள்ள வேளாண்மை உதவி அலுவலரை (KVK) அணுகவும்.")
            return "\n".join(lines)
        else:
            lines = [f"AgroNex Agricultural Copilot Guidance:"]
            if cond:
                clean_cond = cond.replace('_', ' ')
                lines.append(f"• Model Observation: {crop} ({clean_cond}).")
            if alerts:
                lines.append(f"• Weather Advisory: {alerts[0].get('message_en', 'Rain or high humidity expected. Postpone chemical sprays.')}")
            lines.append("• Immediate Action: Prune affected leaves, ensure proper field drainage, and consider bio-controls like Neem-based spray.")
            lines.append("• For uncertain or severe symptoms, please verify with your local agricultural extension officer (KVK).")
            return "\n".join(lines)

    def answer(self, question: str, language: str = "en", context: dict = None) -> str:
        if not self.client:
            return self._generate_fallback_response(question, language, context)

        try:
            prompt_modifier = ""
            if language == "ta":
                prompt_modifier = "\nPlease answer primarily in Tamil or natural Tamil-English code-mix as used by Tamil Nadu farmers."
            elif language == "en":
                prompt_modifier = "\nPlease answer in simple, direct English."

            grounding_text = self._format_context_block(context) if context else ""

            user_content = f"{grounding_text}Farmer Question: {question}" if grounding_text else question

            response = self.client.chat.completions(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + prompt_modifier},
                    {"role": "user", "content": user_content},
                ],
                model="sarvam-105b-conversations",
            )
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            return self._generate_fallback_response(question, language, context)
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            return self._generate_fallback_response(question, language, context)

    def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.wav", content_type: str = "audio/wav") -> tuple[str, str]:
        if not self.client:
            raise RuntimeError("Sarvam client is not configured.")

        # Ensure filename has an appropriate extension
        if "." not in filename:
            filename = f"{filename}.wav"

        ext = Path(filename).suffix.lower()
        if not content_type or content_type.startswith("video/") or content_type == "application/octet-stream":
            if ext == ".wav":
                content_type = "audio/wav"
            elif ext == ".webm":
                content_type = "audio/webm"
            elif ext == ".ogg":
                content_type = "audio/ogg"
            elif ext in [".mp4", ".m4a"]:
                content_type = "audio/mp4"
            elif ext == ".mp3":
                content_type = "audio/mpeg"
            else:
                content_type = "audio/wav"

        logger.info(f"Calling Sarvam STT with file: {filename}, size: {len(audio_bytes)} bytes, mime: {content_type}")

        response = self.client.speech_to_text.transcribe(
            file=(filename, io.BytesIO(audio_bytes), content_type),
            model="saaras:v4",
            language_code="unknown",
            mode="codemix",
        )
        detected_lang = getattr(response, "language_code", None) or "ta-IN"
        transcript = getattr(response, "transcript", "").strip()
        logger.info(f"Sarvam STT success. Detected lang: {detected_lang}, Transcript: '{transcript}'")
        return detected_lang, transcript

    def text_to_speech(self, text: str, language_code: str = "ta-IN") -> str | None:
        if not self.client:
            return None

        try:
            tts_lang = language_code if language_code in ["ta-IN", "en-IN", "hi-IN", "te-IN", "kn-IN", "ml-IN"] else "ta-IN"
            clean_text = self.clean_for_tts(text)

            response = self.client.text_to_speech.convert(
                text=clean_text,
                language_code=tts_lang,
                model="bulbul:v3",
                output_audio_codec="wav",
            )
            if response and response.audios and len(response.audios) > 0:
                return response.audios[0]
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}")
        return None

    def process_voice_chat(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        preferred_language: str = "ta",
        content_type: str = "audio/wav",
        context: dict = None
    ) -> dict:
        # Step 1: Speech-to-Text (Saaras v4)
        detected_lang = "ta-IN" if "ta" in preferred_language else "en-IN"
        transcript = ""
        try:
            detected_lang, transcript = self.speech_to_text(audio_bytes, filename=filename, content_type=content_type)
        except Exception as e:
            logger.exception(f"STT processing failed for file '{filename}' ({len(audio_bytes)} bytes): {e}")

        if not transcript:
            fallback_msg = "மன்னிக்கவும், உங்கள் குரல் தெளிவாகக் கேட்கவில்லை. மீண்டும் பேசவும் அல்லது தட்டச்சு செய்யவும்." if "ta" in preferred_language else "Sorry, I could not hear any speech clearly. Please try again or type your question."
            audio_data = self.text_to_speech(fallback_msg, language_code="ta-IN" if "ta" in preferred_language else "en-IN")
            return {
                "detected_language": detected_lang or "unknown",
                "transcription": "",
                "reply": fallback_msg,
                "audio_base64": audio_data,
            }

        # Step 2: Sarvam-105B Chatbot with grounded agricultural context
        ai_reply = self.answer(
            transcript,
            language="ta" if "ta" in detected_lang else preferred_language,
            context=context
        )

        # Step 3: Text-to-Speech (Bulbul v3)
        audio_base64 = self.text_to_speech(ai_reply, language_code=detected_lang)

        return {
            "detected_language": detected_lang,
            "transcription": transcript,
            "reply": ai_reply,
            "audio_base64": audio_base64,
        }
