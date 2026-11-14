import io
import logging
import os
import re
import base64
import importlib
import requests
from pathlib import Path
from dotenv import load_dotenv

try:
    _sarvam_mod = importlib.import_module("sarvamai")
    SarvamAI = getattr(_sarvam_mod, "SarvamAI", None)
except Exception:
    SarvamAI = None

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are AgroNex, a knowledgeable, farmer-friendly AI agricultural copilot for smallholder and commercial farmers.

CORE OBJECTIVE:
Provide complete, useful, and actionable agricultural explanations containing all important agronomic guidance in a clear, structured, and farmer-friendly format. The response length must naturally match the complexity of the inquiry. Never force responses into a fixed number of lines, sentences, or bullet points.

RESPONSE STRUCTURE & CONTENT GUIDELINES:
1. Direct Explanation & Possible Causes:
   - Begin immediately with the likely causes or explanation in clear, simple terms.
   - Clearly distinguish confirmed visual observations from possible or probable underlying causes (such as excess watering, root rot, fungal/bacterial infection, pest damage, or nutrient deficiencies).
   - Skip pleasantries, robotic greetings ("Hello!", "I understand you are worried..."), and repetitive filler.

2. Practical Immediate Actions & Preventive Steps:
   - Provide all practical, necessary next steps using clear, readable bullet points under the heading **உடனடியாக செய்ய வேண்டியவை:** (or **What to do now:** in English).
   - Focus on cultural sanitation, irrigation/drainage adjustment, organic remedies, and bio-controls (such as neem oil, Trichoderma viride, vermicompost) before chemical interventions.
   - Explain necessary precautions (e.g. not spraying chemicals without confirmation, avoiding spraying during rain or high wind).

3. Weather & Spray Safety Integration:
   - If rain (>60% probability or >2mm) is forecast within 24-48 hours, advise postponing foliar sprays to prevent chemical wash-off.
   - If wind speed exceeds 25 km/h, advise against spraying due to drift hazards.

4. Expert Verification:
   - Conclude with a single, helpful recommendation under **குறிப்பு:** (or **Note:** in English) advising the farmer to verify with their nearest Krishi Vigyan Kendra (KVK) or village agricultural extension officer if the issue persists.
   - Do NOT repeat the KVK disclaimer multiple times.

FORMATTING RULES:
- Use clean Markdown with readable headings (e.g., **உடனடியாக செய்ய வேண்டியவை:** / **What to do now:** and **குறிப்பு:** / **Note:**).
- Use concise bullet points for action steps.
- Avoid unnecessary technical jargon; speak in terms practical farmers understand.
- Language: Respond in the farmer's preferred language (Tamil, English, or conversational Tamil-English code-mix commonly used by Tamil Nadu farmers)."""

