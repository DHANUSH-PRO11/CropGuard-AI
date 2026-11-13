import io
import logging
import os
import re
import base64
import requests
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
       
        load_dotenv(dotenv_path=base_dir / ".env")
        load_dotenv(dotenv_path=base_dir / "backend" / ".env")

        self.gnani_api_key = os.environ.get("GNANI_API_KEY")
        self.api_key = os.environ.get("SARVAM_API_KEY")

        for candidate in [base_dir / ".env", base_dir / "backend" / ".env"]:
            if candidate.exists():
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not self.gnani_api_key and line.startswith("GNANI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            self.gnani_api_key = val
                    if not self.api_key and line.startswith("SARVAM_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            self.api_key = val

        # Fallback key for serverless Vercel deployment if dashboard env vars are not set
        if not self.gnani_api_key:
            self.gnani_api_key = "vach_1ytE2CY5X2EB7Rx1KDRLPVPvNvl19OVWCDOgHImeYU5SSVXaOHx6i3opg0s53mYN5WjUEZ5wfabFGsbJKjOTfYDWReZUIqCC_a78315d638d083ac6d676c5f402d056b"

        if self.gnani_api_key:
            logger.info("Gnani AI voice models (Prisma STT & Timbre TTS) active.")

        if self.api_key and SarvamAI is not None:
            self.client = SarvamAI(api_subscription_key=self.api_key)
        else:
            self.client = None
            if not SarvamAI:
                logger.warning("sarvamai package is not installed; AI assistant features will operate in fallback mode.")


    def clean_for_tts(self, text: str, max_chars: int = 260) -> str:
        """Strip markdown/emoji symbols and summarize to a crisp spoken length for fast Timbre TTS."""
        # Remove markdown tokens, bullets, and emoji/pictograph ranges while preserving Tamil/ASCII punctuation
        clean = re.sub(r'[*_~`#•🌾🎤📷🤖⚠️✅🌱💧☀️]+', ' ', text)
        clean = re.sub(r'^\s*(?:[-+*]|\d+\.)\s+', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'\n+', '. ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        clean = re.sub(r'\.\s*\.', '.', clean)

        if len(clean) <= max_chars:
            return clean

        # Trim cleanly at the nearest sentence or punctuation boundary
        truncated = clean[:max_chars]
        for sep in ['. ', '। ', ', ', '; ', ': ']:
            idx = truncated.rfind(sep)
            if idx >= int(max_chars * 0.45):
                return truncated[:idx + 1].strip()

        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space].strip() + "."
        return truncated.strip()

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
        """
        Intelligent, grounded agricultural reasoner that analyzes the farmer's question,
        identifies the crop and symptoms (leaf drop, growth, fertilizer, pests, disease, weather),
        and synthesizes specific, actionable agronomic advice in Tamil or English.
        """
        q_lower = (question or "").lower()
        is_tamil = language == "ta" or any('\u0b80' <= c <= '\u0bff' for c in question)

        # 1. Identify Crop Mentioned in Question or Context
        crop = context.get("crop") if context else None
        crop_name = ""

        crops_map = [
            ("ஆப்பிள்", "Apple", ["ஆப்பிள்", "apple"]),
            ("தக்காளி", "Tomato", ["தக்காளி", "tomato"]),
            ("நெல்", "Paddy / Rice", ["நெல்", "அரிசி", "paddy", "rice"]),
            ("பருத்தி", "Cotton", ["பருத்தி", "cotton"]),
            ("மிளகாய்", "Chilli", ["மிளகாய்", "chilli", "chili", "pepper"]),
            ("வாழை", "Banana", ["வாழை", "banana"]),
            ("மக்காச்சோளம்", "Maize / Corn", ["மக்காச்சோளம்", "சோளம்", "maize", "corn"]),
            ("மாமரம்", "Mango", ["மாமரம்", "மாம்பழம்", "மாங்காய்", "mango"]),
            ("உருளைக்கிழங்கு", "Potato", ["உருளை", "potato"]),
            ("வெங்காயம்", "Onion", ["வெங்காயம்", "onion"]),
            ("தென்னை", "Coconut", ["தென்னை", "தேங்காய்", "coconut"]),
            ("நிலக்கடலை", "Groundnut", ["நிலக்கடலை", "வேர்க்கடலை", "groundnut", "peanut"]),
            ("எலுமிச்சை", "Citrus / Lemon", ["எலுமிச்சை", "citrus", "lemon"]),
            ("கரும்பு", "Sugarcane", ["கரும்பு", "sugarcane"]),
            ("கத்தரி", "Brinjal", ["கத்தரி", "brinjal", "eggplant"]),
            ("வெண்டை", "Okra / Bhendi", ["வெண்டை", "okra", "bhendi"]),
            ("முருங்கை", "Moringa", ["முருங்கை", "moringa", "drumstick"]),
            ("மல்லிகை", "Jasmine", ["மல்லிகை", "jasmine", "பூச்செடி"]),
            ("பயிர்", "Crop / Plant", ["செடி", "பயிர்", "மரம்", "plant", "tree", "crop"]),
        ]

        detected_crop_ta = None
        detected_crop_en = None
        for ta, en, keywords in crops_map:
            if any(k in q_lower for k in keywords):
                detected_crop_ta = ta
                detected_crop_en = en
                break

        if not detected_crop_ta and crop:
            detected_crop_ta = crop
            detected_crop_en = crop

        crop_header_ta = f" ({detected_crop_ta})" if detected_crop_ta else ""
        crop_header_en = f" ({detected_crop_en})" if detected_crop_en else ""

        # 2. Extract Symptoms, Problems & Intent
        has_leaf_drop = any(w in q_lower for w in ["விழுகுத", "உதிர", "கொட்டு", "leaf drop", "falling", "shedding"])
        has_growth_issue = any(w in q_lower for w in ["வளர", "வளர்ச்சி", "வளரல", "growth", "stunt", "slow growth", "not growing"])
        has_fertilizer = any(w in q_lower for w in ["ஃபெர்டிலைசர்", "உரம்", "உர", "ஊட்டச்சத்து", "fertilizer", "nutrient", "npk", "urea", "potash", "manure"])
        has_yellowing = any(w in q_lower for w in ["மஞ்சள்", "பழுப்பு", "yellow", "chlorosis", "pale"])
        has_pests = any(w in q_lower for w in ["பூச்சி", "புழு", "வண்டு", "அசுவினி", "pest", "worm", "caterpillar", "borer", "bug", "aphid"])
        has_fungus_blight = any(w in q_lower for w in ["பூஞ்சை", "கருகல்", "அழுகல்", "வாடல்", "புள்ளி", "fungus", "blight", "rot", "wilt", "spot", "mildew"])
        has_flower_fruit_drop = any(w in q_lower for w in ["பூ உதிர", "காய் உதிர", "பூ கொட்டு", "flower drop", "fruit drop"])
        has_water_issue = any(w in q_lower for w in ["தண்ணீர்", "பாசனம்", "நீர்", "water", "irrigation", "drainage"])
        has_weather_query = any(w in q_lower for w in ["வானிலை", "மழை", "மருந்து அடிக்கலாமா", "spray", "weather", "rain"])
        has_schemes = any(w in q_lower for w in ["திட்டம்", "மானியம்", "காப்பீடு", "scheme", "subsidy", "pm-kisan", "insurance"])

        cond = context.get("condition") if context else ""
        weather = context.get("weather", {}) if context else {}
        alerts = weather.get("alerts", []) if isinstance(weather, dict) else []

        # 3. Synthesize Tailored Response in Tamil
        if is_tamil:
            lines = [f"🌾 அக்ரோநெக்ஸ் விவசாய வழிகாட்டல்{crop_header_ta}:"]

            if has_schemes:
                lines.append("• அரசு விவசாய நலத் திட்டங்கள்:")
                lines.append("  1. பி.எம்-கிசான் (PM-KISAN): ஆண்டுக்கு ₹6,000 நேரடி உதவித்தொகை.")
                lines.append("  2. பயிர் காப்பீட்டுத் திட்டம் (PMFBY): இயற்கை இடர்பாடுகளுக்கான இழப்பீடு.")
                lines.append("  3. நுண்ணீர் பாசன மானியம்: சிறு, குறு விவசாயிகளுக்கு 100% மானியத்தில் சொட்டு நீர் பாசனம்.")
                lines.append("• அருகிலுள்ள வட்டார வேளாண்மை விரிவாக்க மையத்தை (ADA Office) அணுகவும்.")
                return "\n".join(lines)

            if has_leaf_drop or has_growth_issue:
                lines.append(f"• இலை உதிர்தல் மற்றும் வளர்ச்சி குறைபாட்டிற்கான முக்கிய காரணங்கள்:")
                lines.append("  1. வேர் பகுதியில் அதிகப்படியான நீர் தேக்கம் அல்லது கடுமையான வறட்சி (வேர் அழுகல்).")
                lines.append("  2. முக்கிய ஊட்டச்சத்துக்களான நைட்ரஜன், துத்தநாகம் (Zinc) மற்றும் இரும்புச்சத்து பற்றாக்குறை.")
                lines.append("  3. மண்ணில் போதிய காற்றோட்டமின்மை அல்லது கார-அமிலத்தன்மை (pH) ஏற்றத்தாழ்வு.")

            if has_fertilizer or has_growth_issue:
                lines.append(f"• பரிந்துரைக்கப்படும் உர மேலாண்மை:")
                lines.append("  1. இயற்கை உரம்: மட்கிய தொழு உரம் அல்லது மண்புழு உரம் 15-20 கிலோ மரத்தை சுற்றி 2 அடி தள்ளி இடவும்.")
                lines.append("  2. வளர்ச்சி ஊக்கி: 19:19:19 (NPK) நீரில் கரையும் உரத்தை 1 லிட்டர் தண்ணீருக்கு 5 கிராம் வீதம் கலந்து இலைகளில் தெளிக்கவும்.")
                lines.append("  3. நுண்ணூட்டச்சத்து: Zinc Sulphate மற்றும் Boron கலவையை தெளிப்பது புதிய தளிர்கள் விடவும் இலை உதிர்தலைத் தடுக்கவும் உதவும்.")

            if has_yellowing:
                lines.append("• இலைகள் மஞ்சள் நிறமாவதை சரிசெய்ய:")
                lines.append("  1. எப்சம் உப்பு (Magnesium Sulphate) 1 லிட்டர் தண்ணீருக்கு 5 கிராம் வீதம் தெளிக்கவும்.")
                lines.append("  2. இரும்புச்சத்து குறைபாட்டிற்கு Ferrous Sulphate (19:19:19 உடன்) தெளிப்பது இலைகளை மீண்டும் பசுமையாக்கும்.")

            if has_pests:
                lines.append("• பூச்சி & புழு கட்டுப்பாடு:")
                lines.append("  1. வேப்ப எண்ணெய் கரைசல் (3% - 10 லிட்டர் தண்ணீருக்கு 30 மி.லி) + காதி சோப் கலந்து மாலையில் தெளிக்கவும்.")
                lines.append("  2. சாறு உறிஞ்சும் பூச்சிகளுக்கு மஞ்சள் மற்றும் நீல நிற ஒட்டும் பொறிகளை ஏக்கருக்கு 6-8 வைக்கவும்.")

            if has_fungus_blight or cond:
                cond_text = f" ({cond.replace('_', ' ')})" if cond else ""
                lines.append(f"• நோய் & பூஞ்சை மேலாண்மை{cond_text}:")
                lines.append("  1. பாதிக்கப்பட்ட இலைகளை உடனே வெட்டி அகற்றி அழிக்கவும்.")
                lines.append("  2. காப்பர் ஆக்சிகுளோரைடு (COC) 1 லிட்டருக்கு 2.5 கிராம் அல்லது டிரைக்கோடெர்மா விரிடி உயிரி பூஞ்சாணக்கொல்லி இடவும்.")

            if has_flower_fruit_drop:
                lines.append("• பூ & பிஞ்சு உதிர்தலைத் தடுக்க:")
                lines.append("  1. பிளனோபிக்ஸ் (Planofix) 4.5 லிட்டர் தண்ணீருக்கு 1 மி.லி வீதம் பூக்கும் தருணத்தில் தெளிக்கவும்.")
                lines.append("  2. போராக்ஸ் (Borax) 1 கிராம்/லிட்டர் தெளிப்பது காய் பிடிப்பை அதிகரிக்கும்.")

            if has_weather_query or alerts:
                if alerts:
                    lines.append(f"• வானிலை ஆலோசனை: {alerts[0].get('message_ta', 'மழை எச்சரிக்கை உள்ளது, மருந்து தெளிப்பதைத் தவிர்க்கவும்.')}")
                else:
                    lines.append("• தெளிப்பு நேரம்: காற்று வேகம் குறைவாக உள்ள காலை 7-10 மணி அல்லது மாலை 4-6 மணி வேளையில் மருந்து தெளிக்கவும்.")

            # Default actionable conclusion
            if len(lines) == 1:
                lines.append("• பயிர் பாதுகாப்பு வழிகாட்டல்:")
                lines.append("  1. மண்ணின் ஈரப்பதத்தை சீராகப் பராமரித்து, வேர் பகுதியில் நீர் தேங்காமல் பார்த்துக் கொள்ளவும்.")
                lines.append("  2. இயற்கை மண்புழு உரம் மற்றும் நுண்ணூட்டச்சத்து கலவை இடுவது செடியின் நோய் எதிர்ப்பு சக்தியை அதிகரிக்கும்.")
                lines.append("  3. இயற்கை வேப்ப எண்ணெய் (3%) கரைசலை 15 நாட்களுக்கு ஒருமுறை தெளிக்கவும்.")

            lines.append("• மேலதிக கள ஆய்வுக்கு உங்கள் பகுதி வேளாண் அறிவியல் நிலையத்தை (KVK) அணுகவும்.")
            return "\n".join(lines)

        # 4. Synthesize Tailored Response in English
        else:
            lines = [f"🌾 AgroNex Agricultural Copilot Guidance{crop_header_en}:"]

            if has_schemes:
                lines.append("• Key Government Agricultural Schemes:")
                lines.append("  1. PM-KISAN: ₹6,000 annual direct income support in 3 equal installments.")
                lines.append("  2. PMFBY (Pradhan Mantri Fasal Bima Yojana): Subsidized comprehensive crop insurance.")
                lines.append("  3. Per Drop More Crop (Micro Irrigation): Up to 100% subsidy for drip/sprinkler setups.")
                lines.append("• Visit your nearest Krishi Vigyan Kendra (KVK) or Agriculture Department to apply.")
                return "\n".join(lines)

            if has_leaf_drop or has_growth_issue:
                lines.append("• Primary Causes for Leaf Drop & Stunted Growth:")
                lines.append("  1. Root Stress: Waterlogging or extreme root dryness leading to early root rot.")
                lines.append("  2. Nutrient Deficiencies: Lack of vegetative Nitrogen, Zinc, or Magnesium.")
                lines.append("  3. Compacted Soil: Poor aeration preventing roots from expanding.")

            if has_fertilizer or has_growth_issue:
                lines.append("• Recommended Fertilizer & Nutrition Schedule:")
                lines.append("  1. Organic Base: Apply 15-20 kg well-decomposed FYM (farmyard manure) or vermicompost around the drip line.")
                lines.append("  2. Foliar Booster: Spray 19:19:19 (NPK) water-soluble fertilizer at 5g per litre of water to spur active vegetative shoots.")
                lines.append("  3. Micronutrient Mix: Apply Zinc Sulphate and Boron to halt premature leaf shedding and promote canopy vigor.")

            if has_yellowing:
                lines.append("• Correcting Yellowing / Chlorotic Foliage:")
                lines.append("  1. Spray Epsom Salt (Magnesium Sulphate) at 5g/L to restore chlorophyll synthesis.")
                lines.append("  2. Apply chelated Iron/Zinc if interveinal yellowing persists.")

            if has_pests:
                lines.append("• Integrated Pest Management:")
                lines.append("  1. Spray 3% Neem oil emulsion (30ml in 10L water + mild soap) during calm evening hours.")
                lines.append("  2. Install yellow sticky traps (6-8 per acre) to intercept sucking pests.")

            if has_fungus_blight or cond:
                cond_text = f" ({cond.replace('_', ' ')})" if cond else ""
                lines.append(f"• Fungal & Pathology Management{cond_text}:")
                lines.append("  1. Prune and safely destroy heavily spotted/infected foliage to stop spread.")
                lines.append("  2. Apply Copper Oxychloride (2.5g/L) or bio-fungicide Trichoderma viride around the root zone.")

            if has_flower_fruit_drop:
                lines.append("• Mitigating Flower & Fruit Drop:")
                lines.append("  1. Spray Planofix (alpha naphthyl acetic acid) at 1ml per 4.5 litres of water.")
                lines.append("  2. Supplement with Borax (1g/L) during flower bud initiation.")

            if has_weather_query or alerts:
                if alerts:
                    lines.append(f"• Weather Alert: {alerts[0].get('message_en', 'Rain forecasted. Postpone chemical foliar applications.')}")
                else:
                    lines.append("• Safe Spray Window: Spray only during calm morning (7-10 AM) or late afternoon (4-6 PM) when wind is <20 km/h.")

            # Default actionable conclusion
            if len(lines) == 1:
                lines.append("• Agronomic Action Plan:")
                lines.append("  1. Maintain steady soil moisture without surface water accumulation.")
                lines.append("  2. Incorporate organic vermicompost and balanced micronutrients to strengthen natural plant immunity.")
                lines.append("  3. Inspect leaf undersides weekly for early pest colonies.")

            lines.append("• For certified on-site verification, consult your local agricultural extension officer (KVK).")
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

    def _gnani_speech_to_text(self, audio_bytes: bytes, filename: str = "audio.wav", content_type: str = "audio/wav") -> tuple[str, str]:
        """
        Transcribes speech using Gnani AI's Prisma v3.0 model (REST API).
        Supports indic-auto language identification and conversational code-mixing.
        """
        if not self.gnani_api_key:
            raise RuntimeError("GNANI_API_KEY is not configured.")

        url = "https://api.vachana.ai/stt/v3"
        headers = {
            "X-API-Key-ID": self.gnani_api_key
        }
        files = {
            "audio_file": (filename, io.BytesIO(audio_bytes), content_type)
        }
        data = {
            "model": "prisma-v3.0",
            "language_code": "indic-auto"
        }
        logger.info(f"Calling Gnani AI Prisma v3 STT ({filename}, {len(audio_bytes)} bytes)")
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Gnani Prisma STT returned HTTP {resp.status_code}: {resp.text}")

        res_json = resp.json()
        transcript = res_json.get("transcript", "").strip()
        detected_lang = res_json.get("detected_language_code") or "ta-IN"
        logger.info(f"Gnani Prisma STT success. Lang: {detected_lang}, Transcript: '{transcript}'")
        return detected_lang, transcript

    def _gnani_text_to_speech(self, text: str, language_code: str = "ta-IN") -> str | None:
        """
        Synthesizes natural spoken regional speech using Gnani AI's Timbre v3.0 model.
        Returns base64 encoded WAV audio string.
        """
        if not self.gnani_api_key:
            return None

        url = "https://api.vachana.ai/api/v1/tts/inference"
        headers = {
            "X-API-Key-ID": self.gnani_api_key,
            "Content-Type": "application/json"
        }
        clean_text = self.clean_for_tts(text)
        # Match Gnani supported regional locale codes
        valid_langs = ["ta-IN", "hi-IN", "en-IN", "kn-IN", "te-IN", "ml-IN", "mr-IN", "gu-IN", "bn-IN", "pa-IN"]
        tts_lang = language_code if language_code in valid_langs else "ta-IN"

        payload = {
            "text": clean_text,
            "voice": "Lakshmi",
            "model": "timbre-v3.0",
            "language": tts_lang,
            "speed": 1.0,
            "audio_config": {
                "encoding": "linear_pcm",
                "container": "wav",
                "num_channels": 1,
                "sample_rate": 16000,
                "sample_width": 2
            }
        }
        logger.info(f"Calling Gnani AI Timbre v3 TTS ({tts_lang}, {len(clean_text)} chars)")
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200 and resp.content:
            logger.info(f"Gnani Timbre TTS success ({len(resp.content)} audio bytes received)")
            return base64.b64encode(resp.content).decode("utf-8")
        else:
            logger.warning(f"Gnani Timbre TTS failed ({resp.status_code}): {resp.text}")
            return None

    def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.wav", content_type: str = "audio/wav") -> tuple[str, str]:
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

        # 1. Primary: Gnani AI Prisma STT (Great Indian AI Challenge)
        if self.gnani_api_key:
            try:
                return self._gnani_speech_to_text(audio_bytes, filename=filename, content_type=content_type)
            except Exception as e:
                logger.warning(f"Gnani Prisma STT error: {e}. Checking fallback provider.")

        # 2. Secondary: Sarvam AI Saaras v4 STT
        if self.client:
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

        raise RuntimeError("No STT client (Gnani AI or Sarvam AI) is configured.")

    def text_to_speech(self, text: str, language_code: str = "ta-IN") -> str | None:
        clean_text = self.clean_for_tts(text)

        # 1. Primary: Gnani AI Timbre TTS (Great Indian AI Challenge)
        if self.gnani_api_key:
            try:
                audio = self._gnani_text_to_speech(clean_text, language_code=language_code)
                if audio:
                    return audio
            except Exception as e:
                logger.warning(f"Gnani Timbre TTS error: {e}. Checking fallback provider.")

        # 2. Secondary: Sarvam AI Bulbul v3 TTS
        if self.client:
            try:
                tts_lang = language_code if language_code in ["ta-IN", "en-IN", "hi-IN", "te-IN", "kn-IN", "ml-IN"] else "ta-IN"
                response = self.client.text_to_speech.convert(
                    text=clean_text,
                    language_code=tts_lang,
                    model="bulbul:v3",
                    output_audio_codec="wav",
                )
                if response and response.audios and len(response.audios) > 0:
                    return response.audios[0]
            except Exception as e:
                logger.error(f"Sarvam TTS conversion failed: {e}")

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
