# 🌾 AgroNex Project Verification, Bug Fixing & Testing Report

**Date of Verification:** October 14, 2026  
**Auditor:** Antigravity Senior Software Engineer & QA Lead  
**Corpus / Repository:** `DHANUSH-PRO11/CropGuard-AI` (`g:\Agri-ai`)  
**Workflow Engine:** AgentFoundry Autonomous Multimodal Copilot (`agronex-farming-copilot`)  

---

## 1. Project Structure & Technologies Inspected

### Architecture Stack
- **Frontend Framework:** React 19.2 + Vite 8.3 + Tailwind CSS v4 Single Page App (SPA)
- **Internationalization:** i18next (Tamil `ta` & English `en`)
- **Backend Framework:** Python 3.14 + FastAPI 0.141 + Uvicorn 0.54
- **Computer Vision Inference:** ONNX Runtime 1.30 (`efficientnet_v2_s_best.onnx` ~80 MB), 38 PlantVillage pathology classes, EXIF transpositions, discrete Laplacian focus variance, luminance clipping, Test-Time Augmentation (TTA).
- **AI Agent & LLM Services:** Sarvam AI SDK (`sarvam-105b-conversations` reasoner, `saaras:v4` bilingual STT, `bulbul:v3` bilingual TTS).
- **Weather Feed:** Open-Meteo live API (24h hourly forecast, 7-day outlook, WMO meteorological codes, spray window rule engine).
- **Databases & Storage:** Supabase Cloud (PostgreSQL + S3 Storage) with SQLite (`backend/agronex.db`) offline fallback.
- **Authentication:** Custom JWT (PBKDF2-HMAC-SHA256 salted password hashing) + Google OAuth 2.0 Identity Services.
- **Orchestration & Deploy:** Docker Compose (`backend` + `frontend` Nginx), Render Blueprint (`render.yaml`), Vercel (`vercel.json`), Windows launcher (`start.bat`).

---

## 2. Features & User Journeys Verified

| Feature / User Journey | Expected Outcome | Verification Status | Evidence / Verification Notes |
| :--- | :--- | :--- | :--- |
| **1. Service Health & API Discovery** | `/health` returns `{status: "ok"}` and root `/` returns welcome message | **PASS** | Validated via `TestAgroNexAPIEndpoints.test_01_health_and_root`. Status 200 returned. |
| **2. Farmer Registration & Login** | Register unique mobile/email, hash password with PBKDF2 salt, issue JWT, authenticate `/api/auth/me` | **PASS** | Tested in `test_02_auth_registration_and_validation`, `test_03_auth_login_flow`, and `test_12_auth_login_with_email`. |
| **3. Farmer Profile CRUD** | Retrieve and update farm size, primary crops, and location | **PASS** | Verified with `test_04_farmer_profile_get_and_update`. Profile updates persist in local SQLite. |
| **4. Government Schemes & Subsidies** | Filter PM-KISAN, PMFBY, KCC, micro-irrigation schemes in Tamil & English | **PASS** | Verified with `test_05_schemes_endpoint`. Query parameter search matches accurately. |
| **5. Live Open-Meteo Weather Radar** | Fetch 24h hourly and 7-day forecast with spray alerts for Tamil Nadu coordinates | **PASS** | Verified with `test_06_weather_forecast_endpoint`. Open-Meteo returned 200 with hourly and current feeds. |
| **6. Computer Vision Disease Detection** | 12 preprocessing checks (normal, RGBA alpha, EXIF rotation, blur, low light, overexposure, non-leaf foliage, confidence thresholding, TTA) | **PASS** | Validated via `backend/test_model.py`. 12/12 scenarios passed, plus 4 repository sample images evaluated. |
| **7. Crop Health Analysis API** | POST `/api/crops/analyze` with leaf image | **PASS** | Preprocessing, ONNX inference, and database persistence completed in ~43ms. |
| **8. AgentFoundry Manifest** | GET `/api/agent/workflow` returns 10-node copilot specification | **PASS** | Verified with `test_08_agent_workflow_manifest`. Manifest matches YAML workflow specifications. |
| **9. Autonomous Copilot Chat** | POST `/api/agent/chat` generates grounded agronomic advice | **PASS** | Validated in `test_09_agent_chat_endpoint` and `test_10_agent_chat_with_diagnostic_context`. |
| **10. Multimodal Copilot Follow-up with Context** | Ask "Should I spray today?" after diagnosis; evaluates diagnosis + weather constraint | **PASS** | Context reuse verified. Generates `spray_advisory` and reuses diagnostic context. |
| **11. Offline Resilience & Persistence** | Operate with zero cloud credentials; fall back to local SQLite | **PASS** | Tested with `test_11_local_db_chat_persistence`. Records stored and retrieved from `agronex.db`. |
| **12. Frontend Production Bundling** | Vite builds without errors, transforms React 19 JSX and Tailwind v4 CSS | **PASS** | `npm run build` completed in 4.36s (`dist/index.html`, `dist/assets/`). |
| **13. Frontend Code Quality & Linting** | Oxlint scan across 20 frontend components and pages | **PASS** | 0 errors found across entire codebase. |
| **14. Live Microphone & STT Ingestion** | Record voice audio in browser, send 16kHz mono PCM WAV to Sarvam Saaras v4 | **BLOCKED** | Sarvam AI API returned HTTP 402 `insufficient_quota_error` ("No credits available"). Handled with deterministic fallback. |
| **15. Speech Synthesis (Bulbul v3 TTS)** | Convert generated response to natural spoken Tamil/English audio | **BLOCKED** | Sarvam AI API returned HTTP 402 `insufficient_quota_error`. Gracefully handled with null audio fallback. |
| **16. Google OAuth Live Login** | Real Google OAuth Sign-In button interaction | **BLOCKED** | `VITE_GOOGLE_CLIENT_ID` not configured in `.env`. Google OAuth Component displays guided notice. |

