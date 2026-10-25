import json
import logging
from typing import Optional, List
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Depends
from supabase import Client
from schemas import schemas
from services.ai.ai_assistant import AIAssistant
from config.database import get_supabase
from config import local_db

logger = logging.getLogger(__name__)

router = APIRouter()
assistant = AIAssistant()

@router.post("/chat", response_model=schemas.ChatResponse)
def chat(message: schemas.ChatMessage, db: Optional[Client] = Depends(get_supabase)):
    try:
        lang = message.language or "en"
        reply = assistant.answer(message.message, lang, context=message.context)
        audio_base64 = assistant.text_to_speech(reply, language_code="ta-IN" if lang == "ta" else "en-IN")

        # Save to Supabase if configured
        if db is not None:
            try:
                db.table("chat_history").insert([
                    {"role": "user", "message": message.message},
                    {"role": "ai", "message": reply}
                ]).execute()
            except Exception as e:
                logger.warning(f"Supabase chat save failed: {e}")

        # Always save to local_db for offline resilience
        try:
            local_db.save_chat_message("user", message.message)
            local_db.save_chat_message("ai", reply)
        except Exception as e:
            logger.warning(f"Local db chat save failed: {e}")

        return {"reply": reply, "audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice", response_model=schemas.VoiceChatResponse)
async def voice_chat(
    file: UploadFile = File(...),
    language: Optional[str] = Form("ta"),
    context: Optional[str] = Form(None),
    db: Optional[Client] = Depends(get_supabase)
):
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file received")
        if len(audio_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio file exceeds maximum allowed size of 10 MB.")

        filename = file.filename or "recording.webm"
        if "." not in filename:
            ct = file.content_type or ""
            if "wav" in ct:
                filename = f"{filename}.wav"
            elif "mp4" in ct:
                filename = f"{filename}.mp4"
            elif "ogg" in ct:
                filename = f"{filename}.ogg"
            else:
                filename = f"{filename}.webm"

        parsed_context = None
        if context:
            try:
                parsed_context = json.loads(context)
            except Exception:
                parsed_context = {"raw_context": context}

        result = assistant.process_voice_chat(
            audio_bytes=audio_bytes,
            filename=filename,
            preferred_language=language or "ta",
            content_type=file.content_type or "audio/wav",
            context=parsed_context
        )

        user_text = result.get("transcription") or "Farmer Voice Query"
        reply_text = result.get("reply") or ""

        # Persist conversation
        if db is not None:
            try:
                db.table("chat_history").insert([
                    {"role": "user", "message": user_text},
                    {"role": "ai", "message": reply_text}
                ]).execute()
            except Exception as e:
                logger.warning(f"Supabase chat save failed: {e}")

        try:
            local_db.save_chat_message("user", user_text)
            local_db.save_chat_message("ai", reply_text)
        except Exception as e:
            logger.warning(f"Local db chat save failed: {e}")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[schemas.ChatHistoryItem])
def get_chat_history(limit: int = 50, db: Optional[Client] = Depends(get_supabase)):
    """Retrieve recent chat history from Supabase or local SQLite fallback."""
    records = []
    if db is not None:
        try:
            res = db.table("chat_history").select("*").order("created_at", desc=True).limit(limit).execute()
            for row in res.data or []:
                records.append({
                    "id": str(row.get("id")),
                    "role": row.get("role", "user"),
                    "message": row.get("message", ""),
                    "created_at": row.get("created_at", "")
                })
            if records:
                return records
        except Exception as e:
            logger.warning(f"Supabase chat history query failed: {e}")

    try:
        local_records = local_db.get_recent_chat_history(limit=limit)
        for row in local_records:
            records.append({
                "id": str(row.get("id")),
                "role": row.get("role", "user"),
                "message": row.get("message", ""),
                "created_at": row.get("created_at", "")
            })
    except Exception as e:
        logger.warning(f"Local db chat history query failed: {e}")

    return records

@router.delete("/history")
def clear_history(db: Optional[Client] = Depends(get_supabase)):
    """Clears conversational chat history."""
    if db is not None:
        try:
            db.table("chat_history").delete().neq("id", "0").execute()
        except Exception as e:
            logger.warning(f"Supabase chat history clear failed: {e}")

    local_db.clear_chat_history()
    return {"success": True, "message": "Chat history cleared successfully"}

