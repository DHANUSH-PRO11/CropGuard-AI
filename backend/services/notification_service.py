"""
AgroNex Notification Service — Supported Automation Channels & n8n Dispatcher
Dispatches real-time weather risk signals, spray window advisories,
and crop pathology alerts to farmers via n8n automation webhooks,
SMS/WhatsApp gateways, and local audit logs.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment configuration
base_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=base_dir / ".env")
load_dotenv(dotenv_path=base_dir / "backend" / ".env")

class NotificationService:
    def __init__(self):
        self.n8n_webhook_url = os.environ.get("N8N_WEBHOOK_URL")
        self.notification_webhook_url = os.environ.get("NOTIFICATION_WEBHOOK_URL") or self.n8n_webhook_url
        self.timeout = float(os.environ.get("NOTIFICATION_TIMEOUT_SEC", 5.0))

    def get_channel_status(self) -> Dict[str, Any]:
        """Returns the configuration status of active automation channels."""
        has_n8n = bool(self.n8n_webhook_url and self.n8n_webhook_url.startswith("http"))
        has_generic = bool(self.notification_webhook_url and self.notification_webhook_url.startswith("http"))
        
        return {
            "automation_channel": "n8n_webhook" if has_n8n else ("generic_webhook" if has_generic else "local_resilient_log"),
            "n8n_configured": has_n8n,
            "webhook_configured": has_generic,
            "supported_events": [
                "WEATHER_RISK",
                "SPRAY_ADVISORY",
                "DISEASE_ALERT",
                "DAILY_COPILOT_BRIEF"
            ]
        }

    def dispatch_alert(
        self,
        event_type: str,
        title: str,
        message: str,
        farmer_id: Optional[str] = None,
        mobile: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Dispatches an agricultural alert through the active automation channel (n8n or webhook)
        and persists the event to the audit log.
        """
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "title": title,
            "message": message,
            "farmer_id": farmer_id or "default_farmer",
            "mobile": mobile or "9876543210",
            "metadata": metadata or {}
        }

        channel_used = "local_audit"
        dispatch_success = False
        error_msg = None

        target_url = self.n8n_webhook_url or self.notification_webhook_url

        if target_url and target_url.startswith("http"):
            channel_used = "n8n_webhook" if target_url == self.n8n_webhook_url else "webhook"
            try:
                logger.info(f"Dispatching {event_type} notification to automation webhook: {target_url}")
                resp = requests.post(target_url, json=payload, timeout=self.timeout)
                if resp.status_code in (200, 201, 202, 204):
                    dispatch_success = True
                else:
                    error_msg = f"Webhook returned HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(error_msg)
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Automation notification webhook dispatch failed: {e}")
        else:
            # Resilient fallback: Recorded locally for farmer notifications list
            channel_used = "local_audit"
            dispatch_success = True

        # Log into local_db for persistence & farmer notifications page
        try:
            from config import local_db
            local_db.save_notification({
                "event_type": event_type,
                "title": title,
                "message": message,
                "channel": channel_used,
                "status": "delivered" if dispatch_success else "failed",
                "payload": json.dumps(payload, ensure_ascii=False)
            })
        except Exception as e:
            logger.warning(f"Failed to record notification in local_db: {e}")

        return {
            "success": dispatch_success,
            "channel": channel_used,
            "event_type": event_type,
            "timestamp": payload["timestamp"],
            "error": error_msg
        }

    def notify_weather_risk(
        self,
        weather_alert: Dict[str, Any],
        farmer_mobile: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatches an urgent weather risk notification (e.g., heavy rain, frost, gale winds)."""
        title = f"🌾 AgroNex Weather Alert: {weather_alert.get('alert_type', 'Weather Warning')}"
        msg_en = weather_alert.get("message_en", "Adverse weather forecasted for your farm.")
        msg_ta = weather_alert.get("message_ta", "உங்கள் பண்ணைக்கு சாதகமற்ற வானிலை கணிக்கப்பட்டுள்ளது.")
        full_msg = f"{msg_en}\n{msg_ta}"

        return self.dispatch_alert(
            event_type="WEATHER_RISK",
            title=title,
            message=full_msg,
            mobile=farmer_mobile,
            metadata={"alert": weather_alert}
        )

    def notify_spray_advisory(
        self,
        spray_advisory: str,
        crop: str,
        farmer_mobile: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatches spray window feasibility advisory (chemical runoff / spray drift risk)."""
        is_hazard = "DO NOT SPRAY" in spray_advisory or "CAUTION" in spray_advisory
        title = "⚠️ Chemical Spray Hazard Alert" if is_hazard else "✅ Favorable Spray Window"

        return self.dispatch_alert(
            event_type="SPRAY_ADVISORY",
            title=title,
            message=f"Spray advisory for {crop}: {spray_advisory}",
            mobile=farmer_mobile,
            metadata={"crop": crop, "spray_advisory": spray_advisory, "is_hazard": is_hazard}
        )
