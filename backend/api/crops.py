from typing import Optional, List
import os
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from supabase import Client
from config.database import get_supabase
from config import local_db
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
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds maximum allowed size of 10 MB.")
    
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
    saved_to_supabase = False
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
            saved_to_supabase = True
            logger.info("Crop analysis record saved to Supabase.")
        except Exception as e:
            logger.warning(f"Failed to save crop analysis to Supabase: {str(e)}")

    # Always save to local fallback db as well for offline resilience
    try:
        local_db.save_crop_analysis({
            "crop_type": prediction.get("crop", "Unknown"),
            "image_path": public_url or file_path,
            "detected_disease": prediction.get("condition", "Unknown"),
            "confidence": float(prediction.get("confidence", 0.0)),
            "severity": prediction.get("severity", "Not determined"),
            "risk_level": prediction.get("risk", "Not determined")
        })
    except Exception as e:
        logger.warning(f"Failed to save to local db: {e}")
    
    # Optionally remove local file
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    
    return prediction

@router.get("/history", response_model=List[schemas.CropAnalysisResponse])
def get_crop_history(db: Optional[Client] = Depends(get_supabase)):
    """Retrieve history of saved crop analyses from Supabase or local fallback database."""
    records = []
    if db is not None:
        try:
            res = db.table("crop_analyses").select("*").order("created_at", desc=True).limit(50).execute()
            for row in res.data or []:
                records.append({
                    "id": str(row.get("id")) if row.get("id") else None,
                    "created_at": row.get("created_at"),
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
            if records:
                return records
        except Exception as e:
            logger.warning(f"Failed to fetch history from Supabase: {e}")

    # Fallback to local DB history
    try:
        local_records = local_db.get_recent_crop_analyses(limit=50)
        for row in local_records:
            records.append({
                "id": str(row.get("id")) if row.get("id") else None,
                "created_at": row.get("created_at"),
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
    except Exception as e:
        logger.warning(f"Failed to fetch local crop history: {e}")

    return records

@router.delete("/history/{record_id}")
def delete_crop_history_record(record_id: str, db: Optional[Client] = Depends(get_supabase)):
    """Deletes a specific crop diagnosis history record."""
    deleted = False
    if db is not None:
        try:
            db.table("crop_analyses").delete().eq("id", record_id).execute()
            deleted = True
        except Exception as e:
            logger.warning(f"Failed to delete record from Supabase: {e}")
    
    local_deleted = local_db.delete_crop_analysis(record_id)
    if not deleted and not local_deleted:
        raise HTTPException(status_code=404, detail="Analysis record not found.")
    return {"success": True, "message": "Record deleted successfully"}




