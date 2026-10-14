from typing import Optional, List
import os
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from supabase import Client
from config.database import get_supabase
from schemas import schemas
from services.ai.disease_detector import DiseaseDetector
from datetime import datetime
from PIL import Image

logger = logging.getLogger(__name__)

router = APIRouter()
detector = DiseaseDetector()

@router.post("/analyze", response_model=schemas.CropAnalysisResponse)
async def analyze_crop(
    file: UploadFile = File(...),
    mode: str = Form("direct"),
    enable_tta: bool = Form(False),
    db: Optional[Client] = Depends(get_supabase)
):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")
        
    # Save the file temporarily
    os.makedirs("uploads", exist_ok=True)
    filename = os.path.basename(file.filename or "leaf.jpg")
    file_path = f"uploads/{filename}"
    file_bytes = await file.read()
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)
        
    try:
        img = Image.open(file_path)
        img_width, img_height = img.size
    except Exception as e:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")
        
    file_size_kb = len(file_bytes) / 1024
    
    logger.info(f"Analyzing crop image: {filename} ({img_width}x{img_height}, {file_size_kb:.1f} KB, mode: {mode}, tta: {enable_tta})")
    
    # Use AI service
    try:
        prediction = detector.predict(file_path, preprocessing_mode=mode, enable_tta=enable_tta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop analysis failed: {str(e)}")
        
    public_url = None
    if db is not None:
        try:
            # Upload to Supabase Storage
            file_name_in_storage = f"{int(datetime.utcnow().timestamp())}_{filename}"
            with open(file_path, "rb") as f:
                res = db.storage.from_("crop-images").upload(file_name_in_storage, f.read(), {"content-type": file.content_type})
                
            public_url = db.storage.from_("crop-images").get_public_url(file_name_in_storage)
            
            # Save to database
            db_record = {
                "crop_type": prediction.get("crop", "Unknown"),
                "image_path": public_url,
                "detected_disease": prediction.get("condition", "Unknown"),
                "confidence": float(prediction.get("confidence", 0.0)),
                "severity": prediction.get("severity", "Not determined"),
                "risk_level": prediction.get("risk", "Not determined")
            }
            
            db.table("crop_analyses").insert(db_record).execute()
            logger.info("Crop analysis record saved to Supabase.")
        except Exception as e:
            logger.warning(f"Failed to save crop analysis to Supabase: {str(e)}")
    else:
        logger.info("Supabase not configured; analysis completed in local memory mode.")
    
    # Optionally remove local file
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    
    return prediction

@router.get("/history", response_model=List[schemas.CropAnalysisResponse])
def get_crop_history(db: Optional[Client] = Depends(get_supabase)):
    """Retrieve history of saved crop analyses from Supabase."""
    if db is None:
        return []
    try:
        res = db.table("crop_analyses").select("*").order("created_at", desc=True).limit(20).execute()
        records = []
        for row in res.data or []:
            records.append({
                "crop": row.get("crop_type", "Unknown"),
                "condition": row.get("detected_disease", "Unknown"),
                "confidence": float(row.get("confidence", 0.0)),
                "is_healthy": "healthy" in row.get("detected_disease", "").lower(),
                "status": "High confidence" if float(row.get("confidence", 0.0)) >= 0.7 else "Uncertain",
                "top_predictions": [],
                "severity": row.get("severity", "Not determined"),
                "risk": row.get("risk_level", "Not determined"),
                "quality_status": "Passed",
                "warning_message": None,
                "uncertainty_reason": None,
                "latency_ms": None,
                "preprocessing_mode": "direct",
                "tta_enabled": False
            })
        return records
    except Exception as e:
        logger.warning(f"Failed to fetch history from Supabase: {e}")
        return []



