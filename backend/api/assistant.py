from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from typing import Optional
from schemas import schemas
from services.ai.ai_assistant import AIAssistant

router = APIRouter()
assistant = AIAssistant()

import json
@router.post("/chat", response_model=schemas.ChatResponse)
def chat(message: schemas.ChatMessage):
    try:
        lang = message.language or "en"
        reply = assistant.answer(message.message, lang, context=message.context)
        audio_base64 = assistant.text_to_speech(reply, language_code="ta-IN" if lang == "ta" else "en-IN")
        return {"reply": reply, "audio_base64": audio_base64}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice", response_model=schemas.VoiceChatResponse)
async def voice_chat(
    file: UploadFile = File(...),
    language: Optional[str] = Form("ta"),
    context: Optional[str] = Form(None)
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
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
