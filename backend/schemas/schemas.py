from pydantic import BaseModel, EmailStr
from typing import Optional, List, Union, Any
from datetime import datetime

class UserBase(BaseModel):
    name: str
    mobile: str
    email: Optional[str] = None
    location: Optional[str] = None
    preferred_language: Optional[str] = "en"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str # mobile or email
    password: str

class UserResponse(UserBase):
    id: Union[int, str]
    model_config = {"from_attributes": True}

class FarmerProfileResponse(BaseModel):
    name: Optional[str] = "Farmer"
    mobile: Optional[str] = None
    location: Optional[str] = None
    farm_size: Optional[float] = None
    primary_crop: Optional[str] = None
    preferred_language: Optional[str] = "en"
    notify_weather: Optional[bool] = True
    notify_spray: Optional[bool] = True
    notify_schemes: Optional[bool] = True

class FarmerProfileUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    location: Optional[str] = None
    farm_size: Optional[float] = None
    primary_crop: Optional[str] = None
    preferred_language: Optional[str] = None
    notify_weather: Optional[bool] = None
    notify_spray: Optional[bool] = None
    notify_schemes: Optional[bool] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TopPrediction(BaseModel):
    class_name: str
    confidence: float

class CropAnalysisBase(BaseModel):
    crop_type: str
    detected_disease: str
    confidence: float
    severity: str
    risk_level: str

class CropAnalysisCreate(CropAnalysisBase):
    image_path: str

class CropAnalysisResponse(BaseModel):
    id: Optional[str] = None
    created_at: Optional[str] = None
    crop: str
    condition: str
    confidence: float
    is_healthy: bool
    status: str
    top_predictions: List[TopPrediction]
    disease: Optional[str] = None
    severity: Optional[str] = "Not determined"
    risk: Optional[str] = "Not determined"
    quality_status: Optional[str] = "Passed"
    warning_message: Optional[str] = None
    uncertainty_reason: Optional[str] = None
    latency_ms: Optional[float] = None
    preprocessing_mode: Optional[str] = "direct"
    tta_enabled: Optional[bool] = False

class ChatMessage(BaseModel):
    message: str
    language: Optional[str] = "en"
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    reply: str
    audio_base64: Optional[str] = None

class ChatHistoryItem(BaseModel):
    id: str
    role: str
    message: str
    created_at: str

class VoiceChatResponse(BaseModel):
    detected_language: str
    transcription: str
    reply: str
    audio_base64: Optional[str] = None