---

## 3. Issues Found, Severity & Affected Files

| Issue ID | Severity | File Affected | Description | Status |
| :--- | :--- | :--- | :--- | :--- |
| **ISSUE-01** | **High** | `frontend/src/pages/Login.jsx` | When registering with an email address, `mobile` was hardcoded to `'9876543210'`. The second user attempting to register with an email was blocked with `400 Bad Request: A user with this mobile number already exists`. | **FIXED** |
| **ISSUE-02** | **High** | `backend/api/agent.py`<br/>`backend/services/agent/agronex_agent.py` | In `/result`, clicking Copilot prompt pills ("Should I spray today?") sent `context: { crop, condition }`. However, `backend/api/agent.py` dropped `context`, and `AgroNexAgent.run()` did not accept it. The agent had no diagnosis data. | **FIXED** |
| **ISSUE-03** | **Medium** | `backend/config/local_db.py`<br/>`backend/services/agent/agronex_agent.py` | `local_db` initialized `chat_history` table, but lacked helper functions `save_chat_message` and `get_recent_chat_history`. Conversations were never persisted offline in `agronex.db`. | **FIXED** |
| **ISSUE-04** | **Medium** | `frontend/src/components/WeatherAlerts.jsx`<br/>`frontend/src/hooks/useLocation.js` | Direct call to `navigator.geolocation` failed on browsers where geolocation was blocked or unavailable, displaying an error banner. If geolocation was unsupported, `useLocation` never provided a default location. | **FIXED** |
| **ISSUE-05** | **Medium** | `frontend/src/pages/Result.jsx` | `top_predictions` was destructured but never displayed in the UI, suppressing differential diagnoses from farmers and triggering linter warnings. | **FIXED** |
| **ISSUE-06** | **Low** | `frontend/src/pages/Weather.jsx`<br/>`frontend/src/components/LocationWeatherCard.jsx` | Unused icon imports (`Sunrise`, `Sunset`, `RefreshCw`). `LocationWeatherCard` lacked an in-place retry button when network failed. `Weather.jsx` ignored location errors. | **FIXED** |
| **ISSUE-07** | **Critical** | `backend/requirements.txt`<br/>`.github/workflows/ci-cd.yml` | GitHub Actions CI failed in Backend Unit Tests (Step 6) because `fastapi.testclient.TestClient` requires `httpx`, which was omitted from `backend/requirements.txt`, throwing `RuntimeError: The starlette.testclient module requires the httpx package`. | **FIXED** |
| **ISSUE-08** | **Medium** | `frontend/src/hooks/useLocation.js`<br/>`frontend/src/components/LocationWeatherCard.jsx`<br/>`frontend/src/components/WeatherAlerts.jsx`<br/>`frontend/src/pages/Assistant.jsx`<br/>`frontend/src/pages/CropCheck.jsx`<br/>`frontend/src/pages/Dashboard.jsx` | 23 frontend linter annotations in CI: unused imports (`MapPin`, `Upload`, `Leaf`, `Sparkles`), temporal dead zone in `useLocation.js`, cascading `react(set-state-in-effect)`, and impure function calls in renders. | **FIXED** |

