# 🌾 AgroNex (CropGuard AI) — Solution Pitch
**Autonomous Voice-First AI Copilot for Indian Farmers**  
*Built for the Great Indian AI Internship Challenge 2026 | Powered by Gnani AI

---

### 1. Problem Statement
Smallholder farmers across rural India lose **15% to 30% of their crop yields annually** due to delayed diagnosis of leaf diseases and ill-timed pesticide spraying. Furthermore, most existing agricultural apps are text-heavy and English-centric, creating a digital barrier for farmers who are working directly in fields with soiled hands and require hands-free, regional-language interaction.

### 2. The Solution: AgroNex
**AgroNex** is an autonomous, multimodal agricultural copilot that integrates:
1. **Computer Vision Disease Detection**: Instant leaf analysis (38 disease classes via EfficientNetV2-S ONNX) with blur and foliage quality gates.
2. **Real-time Micro-climate Weather Feed**: Live 24-hour and 7-day meteorological forecasts via Open-Meteo.
3. **Automated Spray Window Gate**: Automatically prevents wasteful chemical runoff by verifying if rainfall (>60% prob / >2mm) or high winds (>25 km/h) are impending.
4. **Voice-First Vernacular Interaction**: Fully powered by **Gnani AI** speech intelligence.

---

### 3. Gnani AI Voice Stack Integration
AgroNex uses Gnani AI's proprietary speech models to deliver a completely hands-free voice experience:
- **Speech-to-Text (Gnani Prisma v3.0)**:
  - Transcribes spoken farmer queries using automatic Indic language detection (`indic-auto`) and robust conversational code-mixing (e.g., Tamil, Hindi, Tanglish, Hinglish).
- **Text-to-Speech (Gnani Timbre v3.0)**:
  - Generates natural, expressive spoken audio advice in Indian languages using low-latency neural synthesis (voice: `Lakshmi` / `Shivani`), allowing farmers to hear diagnosis and spray advisories directly in the field.

---

### 4. Workflow Architecture
```
[Farmer Voice Query] ──► Gnani Prisma STT ──► AgroNex Intent Router
                                                     │
[Leaf Snapshot] ──────► ONNX Vision Gate ────────────┼──► Governed Agent Loop
[GPS Location] ───────► Open-Meteo Weather ──────────┤    (Spray Risk & Safety Rules)
                                                     │
[Spoken Guidance] ◄─── Gnani Timbre TTS ◄────────────┘
```

---

### 5. Real-World Impact
- **Financial Savings**: Prevents expensive chemical pesticide wastage by warning farmers before rainfall washes treatments away.
- **Vernacular Inclusivity**: Eliminates language and literacy barriers for farmers in Tier-2, Tier-3, and rural communities.
- **Offline Resilience**: Operates with graceful local fallbacks ensuring continuous advisory even in low-bandwidth rural zones.

---
**Repository**: [github.com/DHANUSH-PRO11/CropGuard-AI](https://github.com/DHANUSH-PRO11/CropGuard-AI)  
**Developer**: Dhanush G | Built for Gnani AI Great Indian AI Internship Challenge 2026

