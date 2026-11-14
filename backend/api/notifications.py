"""
AgroNex Notifications API Router
Exposes endpoints for querying automation channel status (n8n / webhook),
dispatching alerts, and viewing notification delivery history.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from services.notification_service import NotificationService
from config import local_db

router = APIRouter(prefix="/api/notifications", tags=["Automation Notifications"])
notification_service = NotificationService()

class DispatchNotificationRequest(BaseModel):
    event_type: str = Field(..., description="Alert category: WEATHER_RISK, SPRAY_ADVISORY, DISEASE_ALERT, DAILY_COPILOT_BRIEF")
    title: str = Field(..., description="Short alert title")
    message: str = Field(..., description="Notification message body")
    farmer_id: Optional[str] = Field(None, description="Target farmer ID")
    mobile: Optional[str] = Field(None, description="Farmer mobile number")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom sensor or diagnosis payload")

@router.get("/status")
def get_notification_status():
    """Returns the live status of the supported automation channels (n8n, webhook, audit)."""
    return notification_service.get_channel_status()

@router.post("/dispatch")
def dispatch_notification(request: DispatchNotificationRequest):
    """
    Dispatches an agricultural alert through the active automation channel (e.g. n8n webhook)
    and records the event into the notification audit log.
    """
    try:
        result = notification_service.dispatch_alert(
            event_type=request.event_type,
            title=request.title,
            message=request.message,
            farmer_id=request.farmer_id,
            mobile=request.mobile,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch notification: {str(e)}")

@router.get("/history")
def get_notification_history(limit: int = Query(20, ge=1, le=100)):
    """Retrieves recent automation notification events."""
    return local_db.get_recent_notifications(limit=limit)