---

## 4. Fixes Implemented

### 1. Fix for Registration Collision (`Login.jsx`)
- Introduced dedicated input fields on the registration form for **Full Name**, **Mobile Number (10 digits)**, and **Email Address (Optional)**.
- Ensured registration payloads send clean, user-provided mobile numbers and optional lowercase emails, eliminating duplicate `'9876543210'` collisions.
- Preserved single-input convenience ("Mobile Number or Email") for the Login view.

### 2. Context-Aware Autonomous Copilot (`agronex_agent.py` & `api/agent.py`)
- Added `context: Optional[Dict[str, Any]] = None` parameter to `AgroNexAgent.run()`.
- Added logic in Node 2 (Intent Classification) and Node 3 (Disease Detection) to reuse prior diagnostic context (`crop`, `condition`, `confidence`, `status`, `quality_status`) when text follow-up queries are made without re-uploading an image.
- Updated `POST /api/agent/chat` and `POST /api/agent/run` in `backend/api/agent.py` to parse and forward `context`.

### 3. Local Offline Chat & Diagnosis Persistence (`local_db.py`)
- Implemented `save_chat_message(role, message, user_id=None)` and `get_recent_chat_history(user_id=None, limit=20)` in `backend/config/local_db.py`.
- Updated Node 8 in `agronex_agent.py` to persist crop analysis and user/agent chat messages to `local_db` whenever Supabase credentials are absent or fail.

### 4. Resilient Weather Alerts & Geolocation (`WeatherAlerts.jsx` & `useLocation.js`)
- Refactored `WeatherAlerts.jsx` to use the unified `useLocation()` hook.
- Added automatic fallback to regional agricultural center coordinates (Coimbatore, Tamil Nadu: `11.0168, 76.9558`) if geolocation is blocked, denied, or unsupported by the browser.
- Added in-place refresh buttons and loading spinners for seamless offline-to-online recovery.

### 5. Differential Diagnoses Section (`Result.jsx`)
- Added an **Alternative Possibilities / Differential Diagnoses** card in `Result.jsx`.
- Renders ranked top-3 alternative conditions with percentage confidence match, helping farmers and agricultural extension officers assess ambiguous symptoms.

### 6. Component Clean-up & UX Enhancements (`Weather.jsx`, `Assistant.jsx`, `LocationWeatherCard.jsx`)
- Removed dead imports (`Sunrise`, `Sunset`).
- Wired `cameraActive` state in `Assistant.jsx` to display a loading spinner while the camera video feed initializes.
- Added an in-place retry button in `LocationWeatherCard.jsx` for graceful network error recovery.

---

## 5. Automated Tests Executed & Results

### 1. Backend Test Suite (`python -m unittest discover -s tests`)
```
Ran 18 tests in 18.434s
Status: OK (18/18 Passed)
```
- `test_01_health_and_root`: Health check and root route verification [PASS]
- `test_02_auth_registration_and_validation`: Password length, mobile uniqueness, registration [PASS]
- `test_03_auth_login_flow`: Incorrect credentials rejection, JWT issuance, `/api/auth/me` [PASS]
- `test_04_farmer_profile_get_and_update`: Profile reading and updates [PASS]
- `test_05_schemes_endpoint`: PM-KISAN, PMFBY, and Tamil Nadu subsidy retrieval and search [PASS]
- `test_06_weather_forecast_endpoint`: Open-Meteo live forecast parsing [PASS]
- `test_07_crop_history_endpoint`: Recent crop diagnoses history [PASS]
- `test_08_agent_workflow_manifest`: 10-node AgentFoundry manifest [PASS]
- `test_09_agent_chat_endpoint`: Basic text copilot query [PASS]
- `test_10_agent_chat_with_diagnostic_context`: Context-grounded follow-up query [PASS]
- `test_11_local_db_chat_persistence`: Offline chat persistence in SQLite [PASS]
- `test_12_auth_login_with_email`: Registration and login with email identifier [PASS]
- 6 AgentFoundry integration tests (`test_agent_workflow.py`): Input Ingestion, Intent Routing, Vision Inference, Meteorological Feed, Context Assembly, Uncertainty Gate [PASS]