class AIAssistant:
    def __init__(self):
        base_dir = BASE_DIR
        load_dotenv(dotenv_path=base_dir / ".env")
        load_dotenv(dotenv_path=base_dir / "backend" / ".env")

        self.api_key = os.environ.get("SARVAM_API_KEY")

        for candidate in [base_dir / ".env", base_dir / "backend" / ".env"]:
            if candidate.exists():
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not self.api_key and line.startswith("SARVAM_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            self.api_key = val

        if self.api_key and SarvamAI is not None:
            self.client = SarvamAI(api_subscription_key=self.api_key)
            logger.info("Sarvam AI client initialized successfully.")
        else:
            self.client = None
            if not SarvamAI:
                logger.warning("sarvamai package is not installed; AI assistant features will operate in fallback mode.")
            elif not self.api_key:
                logger.warning("SARVAM_API_KEY is not configured; AI assistant will operate in fallback mode.")

    def clean_for_tts(self, text: str) -> str:
        """
        Cleans markdown tokens, asterisks, hashtags, and decorative emojis so that
        Sarvam Bulbul v3 reads the complete response naturally aloud without pronunciation artifacts.
        Preserves all paragraphs, bullet points, and sentences in full without truncation.
        """
        if not text:
            return ""

        # Remove markdown bold/italics markers (*, **, _, ~)
        clean = re.sub(r'[*_~`#]+', '', text)
        # Remove decorative emojis
        clean = re.sub(r'[🌾🎤📷🤖⚠️✅🌱💧☀️💡]+', ' ', clean)
        # Normalize bullet markers at start of lines into clean spoken flow
        clean = re.sub(r'^\s*[-•*]\s*', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'^\s*\d+\.\s*', '', clean, flags=re.MULTILINE)
        # Clean colons followed by newlines/dots
        clean = re.sub(r':\s*\.+', ':', clean)
        clean = re.sub(r'\.+\s*:', ':', clean)
        # Convert line breaks to periods/pauses
        clean = re.sub(r'\n+', '. ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        clean = re.sub(r'\.\s*\.', '.', clean)

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
        """
        Intelligent, grounded agricultural reasoner that analyzes the farmer's question,
        identifies the crop and symptoms (dots/spots, leaf drop, leaf curl, growth, fertilizer,
        pests, mildew, rot, weather, schemes), and synthesizes specific, actionable agronomic advice.
        Follows a structured format:
        1. Possible causes / explanation (distinguishing visual observation from confirmed diagnosis)
        2. Practical immediate actions & precautions as bullet points under '**உடனடியாக செய்ய வேண்டியவை:**' / '**What to do now:**'
        3. Expert verification under '**குறிப்பு:**' / '**Note:**' (recommending KVK or agricultural officer verification)
        """
        q_lower = (question or "").lower()
        is_tamil = language == "ta" or any('\u0b80' <= c <= '\u0bff' for c in question)

        # 1. Identify Crop Mentioned in Question or Context
        crop = context.get("crop") if context else None

        crops_map = [
            ("மஞ்சள் செடி", "Turmeric", ["மஞ்சள் செடி", "மஞ்சள் பயிர்", "மஞ்சள் கிழங்கு", "turmeric"]),
            ("ஆப்பிள்", "Apple", ["ஆப்பிள்", "apple"]),
            ("தக்காளி", "Tomato", ["தக்காளி", "tomato"]),
            ("நெல்", "Paddy / Rice", ["நெல்", "நெற்", "அரிசி", "paddy", "rice"]),
            ("பருத்தி", "Cotton", ["பருத்தி", "cotton"]),
            ("மிளகாய்", "Chilli", ["மிளகாய்", "chilli", "chili", "pepper"]),
            ("வாழை", "Banana", ["வாழை", "banana"]),
            ("மக்காச்சோளம்", "Maize / Corn", ["மக்காச்சோளம்", "சோளம்", "maize", "corn"]),
            ("மாமரம்", "Mango", ["மாமரம்", "மாம்பழம்", "மாங்காய்", "மாஞ்செடி", "mango"]),
            ("உருளைக்கிழங்கு", "Potato", ["உருளை", "potato"]),
            ("வெங்காயம்", "Onion", ["வெங்காயம்", "onion"]),
            ("தென்னை", "Coconut", ["தென்னை", "தேங்காய்", "தென்னங்", "coconut"]),
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

        crop_name_ta = detected_crop_ta or "பயிர்"
        crop_name_en = detected_crop_en or "crop"

        # 2. Extract Comprehensive Symptoms, Problems & Intent
        has_spots_dots = any(w in q_lower for w in [
            "டாட்", "டாட்டாக", "டாட்கள்", "புள்ளி", "புள்ளிகள்", "கரும்புள்ளி", "செம்புள்ளி",
            "மஞ்சள் புள்ளி", "திட்டு", "திட்டுகள்", "துளை", "துளைகள்",
            "dot", "dots", "spot", "spots", "speck", "specks", "blotch", "patch", "patches", "hole", "holes"
        ])
        has_leaf_curl = any(w in q_lower for w in [
            "சுருள்", "சுருண்", "சுருண்டு", "சுருட்டை", "சுருட்ட", "சுருங்கு", "மடங்கு", "குடை",
            "curl", "curling", "crinkle", "crinkled", "wrinkled", "twisted"
        ])
        has_white_mildew = any(w in q_lower for w in [
            "வெள்ளை", "சாம்பல்", "பவுடர்", "மாவு", "பூஞ்சணம்", "white", "powdery", "mildew", "ash", "mold", "mould"
        ])
        has_wilting_drying = any(w in q_lower for w in [
            "வாடு", "வாடி", "வாடுதல்", "காய்ந்து", "உலர்ந்து", "சருகு", "செத்து", "wilt", "wilting", "dry", "drying", "wither", "dieback"
        ])
        has_root_rot = any(w in q_lower for w in [
            "வேர் அழுகல்", "கால் அழுகல்", "வேர்", "அழுகி", "அழுகல்", "root rot", "stem rot", "collar rot", "damping"
        ])
        has_leaf_drop = any(w in q_lower for w in [
            "விழுகு", "விழும்", "விழுகுத", "விழுது", "உதிர்", "உதிர", "கொட்டு", "leaf drop", "falling", "shedding", "shed"
        ])
        has_growth_issue = any(w in q_lower for w in [
            "வளர", "வளர்ச்சி", "வளரல", "வளரவே", "growth", "stunt", "slow growth", "not growing", "குட்டைய"
        ])
        has_fertilizer = any(w in q_lower for w in [
            "ஃபெர்டிலைசர்", "உரம்", "உர", "ஊட்டச்சத்து", "fertilizer", "nutrient", "npk", "urea", "potash", "manure", "போரான்", "துத்தநாகம்"
        ])
        has_yellowing = any(w in q_lower for w in [
            "மஞ்சள்", "பழுப்பு", "வெளுத்து", "yellow", "yellowing", "chlorosis", "pale"
        ])
        has_pests = any(w in q_lower for w in [
            "பூச்சி", "புழு", "வண்டு", "அசுவினி", "வெள்ளை ஈ", "துளைப்பான்", "தத்துப்பூச்சி",
            "pest", "worm", "caterpillar", "borer", "bug", "aphid", "thrips", "whitefly", "mite", "mites"
        ])
        has_fungus_blight = any(w in q_lower for w in [
            "பூஞ்சை", "கருகல்", "திட்டு", "fungus", "blight", "canker", "scab", "rust"
        ])
        has_flower_fruit_drop = any(w in q_lower for w in [
            "பூ உதிர்", "பூ கொட்டு", "காய் உதிர்", "காய் கொட்டு", "பிஞ்சு உதிர்", "flower drop", "fruit drop"
        ])
        has_water_issue = any(w in q_lower for w in [
            "தண்ணீர்", "பாசனம்", "நீர்", "water", "irrigation", "drainage", "ஈரப்பதம்"
        ])
        has_weather_query = any(w in q_lower for w in [
            "வானிலை", "மழை", "மருந்து அடிக்கலாமா", "spray", "weather", "rain", "wind"
        ])
        has_schemes = any(w in q_lower for w in [
            "திட்டம்", "மானியம்", "காப்பீடு", "scheme", "subsidy", "pm-kisan", "insurance"
        ])

        cond = context.get("condition") if context else ""
        weather = context.get("weather", {}) if context else {}
        alerts = weather.get("alerts", []) if isinstance(weather, dict) else []

        # 3. Synthesize Tailored, Structured Response in Tamil
        if is_tamil:
            if has_schemes:
                intro = "விவசாயிகளின் நிதி பாதுகாப்பு மற்றும் நவீன வேளாண்மைக்கான முக்கிய அரசு நலத் திட்டங்கள்:"
                actions = [
                    "பி.எம்-கிசான் (PM-KISAN): தகுதியுள்ள அனைத்து விவசாயிகளுக்கும் ஆண்டுக்கு ₹6,000 நேரடி வங்கிப் பரிமாற்றம் (3 தவணைகளில்).",
                    "பிரதமர் பயிர் காப்பீட்டுத் திட்டம் (PMFBY): இயற்கை இடர்பாடுகள், வெள்ளம், வறட்சி போன்றவற்றால் ஏற்படும் பயிர் இழப்புகளுக்கு குறைந்த பிரீமியத்தில் இழப்பீடு.",
                    "நுண்ணீர் பாசன மானியத் திட்டம்: சிறு மற்றும் குறு விவசாயிகளுக்கு 100% மானியத்திலும், இதர விவசாயிகளுக்கு 75% மானியத்திலும் சொட்டு நீர் பாசன வசதி.",
                    "விவசாய ஆவணங்கள்: ஆதார் அட்டை, நில பட்டா/சிட்டா மற்றும் வங்கி கணக்கு புத்தகத்துடன் இ-சேவை மையம் மூலம் விண்ணப்பிக்கலாம்."
                ]
                note = "உங்கள் கிராம நிர்வாக அலுவலர் (VAO) அல்லது வட்டார வேளாண்மை உதவி இயக்குநர் (ADA) அலுவலகத்தை அணுகி விண்ணப்ப வழிகாட்டலைப் பெறலாம்."
            elif has_yellowing or has_water_issue:
                intro = f"உங்கள் {crop_name_ta} இலைகள் மஞ்சளாக மாறுவதற்கு அதிகப்படியான தண்ணீர், வேர் அழுகல் அல்லது ஊட்டச்சத்து குறைபாடு போன்ற காரணங்கள் இருக்கலாம். இலைகளை மட்டும் பார்த்து சரியான காரணத்தை உறுதிப்படுத்த முடியாது."
                actions = [
                    "செடிக்கு சரியான வடிகால் வசதி உள்ளதா என்று பாருங்கள். தண்ணீர் தேங்கினால் வேர் அழுகும் வாய்ப்பு உள்ளது.",
                    "மண்ணின் ஈரப்பதத்தைப் பார்த்து தேவையான அளவு மட்டும் தண்ணீர் ஊற்றுங்கள்.",
                    "பாதிக்கப்பட்ட இலைகள் மற்றும் செடியைச் சுற்றியுள்ள அழுகிய கழிவுகளை அகற்றுங்கள்.",
                    "ஊட்டச்சத்து குறைபாடு சந்தேகம் இருந்தால் மண் பரிசோதனை செய்து தேவையான உரத்தைத் தேர்வு செய்யுங்கள்.",
                    "வேர் அழுகல் அல்லது பூஞ்சை சந்தேகம் இருந்தால் 1 லிட்டர் தண்ணீரில் 5 கிராம் டிரைக்கோடெர்மா விரிடி (Trichoderma viride) கலந்து வேர்ப்பகுதியில் ஊற்றுங்கள்.",
                    "மழை வர வாய்ப்பு இருந்தாலோ அல்லது பலத்த காற்று வீசினாலோ பூஞ்சாண மருந்து தெளிப்பதைத் தவிர்க்கவும்.",
                    "காரணம் உறுதியாகத் தெரியாமல் ரசாயன மருந்துகளைத் தெளிக்க வேண்டாம்."
                ]
                note = "பிரச்சினை தொடர்ந்து இருந்தால் அருகிலுள்ள KVK அல்லது வேளாண் அதிகாரியிடம் செடியைக் காட்டி சரியான சிகிச்சையை உறுதிப்படுத்துங்கள்."
            elif has_spots_dots or has_fungus_blight or cond:
                cond_text = f" ({cond.replace('_', ' ')})" if cond else ""
                intro = f"உங்கள் {crop_name_ta} இலைகளில் புள்ளிகள் / கருகல் தோன்றுவதற்கு பூஞ்சை அல்லது பாக்டீரியா தொற்று காரணமாக இருக்கலாம்{cond_text}. இலைகளில் தோன்றும் மாற்றங்களை மட்டும் வைத்து 100% நோயை உறுதி செய்ய முடியாது."
                actions = [
                    "புள்ளிகள் விழுந்த மற்றும் அழுகிய இலைகளை உடனே வெட்டி அகற்றி தோட்டத்தில் இருந்து அப்புறப்படுத்தி அழிக்கவும்.",
                    "செடிகளின் இலைகளில் தண்ணீர் தேங்காதவாறு தரைமட்டத்தில் அல்லது சொட்டு நீர் பாசனம் மூலம் தண்ணீர் பாய்ச்சவும்.",
                    "ஆரம்பகட்ட பூஞ்சை தடுப்பிற்கு 1 லிட்டர் தண்ணீரில் 2.5 கிராம் காப்பர் ஆக்சிகுளோரைடு (COC) அல்லது 2 கிராம் மேன்கோசெப் (Mancozeb) கலந்து இலைகளின் இருபுறமும் படும்படி தெளிக்கவும்.",
                    "இயற்கை முறையில் கட்டுப்படுத்த 3% வேப்ப எண்ணெய் கரைசலை 10 நாட்களுக்கு ஒருமுறை தெளிக்கலாம்.",
                    "மழை வர வாய்ப்பு இருந்தாலோ (24-48 மணி நேரம்) அல்லது பலத்த காற்று வீசினாலோ தெளிப்பதைத் தள்ளிப்போடவும்.",
                    "நண்பகல் கடும் வெயிலில் ரசாயன மருந்துகளைத் தெளிக்க வேண்டாம்."
                ]
                note = "தொற்று பரவுவது நிற்கவில்லை என்றால் பாதிக்கப்பட்ட இலை மாதிரியுடன் அருகிலுள்ள வேளாண் அறிவியல் நிலையத்தை (KVK) அணுகி பரிசோதிக்கவும்."
            elif has_leaf_curl:
                intro = f"உங்கள் {crop_name_ta} இலைகள் சுருள்வதற்கு சாறு உறிஞ்சும் பூச்சிகள் (இலைப்பேன், அசுவினி, வெள்ளை ஈ) அல்லது பூச்சிகளால் பரவும் வைரஸ் தொற்று காரணமாக இருக்கலாம்."
                actions = [
                    "சாறு உறிஞ்சும் பூச்சிகளைக் கண்காணிக்க மற்றும் அழிக்க ஏக்கருக்கு 6-8 மஞ்சள் மற்றும் நீல வண்ண ஒட்டும் பொறிகளை அமைக்கவும்.",
                    "மாலை வேளையில் 3% வேப்ப எண்ணெய் கரைசல் (10 லிட்டர் தண்ணீருக்கு 30 மி.லி + சோப்) தெளிக்கவும்.",
                    "பாதிப்பு அதிகமாக இருந்தால் பரிந்துரைக்கப்பட்ட இமிடாக்குளோப்ரிட் (Imidacloprid 17.8% SL) 1 மி.லி / 3 லிட்டர் நீரில் கலந்து தெளிக்கவும்.",
                    "வைரஸ் தாக்கி வளர்ச்சி முற்றிலும் குன்றிய செடிகளை வேரோடு பிடுங்கி எரித்து விடவும்.",
                    "பலத்த காற்று வீசும் வேளைகளில் மருந்து தெளிப்பதைத் தவிர்க்கவும்."
                ]
                note = "பூச்சித் தாக்குதல் நீடித்தால் வேளாண் அலுவலரிடம் ஆலோசித்து ஒருங்கிணைந்த பயிர் பாதுகாப்பு முறைகளை மேற்கொள்ளவும்."
            elif has_white_mildew:
                intro = f"உங்கள் {crop_name_ta} இலைகளில் வெள்ளை நிற மாவு போன்ற படலம் சாம்பல் நோய் (Powdery Mildew) பூஞ்சைத் தொற்றால் ஏற்படுகிறது."
                actions = [
                    "செடிகளுக்கு இடையே போதுமான காற்றோட்டம் மற்றும் சூரிய ஒளி கிடைக்குமாறு அடர்ந்த கிளைகளை கவாத்து செய்யவும்.",
                    "நீரில் கரையும் கந்தகம் (Wettable Sulphur 80% WP) 3 கிராம்/லிட்டர் அல்லது 3% வேப்ப எண்ணெய் கரைசல் மாலை வேளையில் தெளிக்கவும்.",
                    "பாதிக்கப்பட்டு கீழே விழுந்த இலைகளைச் சேகரித்து எரிக்கவும்; நிலத்தில் மக்க விட வேண்டாம்.",
                    "அதிக தழைச்சத்து (நைட்ரஜன்) உரம் இடுவதைத் தவிர்த்து சமச்சீரான பொட்டாஷ் உரங்களை இடவும்."
                ]
                note = "நோயின் தீவிரத்தை கட்டுப்படுத்த இயலவில்லை எனில் KVK அதிகாரியை அணுகி மாற்று பூஞ்சாணக்கொல்லியைத் தேர்வு செய்யவும்."
            elif has_wilting_drying or has_root_rot:
                intro = f"உங்கள் {crop_name_ta} வாடி வதங்குவதற்கு வேர் அழுகல் அல்லது வாடல் நோய் (Fusarium/Pythium பூஞ்சை) காரணமாக இருக்கலாம். மண்ணில் அதிகப்படியான நீர் தேங்குவது இதற்கு முக்கியக் காரணம்."
                actions = [
                    "உடனடியாக தண்ணீர் பாய்ச்சுவதை நிறுத்தி, செடியின் அடிப்பகுதியில் தேங்கியுள்ள நீரை வடிய வைக்க வடிகால் அமைக்கவும்.",
                    "டிரைக்கோடெர்மா விரிடி (Trichoderma viride) உயிரி பூஞ்சாணக்கொல்லி 1 செடிக்கு 10-20 கிராம் அல்லது சூடோமோனாஸ் கரைசலை வேர்ப்பகுதியில் ஊற்றவும்.",
                    "செடியின் வேர்ப் பகுதியில் 100-200 கிராம் வேப்பம் புண்ணாக்கு இட்டு மண்ணை லேசாகக் கிளறிவிடவும்.",
                    "அழுகிய வேர் மற்றும் காய்ந்த செடிகளை வேரோடு அகற்றி நிலத்தில் இருந்து அப்புறப்படுத்தவும்."
                ]
                note = "வாடல் நோய் பரவும் அபாயம் உள்ளதால் வேளாண் விரிவாக்க மையத்தில் மண் பரிசோதனை செய்து வழிகாட்டல் பெறவும்."
            elif has_pests:
                intro = f"உங்கள் {crop_name_ta} பயிரில் இலை துளைப்பான் புழுக்கள், வண்டுகள் அல்லது தண்டு துளைப்பான் பூச்சிகளின் தாக்குதல் காணப்படுகிறது."
                actions = [
                    "காலை வேளையில் கண்ணில் தென்படும் புழுக்கள் மற்றும் முட்டைக் குவியல்களை கையால் சேகரித்து அழிக்கவும்.",
                    "விளக்குப் பொறிகள் மற்றும் இனக்கவர்ச்சிப் பொறிகளை அமைத்து தாய் அந்துப்பூச்சிகளைக் கட்டுப்படுத்தவும்.",
                    "இயற்கை முறையில் பேசில்லஸ் துரிஞ்சியென்சிஸ் (Bt) 2 கிராம்/லிட்டர் அல்லது 5% வேப்பங்கொட்டை சாறு தெளிக்கவும்.",
                    "நன்மை செய்யும் பூச்சிகளுக்கு பாதிப்பு ஏற்படாமல் இருக்க ஒரே பூச்சிக்கொல்லியைத் திரும்பத் திரும்ப அடிக்க வேண்டாம்."
                ]
                note = "தாக்குதல் பொருளாதார சேத நிலையைத் தாண்டினால் உள்ளூர் வேளாண் அதிகாரியின் ஆலோசனையுடன் பாதுகாப்பான பூச்சிக்கொல்லியைத் தெளிக்கவும்."
            elif has_fertilizer or has_growth_issue:
                intro = f"உங்கள் {crop_name_ta} பயிரின் ஆரோக்கியமான வளர்ச்சிக்கு சமச்சீரான ஊட்டச்சத்து மேலாண்மை அவசியம். தழைச்சத்து, சாம்பல் சத்து அல்லது நுண்ணூட்டச்சத்து குறைபாட்டால் வளர்ச்சி பாதிக்கப்படலாம்."
                actions = [
                    "அடிப்படை உரமாக செடியின் வேர்ப் பகுதியைச் சுற்றி 10-15 கிலோ மட்கிய தொழு உரம் அல்லது மண்புழு உரம் இடவும்.",
                    "வளர்ச்சியைத் தூண்ட நீரில் கரையும் 19:19:19 (NPK) உரம் 5 கிராம்/லிட்டர் நீரில் கலந்து இலைகளில் தெளிக்கவும்.",
                    "நுண்ணூட்டச்சத்து குறைபாட்டைப் போக்க துத்தநாகம் (Zinc Sulphate) மற்றும் போராக்ஸ் கலவையை பரிந்துரைக்கப்பட்ட அளவில் தெளிக்கவும்.",
                    "மண்ணின் ஈரப்பதத்தைப் பராமரித்து வேர்கள் உரங்களை எளிதில் உறிஞ்ச உதவவும்."
                ]
                note = "சரியான உரத் தேவையைத் தெரிந்துகொள்ள உங்கள் வட்டார வேளாண் அலுவலகத்தில் மண் பரிசோதனை அட்டையை (Soil Health Card) பெறவும்."
            elif has_weather_query or alerts:
                alert_text = alerts[0].get('message_ta', 'மழை எச்சரிக்கை உள்ளது.') if alerts else ""
                intro = f"உங்கள் பகுதிக்கான வானிலை நிலவரம் மற்றும் பயிர் பாதுகாப்பு வழிகாட்டல்{': ' + alert_text if alert_text else ''}."
                actions = [
                    "மழை பெய்ய வாய்ப்பு (60% மேல்) அல்லது பலத்த காற்று (25 கி.மீ/மணிக்கு மேல்) இருந்தால் ரசாயன தெளிப்புகளை உடனடியாக தள்ளிப்போடவும்.",
                    "காற்றின் வேகம் குறைவாக இருக்கும் காலை 7-10 மணி அல்லது மாலை 4-6 மணி வேளையில் மட்டுமே தெளிப்பு பணிகளை மேற்கொள்ளவும்.",
                    "மழைக்காலத்தில் வயல்களில் நீர் தேங்காமல் வடிகால்களைத் தூர்வாரி சீராகப் பராமரிக்கவும்.",
                    "தெளித்த மருந்துகள் மழையில் கழுவிச் செல்லாமல் இருக்க ஒட்டும் திரவம் (Sticker/Spreader) கலந்து தெளிக்கவும்."
                ]
                note = "வானிலை மாற்றங்களை தொடர்ந்து கவனித்து உள்ளூர் வேளாண் வானிலை அறிக்கையின்படி களப்பணிகளை திட்டமிடவும்."
            else:
                intro = f"உங்கள் {crop_name_ta} பயிரின் சீரான வளர்ச்சி மற்றும் நோய் எதிர்ப்பு சக்தியை அதிகரிக்க சிறந்த விவசாய நடைமுறைகளைப் பின்பற்றுவது அவசியமாகும்."
                actions = [
                    "மண்ணின் ஈரப்பதத்தை தொடர்ந்து பரிசோதித்து, வேர் பகுதியில் நீர் தேங்காமல் சீரான பாசனத்தை உறுதி செய்யவும்.",
                    "மட்கிய இயற்கை மண்புழு உரம் மற்றும் நுண்ணூட்டச்சத்துக்களை இட்டு மண்ணின் வளத்தை அதிகரிக்கவும்.",
                    "வாரத்திற்கு ஒருமுறை இலைகளின் அடிப்பகுதியை ஆய்வு செய்து பூச்சி மற்றும் பூஞ்சை தாக்குதலை தொடக்கத்திலேயே கண்டறியவும்.",
                    "பயிர் பாதுகாப்புக்கு 15 நாட்களுக்கு ஒருமுறை இயற்கை வேப்ப எண்ணெய் (3%) கரைசலை முன்னெச்சரிக்கையாகத் தெளிக்கவும்."
                ]
                note = "குறிப்பிட்ட நோய் அல்லது ஊட்டச்சத்து சந்தேகங்களுக்கு உங்கள் ஊர் KVK அல்லது வேளாண் அதிகாரியிடம் செடியைக் காட்டி உறுதிப்படுத்தவும்."

            lines = [intro, "", "**உடனடியாக செய்ய வேண்டியவை:**"]
            for act in actions:
                lines.append(f"- {act}")
            lines.append("")
            lines.append(f"**குறிப்பு:** {note}")
            return "\n".join(lines)

        # 4. Synthesize Tailored, Structured Response in English
        else:
            if has_schemes:
                intro = "Key Government Agricultural Schemes for farmer financial security and modernized farming support:"
                actions = [
                    "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi): Provides ₹6,000 annual direct income support to eligible farmer families in three equal installments.",
                    "PMFBY (Pradhan Mantri Fasal Bima Yojana): Low-premium comprehensive crop insurance protecting against unforeseen weather calamities, floods, and droughts.",
                    "Per Drop More Crop (Micro-Irrigation): Offers up to 100% subsidy for small and marginal farmers on drip and sprinkler irrigation installations.",
                    "Required Application Documents: Aadhaar card, land ownership record (patta/chitta), and active bank passbook."
                ]
                note = "Visit your nearest Block Agricultural Extension Office (ADA) or e-Sevai centre for application assistance."
            elif has_yellowing or has_water_issue:
                intro = f"Yellowing leaves on your {crop_name_en} can be caused by excess water, root rot, or nutrient deficiencies. A visual observation alone cannot confirm the exact underlying cause."
                actions = [
                    "Check whether your soil has proper drainage. Standing water rapidly suffocates roots and causes fungal root rot.",
                    "Regulate irrigation based on soil moisture depth; water only when needed and avoid waterlogging.",
                    "Prune and safely remove all yellowed, decaying leaves and debris from around the plant base.",
                    "If nutrient deficiency is suspected, conduct a soil test or apply well-decomposed organic manure before selecting fertilizers.",
                    "If root rot or fungal infection is suspected, drench the root zone with bio-fungicide Trichoderma viride (5g to 10g per litre of water).",
                    "Avoid spraying foliar treatments if rainfall (>60% probability) is forecast within 24-48 hours or during high winds (>25 km/h).",
                    "Do not apply unconfirmed chemical fungicides or pesticides until the exact cause is verified."
                ]
                note = "If the problem persists, consult your local Krishi Vigyan Kendra (KVK) or agricultural extension officer for certified on-site verification."
            elif has_spots_dots or has_fungus_blight or cond:
                cond_text = f" ({cond.replace('_', ' ')})" if cond else ""
                intro = f"Spots, specks, or blighting on your {crop_name_en} leaves are typically caused by foliar fungal or bacterial pathogens{cond_text}. A visual inspection alone cannot provide a 100% verified diagnosis."
                actions = [
                    "Prune and safely destroy heavily spotted or infected leaves to halt airborne fungal spore dissemination.",
                    "Water directly at the root zone and avoid overhead irrigation to prevent moisture from sitting on foliage.",
                    "Apply Copper Oxychloride (COC at 2.5g/L) or Mancozeb 75% WP (2g/L) thoroughly covering both leaf surfaces.",
                    "For organic suppression, spray a 3% neem oil emulsion every 10 to 14 days during early morning or late afternoon.",
                    "Postpone chemical spraying if rain (>60% probability) is forecast within 24-48 hours or if wind speed exceeds 25 km/h.",
                    "Never spray chemical fungicides during intense midday sunlight to avoid leaf scorching."
                ]
                note = "If lesions continue spreading, submit a symptomatic leaf sample to your nearest Krishi Vigyan Kendra (KVK) for laboratory confirmation."
            elif has_leaf_curl:
                intro = f"Leaf curling on your {crop_name_en} is commonly triggered by sap-sucking insect vectors (thrips, whiteflies, aphids) or vector-transmitted viral infections."
                actions = [
                    "Install yellow and blue sticky traps (6-8 traps per acre) to monitor and capture flying sucking insect vectors.",
                    "Apply a 3% neem oil emulsion (30ml in 10L water + mild soap) during calm evening hours.",
                    "For severe infestations, apply recommended systemic insecticides such as Imidacloprid 17.8% SL (1ml per 3 litres of water).",
                    "Uproot and safely incinerate severely stunted or virus-infected plants to prevent transmission to healthy crops.",
                    "Avoid spraying when ambient wind exceeds 20 km/h to prevent spray drift."
                ]
                note = "Consult your local agricultural extension officer for regional integrated pest management (IPM) advisories."
            elif has_white_mildew:
                intro = f"The powdery white residue on your {crop_name_en} leaves indicates a powdery mildew fungal infection thriving in humid microclimates."
                actions = [
                    "Prune overcrowded interior branches to promote sunlight penetration and free airflow through the crop canopy.",
                    "Spray Wettable Sulphur 80% WP at 3g/L or 3% neem oil emulsion in the late afternoon.",
                    "Rake up and destroy fallen infected leaves to stop spores from overwintering in the soil.",
                    "Avoid excessive nitrogen fertilizers which produce overly lush, disease-susceptible foliage."
                ]
                note = "If powdery coating persists, consult your local KVK expert for systemic fungicide recommendations."
            elif has_wilting_drying or has_root_rot:
                intro = f"Wilting or drying on your {crop_name_en} suggests vascular wilt (Fusarium/Pythium fungi) or root rot, often exacerbated by waterlogged soil conditions."
                actions = [
                    "Halt irrigation immediately and clear field drainage channels to facilitate rapid runoff.",
                    "Drench the collar and root zone with bio-fungicide Trichoderma viride or Pseudomonas fluorescens (10g to 20g per plant).",
                    "Incorporate well-cured neem cake (100-250g per plant) into the topsoil around the root circle to suppress soil pathogens.",
                    "Carefully remove dead or heavily rotting plants to restrict pathogen expansion in the soil."
                ]
                note = "Have your field soil tested at the nearest Agricultural Extension Office to check for pathogen saturation."
            elif has_pests:
                intro = f"Your {crop_name_en} is showing signs of caterpillar, borer, or pest infestation damaging foliar or stem tissues."
                actions = [
                    "Inspect crop rows during early morning hours and physically remove visible caterpillars and egg clusters.",
                    "Install pheromone traps and light traps across the field to monitor adult moth populations.",
                    "Spray bio-pesticide Bacillus thuringiensis (Bt at 2g/L) or 5% neem seed kernel extract (NSKE).",
                    "Rotate pesticide modes of action to prevent pest resistance and protect beneficial predatory insects."
                ]
                note = "If pest populations exceed the economic threshold level (ETL), seek guidance from your local agricultural extension officer."
            elif has_fertilizer or has_growth_issue:
                intro = f"Optimal nutrition is essential for vigorous vegetative growth and high yield in your {crop_name_en}. Nutrient imbalances can cause stunted development."
                actions = [
                    "Apply 10-15 kg of well-decomposed farmyard manure (FYM) or vermicompost around the drip line.",
                    "Foliar spray balanced water-soluble 19:19:19 (NPK) fertilizer at 5g per litre of water to spur active vegetative shoots.",
                    "Incorporate secondary and micronutrients such as Zinc Sulphate and Boron to prevent deficiency symptoms.",
                    "Maintain uniform soil moisture through mulching to enhance root nutrient uptake efficiency."
                ]
                note = "Obtain an official Soil Health Card from your local agriculture department to tailor fertilizer dosages precisely."
            elif has_weather_query or alerts:
                alert_text = alerts[0].get('message_en', 'Rain forecasted.') if alerts else ""
                intro = f"Agricultural Weather & Operational Advisory for your field{': ' + alert_text if alert_text else ''}."
                actions = [
                    "Postpone all chemical foliar spraying if rain (>60% probability) is forecast within 24-48 hours.",
                    "Execute spraying operations only during calm morning (7-10 AM) or late afternoon (4-6 PM) hours when wind is <20 km/h.",
                    "Ensure drainage ditches are clear to prevent water accumulation during sudden precipitation.",
                    "Add an agricultural surfactant/sticker to spray solutions during overcast weather to improve adherence."
                ]
                note = "Track local weather updates before scheduling costly agrochemical field applications."
            else:
                intro = f"General Agronomic Care & Protective Management for your {crop_name_en}."
                actions = [
                    "Maintain consistent soil moisture without surface water accumulation to protect feeder roots.",
                    "Incorporate organic vermicompost and balanced micronutrients to bolster natural plant resistance.",
                    "Inspect the undersides of leaves weekly to spot early signs of sucking pests or fungal infection.",
                    "Apply preventive 3% neem oil emulsion bi-weekly to maintain baseline biological protection."
                ]
                note = "For certified on-site diagnosis and soil testing, consult your local Krishi Vigyan Kendra (KVK)."

            lines = [intro, "", "**What to do now:**"]
            for act in actions:
                lines.append(f"- {act}")
            lines.append("")
            lines.append(f"**Note:** {note}")
            return "\n".join(lines)

    def answer(self, question: str, language: str = "en", context: dict = None) -> str:
        if not self.client:
            return self._generate_fallback_response(question, language, context)

        try:
            prompt_modifier = ""
            if language == "ta":
                prompt_modifier = (
                    "\nவிவசாயியின் கேள்விக்கு முழுமையான, நடைமுறை சார்ந்த விவசாய வழிகாட்டலை தமிழில் வழங்கவும். "
                    "தேவையற்ற முகவுரைகள் அல்லது வாழ்த்துக்கள் இன்றி நேரடியாக பதிலளிக்கவும். "
                    "சாத்தியமான காரணங்களை தெளிவாக விளக்கி, உடனடியாக செய்ய வேண்டிய நடைமுறை நடவடிக்கைகளை புல்லட் பாயிண்ட்களாகவும், "
                    "தேவையான முன்னெச்சரிக்கை மற்றும் KVK சரிபார்ப்புக் குறிப்பையும் தெளிவாகத் தரவும்."
                )
            elif language == "en":
                prompt_modifier = (
                    "\nProvide a complete, structured, and practical agricultural explanation in simple, farmer-friendly English. "
                    "Avoid unnecessary greetings or long introductory filler. Clearly explain the probable causes, provide immediate "
                    "practical action steps as clear bullet points, and include necessary precautions and KVK extension verification."
                )

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
        """
        Transcribes vernacular spoken audio using Sarvam AI Saaras v4 STT.
        Supports automatic Indian language identification and conversational code-mixing.
        """
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

        # Sarvam AI Saaras v4 STT
        if self.client:
            logger.info(f"Calling Sarvam STT (Saaras v4) with file: {filename}, size: {len(audio_bytes)} bytes, mime: {content_type}")
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

        raise RuntimeError("Sarvam AI STT client is not configured (SARVAM_API_KEY missing).")

    def text_to_speech(self, text: str, language_code: str = "ta-IN") -> str | None:
        """
        Synthesizes natural regional speech using Sarvam AI Bulbul v3 TTS.
        Returns base64 encoded audio string (WAV).
        """
        clean_text = self.clean_for_tts(text)

        # Sarvam AI Bulbul v3 TTS
        if self.client:
            try:
                valid_langs = ["ta-IN", "en-IN", "hi-IN", "te-IN", "kn-IN", "ml-IN", "mr-IN", "gu-IN", "bn-IN", "pa-IN", "od-IN"]
                tts_lang = language_code if language_code in valid_langs else "ta-IN"
                logger.info(f"Calling Sarvam TTS (Bulbul v3) ({tts_lang}, {len(clean_text)} chars)")
                response = self.client.text_to_speech.convert(
                    text=clean_text,
                    language_code=tts_lang,
                    model="bulbul:v3",
                    output_audio_codec="wav",
                )
                if response and response.audios and len(response.audios) > 0:
                    logger.info(f"Sarvam Bulbul TTS success ({len(response.audios[0])} base64 chars)")
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
