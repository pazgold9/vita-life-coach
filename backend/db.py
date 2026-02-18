"""Supabase client — user profiles and conversation storage.

Degrades gracefully: if credentials are missing or the table doesn't exist,
all functions return empty results and never raise.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from backend import config

logger = logging.getLogger(__name__)
_client = None
CONVERSATIONS_TABLE = "conversations"
PROFILES_TABLE = "user_profiles"
DEFAULT_PROFILE_ID = "default"


def _get_client():
    global _client
    if _client is None and config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client
            _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        except Exception as e:
            logger.warning("Supabase not available: %s", e)
    return _client


# ── User Profiles ──────────────────────────────────────────────

PROFILE_FIELDS = [
    "name", "age", "sex", "weight_kg", "height_cm",
    "activity_level", "dietary_restrictions", "medical_conditions", "goals",
]


def get_profile(profile_id: str = DEFAULT_PROFILE_ID) -> dict:
    client = _get_client()
    if client is None:
        return {}
    try:
        result = client.table(PROFILES_TABLE).select("*").eq("id", profile_id).execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        logger.warning("Failed to get profile: %s", e)
        return {}


def update_profile(updates: dict, profile_id: str = DEFAULT_PROFILE_ID) -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        clean = {k: v for k, v in updates.items() if k in PROFILE_FIELDS and v is not None}
        if not clean:
            return False
        clean["updated_at"] = datetime.now(timezone.utc).isoformat()
        client.table(PROFILES_TABLE).update(clean).eq("id", profile_id).execute()
        return True
    except Exception as e:
        logger.warning("Failed to update profile: %s", e)
        return False


def get_profile_summary(profile_id: str = DEFAULT_PROFILE_ID) -> str:
    """Return a human-readable summary of the user profile for the Orchestrator."""
    profile = get_profile(profile_id)
    if not profile:
        return ""
    parts = []
    if profile.get("name"):
        parts.append(f"Name: {profile['name']}")
    if profile.get("age"):
        parts.append(f"Age: {profile['age']}")
    if profile.get("sex"):
        parts.append(f"Sex: {profile['sex']}")
    if profile.get("weight_kg"):
        parts.append(f"Weight: {profile['weight_kg']} kg")
    if profile.get("height_cm"):
        parts.append(f"Height: {profile['height_cm']} cm")
    if profile.get("activity_level"):
        parts.append(f"Activity: {profile['activity_level']}")
    if profile.get("dietary_restrictions"):
        parts.append(f"Dietary restrictions: {profile['dietary_restrictions']}")
    if profile.get("medical_conditions"):
        parts.append(f"Medical conditions: {profile['medical_conditions']}")
    if profile.get("goals"):
        parts.append(f"Goals: {profile['goals']}")
    return "\n".join(parts)


# ── Conversations ──────────────────────────────────────────────

def save_conversation(
    prompt: str,
    response: str,
    steps: list[dict[str, Any]],
    session_id: Optional[str] = None,
) -> Optional[str]:
    """Persist a conversation turn. Returns the row id or None on failure."""
    client = _get_client()
    if client is None:
        return None
    row_id = str(uuid4())
    try:
        safe_steps = json.loads(json.dumps(steps, default=str))
        client.table(CONVERSATIONS_TABLE).insert({
            "id": row_id,
            "session_id": session_id or str(uuid4()),
            "prompt": prompt,
            "response": response,
            "steps": safe_steps,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return row_id
    except Exception as e:
        logger.warning("Failed to save conversation: %s", e)
        return None


def get_history(session_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Retrieve recent conversation history. Returns [] on failure."""
    client = _get_client()
    if client is None:
        return []
    try:
        q = client.table(CONVERSATIONS_TABLE).select("id, session_id, prompt, response, created_at").order("created_at", desc=True).limit(limit)
        if session_id:
            q = q.eq("session_id", session_id)
        result = q.execute()
        return result.data or []
    except Exception as e:
        logger.warning("Failed to get conversation history: %s", e)
        return []
