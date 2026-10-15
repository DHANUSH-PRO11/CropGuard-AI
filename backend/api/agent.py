"""
FastAPI Router for AgroNex Agent — Agricultural Copilot Endpoints
"""

import io
import json
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client
from PIL import Image

from config.database import get_supabase
from services.agent.agronex_agent import AgroNexAgent

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB maximum upload limit

router = APIRouter(prefix="/api/agent", tags=["AgroNex Agent"])
agent = AgroNexAgent()

class AgentChatRequest(BaseModel):
    message: str
    language: Optional[str] = "en"
    crop_hint: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    context: Optional[dict] = None

@router.post("/run")
async def run_agent_workflow(
    query: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    crop_hint: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    language: Optional[str] = Form("en"),
    context: Optional[str] = Form(None),
    db: Optional[Client] = Depends(get_supabase)
):
    """
    Multimodal entrypoint for AgroNex Agent.
    Accepts text queries, plant leaf images, farmer voice audio, coordinates, and context.
    Runs the 10-step AgentFoundry workflow.
    """
    image_bytes = None
    image_filename = None
    if image is not None:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Provided file is not an image.")
        image_bytes = await image.read()
        if len(image_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Image file exceeds maximum allowed size of 10 MB.")
        try:
            with Image.open(io.BytesIO(image_bytes)) as img_check:
                img_check.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Provided file is not a valid or supported image.")
        image_filename = image.filename

    audio_bytes = None
    audio_filename = None
    if audio is not None:
        audio_bytes = await audio.read()
        if len(audio_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Audio file exceeds maximum allowed size of 10 MB.")
        audio_filename = audio.filename

    parsed_context = None
    if context:
        try:
            parsed_context = json.loads(context)
        except Exception:
            parsed_context = {"raw_context": context}

    result = agent.run(
        query=query,
        image_bytes=image_bytes,
        image_filename=image_filename,
        audio_bytes=audio_bytes,
        audio_filename=audio_filename,
        crop_hint=crop_hint,
        latitude=latitude,
        longitude=longitude,
        language=language or "en",
        db_client=db,
        context=parsed_context
    )
    return result

@router.post("/chat")
def run_agent_chat(
    req: AgentChatRequest,
    db: Optional[Client] = Depends(get_supabase)
):
    """
    Fast JSON chat entrypoint for text queries with weather and context grounding.
    """
    result = agent.run(
        query=req.message,
        crop_hint=req.crop_hint,
        latitude=req.latitude,
        longitude=req.longitude,
        language=req.language or "en",
        db_client=db,
        context=req.context
    )
    return result

@router.get("/workflow")
def get_workflow_manifest():
    """
    Returns the AgentFoundry workflow metadata and current node specification.
    """
    return {
        "workflow_id": "agronex-farming-copilot",
        "name": "AgroNex Agent — Autonomous Agricultural Copilot",
        "version": "1.0.0",
        "platform": "AgentFoundry / Code for a Billion",
        "nodes": [
            {"id": "input_ingestion", "type": "multimodal_input_gate", "tools": ["sarvam_stt"]},
            {"id": "intent_routing", "type": "conditional_router", "tools": []},
            {"id": "disease_detection", "type": "vision_inference", "tools": ["efficientnet_v2_onnx", "quality_gatekeeper"]},
            {"id": "weather_lookup", "type": "meteorological_feed", "tools": ["open_meteo_api", "weather_alert_rules"]},
            {"id": "schemes_provider", "type": "knowledge_retrieval", "tools": ["government_schemes_database"]},
            {"id": "context_assembly", "type": "grounding_synthesizer", "tools": ["spray_window_evaluator"]},
            {"id": "agricultural_reasoning", "type": "llm_copilot", "tools": ["sarvam_105b_conversations"]},
            {"id": "voice_synthesis", "type": "audio_generator", "tools": ["sarvam_bulbul_v3"]},
            {"id": "persistence", "type": "cloud_storage", "tools": ["supabase_postgres", "supabase_storage", "local_sqlite"]}
        ],
        "languages": ["ta", "en", "code-mix"],
        "safety_boundaries": [
            "No hallucinated weather or disease conditions",
            "Spray postponement alert if rain > 60%",
            "Human agronomist verification required if confidence < 60%"
        ]
    }