### 2. Computer Vision Preprocessing Suite (`python test_model.py`)
```
Status: OK (12/12 Scenarios Passed)
Average Single-View Latency: ~58.1 ms
Average TTA Latency: ~105.6 ms
```
- [TEST 1/12] Normal RGB Image: Cherry - healthy (Quality: Passed) [PASS]
- [TEST 2/12] RGBA Transparent Image: Alpha composited over neutral background [PASS]
- [TEST 3/12] EXIF Rotated Image: Transposed (180, 320) successfully [PASS]
- [TEST 4/12] Rectangular Aspect Ratio Comparison: Direct & letterbox modes [PASS]
- [TEST 5/12] Very Small Image (64x64): Warning: Low Resolution flagged [PASS]
- [TEST 6/12] Blurry Image: Warning: Mild Blur flagged [PASS]
- [TEST 7/12] Dark / Underexposed Image: Warning: Low Light flagged [PASS]
- [TEST 8/12] Overexposed Image: Warning: Overexposed flagged [PASS]
- [TEST 9/12] Non-Leaf Image: Warning: Low Foliage flagged [PASS]
- [TEST 10/12] Model Confidence Uncertainty Check: Status Uncertain flagged [PASS]
- [TEST 11/12] Batch Softmax Numerical Stability: Max absolute difference = 0.0 [PASS]
- [TEST 12/12] Test-Time Augmentation (TTA) Benchmark: Verified [PASS]

### 3. Frontend Production Build (`npm run build`)
```
vite v8.3.2 building client environment for production...
transforming...
✓ 2355 modules transformed.
dist/index.html                   0.99 kB │ gzip:   0.56 kB
dist/assets/index-BulzKCMk.css   74.41 kB │ gzip:  12.12 kB
dist/assets/index-mcg31rX5.js   557.67 kB │ gzip: 170.34 kB
✓ built in 4.36s
Status: PASS (0 Errors)
```

### 4. Frontend Linter (`npm run lint`)
```
oxlint v1.81.0
20 files scanned with 104 rules.
Status: PASS (0 Warnings, 0 Errors across 20 files)
```

---

## 6. Security & Best Practices Verification

| Check | Status | Findings |
| :--- | :--- | :--- |
| **Hardcoded Secrets** | **PASS** | No private API keys or database passwords committed to version control. Keys read from `.env`. |
| **Password Hashing** | **PASS** | Secure PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte random salt per user. |
| **JWT Verification** | **PASS** | Tokens signed with HS256, expiration dates enforced, validated on protected routes (`/api/auth/me`). |
| **Safe File Uploads** | **PASS** | `api/crops.py` and `api/agent.py` validate MIME type (`image/*`), check PIL decodability, and clean temp files in `finally` blocks. |
| **SQL Injection** | **PASS** | SQLite queries in `local_db.py` use parameterized placeholders (`?`) exclusively. |
| **CORS Configuration** | **PASS** | Explicit origin allowlisting configured in `main.py` via `FRONTEND_URL` and `ALLOW_ALL_ORIGINS`. |

---

## 7. Features That Remain Incomplete or Unverified

1. **Sarvam AI Live Credits (Quota Exhausted):**  
   - **Status:** **BLOCKED**  
   - **Reason:** The configured `SARVAM_API_KEY` returned HTTP 402 `insufficient_quota_error` ("No credits available").  
   - **Mitigation:** The application includes deterministic, prompt-grounded fallback reasoning for Tamil and English that activates seamlessly. To enable live Sarvam-105B LLM generation and Bulbul v3 TTS voice audio, recharge or replace the Sarvam API key in `.env`.

2. **Google OAuth Production Client ID:**  
   - **Status:** **BLOCKED**  
   - **Reason:** `VITE_GOOGLE_CLIENT_ID` in `frontend/.env` is currently unconfigured (`your_google_oauth_client_id_here`).  
   - **Mitigation:** The frontend displays an informational notice and allows full access via standard registration/login without crashing.

3. **Supabase Cloud Credentials:**  
   - **Status:** **PASS (Local Fallback Verified)**  
   - **Reason:** Live Supabase cloud credentials are optional. Zero-setup SQLite (`backend/agronex.db`) provides full local persistence.

---

## 8. Summary Checklist Before Deployment

- [x] All 18 automated backend tests pass.
- [x] All 12 computer vision preprocessing and TTA benchmarks pass.
- [x] Frontend builds cleanly with Vite into `frontend/dist/`.
- [x] Registration collision bug fixed.
- [x] Copilot follow-up context forwarding fixed.
- [x] Weather alert geolocation fallback verified.
- [x] Differential diagnosis UI implemented.
- [ ] Add active credits to `SARVAM_API_KEY` in `backend/.env` for live voice STT & TTS.
- [ ] Set `VITE_GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_ID` in production environment.
- [ ] Run `docker compose up --build` or deploy using `render.yaml` / `vercel.json`.
