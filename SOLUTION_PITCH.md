 🌾 AgroNex: Autonomous Vernacular Voice Copilot for Indian Farmers

Hands-free multimodal agricultural advisory fusing real-time computer vision disease detection, live micro-climate spray windows, and Gnani AI speech intelligence in regional languages.



1. Problem Statement
Over 140 million Indian smallholder farmers lose "15% to 30% of their crop yields annually" due to delayed foliar disease identification and pesticide spray run-off caused by unpredictable weather. Existing agricultural platforms rely on complex, text-heavy English interfaces that are impractical for farmers working in dusty fields with soiled hands. There is a critical lack of voice-first, code-mixed regional tools that integrate instant visual crop diagnostics with grounded meteorological risk safety.

2. Proposed Solution & Core Workflow
AgroNex delivers an autonomous, voice-driven agricultural copilot built specifically for rural and Tier-2/3 farming communities. A farmer snaps a photo of an infected leaf and speaks a query in Tamil, Hindi, or conversational code-mix (e.g., Tanglish/Hinglish). AgroNex transcribes the audio via "Gnani Prisma v3.0 STT", validates leaf quality, executes ONNX neural disease inference, and pulls live Open-Meteo forecasts to enforce spray safety windows (blocking sprays if rain >60% or winds >25 km/h). The synthesized, safe advisory is then read aloud in natural regional speech using "Gnani Timbre v3.0 TTS".

3. Architecture & Tech Stack
Frontend / UI:
 React 19, Vite, Tailwind CSS v4, Lucide Icons, bilingual i18n (Tamil & English), responsive mobile-first PWA design.
Backend & Services:
 FastAPI (Python 3.11/3.12), RESTful endpoints, asynchronous streaming, Uvicorn ASGI server.
- **AI / Speech / ML Models**:
  - **Gnani AI Prisma v3.0 STT**: Automatic Indic language detection (`indic-auto`) and conversational code-mix speech transcription.
  - **Gnani AI Timbre v3.0 TTS**: Neural speech synthesis for regional audio playback (`Lakshmi` voice).
  - **EfficientNetV2-S (ONNX Runtime)**: 38-class PlantVillage crop disease classifier with Laplacian blur and foliage quality gates.
  - **Agricultural Knowledge Reasoner**: Grounded anti-hallucination recommendation engine with PM-KISAN subsidy matching.
- **Data & Integrations**: Open-Meteo Micro-climate API, Supabase Cloud Storage & Postgres with zero-setup resilient local SQLite fallback.

### 4. Key Features & Novelty
- **Voice-First Vernacular Inclusion**: Hands-free voice interface tailored for farmers in regional dialects and code-mixes using Gnani AI's proprietary speech models.
- **Automated Weather Spray Safety Gate**: Prevents expensive pesticide wastage and chemical run-off by checking real-time rainfall and wind thresholds before advising sprays.
- **Uncertainty & Quality Gatekeeping**: Eliminates hallucinations by rejecting blurry/non-foliage photos and flagging predictions below 60% confidence for KVK extension officer review.
- **Offline & Low-Bandwidth Resilience**: Seamlessly operates with local SQLite caching when network connectivity drops in remote fields.

### 5. Setup & Execution
```bash
# 1. Backend Setup & Run (Terminal 1)
pip install -r backend/requirements.txt
echo "GNANI_API_KEY=your_gnani_key" > backend/.env
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend

# 2. Frontend Setup & Run (Terminal 2)
npm install --prefix frontend && npm run dev --prefix frontend
# Access at: http://localhost:5173
```
