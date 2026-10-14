import os
import logging
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Load environment from backend/.env or root .env
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    or os.environ.get("SUPABASE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)

_supabase_client: Optional[Client] = None

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.info("Supabase credentials not configured. Cloud database and storage features will run in offline/fallback mode.")
else:
    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to Supabase: {e}. Running in fallback mode.")

# Dependency to provide the optional Supabase client
def get_supabase() -> Optional[Client]:
    """
    Returns an active Supabase client if configured, or None if credentials are absent.
    Endpoints using this dependency must check `if db is not None:` before querying.
    """
    return _supabase_client

