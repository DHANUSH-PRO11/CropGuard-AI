import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header
from supabase import Client
from config.database import get_supabase
from config import local_db
from schemas import schemas
from api.auth import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=schemas.FarmerProfileResponse)
def get_profile(
    authorization: Optional[str] = Header(None),
    db: Optional[Client] = Depends(get_supabase)
):
    """Retrieves farmer profile information from Supabase or local persistent database."""
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization.split(" ", 1)[1])
        if payload:
            user_id = payload.get("sub")

    # 1. Supabase branch if configured
    if db is not None:
        try:
            query = db.table("farmer_profiles").select("*")
            if user_id:
                query = query.eq("user_id", user_id)
            res = query.order("created_at", desc=True).limit(1).execute()
            if res.data and len(res.data) > 0:
                p = res.data[0]
                return {
                    "name": p.get("name") or "Farmer",
                    "mobile": p.get("mobile"),
                    "location": p.get("location") or "Tamil Nadu",
                    "farm_size": p.get("farm_size", 2.5),
                    "primary_crop": p.get("primary_crop", "Paddy, Tomato"),
                    "preferred_language": p.get("preferred_language", "en"),
                    "notify_weather": p.get("notify_weather", True),
                    "notify_spray": p.get("notify_spray", True),
                    "notify_schemes": p.get("notify_schemes", True)
                }
        except Exception as e:
            logger.warning(f"Supabase profile query failed: {e}. Falling back to local DB.")

    # 2. Local fallback DB
    return local_db.get_or_create_profile(user_id)

@router.put("/", response_model=schemas.FarmerProfileResponse)
@router.post("/", response_model=schemas.FarmerProfileResponse)
def update_profile(
    data: schemas.FarmerProfileUpdate,
    authorization: Optional[str] = Header(None),
    db: Optional[Client] = Depends(get_supabase)
):
    """Updates farmer profile information (farm size, primary crops, location, preferred language)."""
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization.split(" ", 1)[1])
        if payload:
            user_id = payload.get("sub")

    update_payload = {k: v for k, v in data.model_dump().items() if v is not None}

    # 1. Supabase branch
    if db is not None and user_id:
        try:
            # Check existing
            res = db.table("farmer_profiles").select("id").eq("user_id", user_id).execute()
            if res.data and len(res.data) > 0:
                prof_id = res.data[0]["id"]
                db.table("farmer_profiles").update(update_payload).eq("id", prof_id).execute()
            else:
                update_payload["user_id"] = user_id
                db.table("farmer_profiles").insert(update_payload).execute()
        except Exception as e:
            logger.warning(f"Supabase profile update failed: {e}")

    # 2. Local DB update
    updated = local_db.update_farmer_profile(update_payload, user_id=user_id)
    return updated
