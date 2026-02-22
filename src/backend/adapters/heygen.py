import os
import logging
import requests
import time

logger = logging.getLogger("stackmind")
HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY")

HEYGEN_BASE = "https://api.heygen.com"


def is_configured() -> bool:
    return bool(HEYGEN_API_KEY)


def list_avatars() -> list:
    if not HEYGEN_API_KEY:
        return []
    try:
        r = requests.get(f"{HEYGEN_BASE}/v2/avatars", headers={"X-Api-Key": HEYGEN_API_KEY}, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", {})
            avatars = data.get("avatars", [])
            return [{"avatar_id": a.get("avatar_id"), "name": a.get("avatar_name", "")} for a in avatars[:20]]
    except Exception as e:
        logger.error(f"HeyGen list avatars error: {e}")
    return []


def generate_video(script_text: str, avatar_id: str = None, voice_id: str = None) -> dict:
    if not HEYGEN_API_KEY:
        return {
            "status": "not_configured",
            "message": "HeyGen API key not set. Add your HEYGEN_API_KEY in Settings to generate videos.",
        }

    try:
        payload = {
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id or "default",
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script_text[:5000],
                    "voice_id": voice_id or "en-US-JennyNeural",
                },
            }],
            "dimension": {"width": 1920, "height": 1080},
        }

        r = requests.post(
            f"{HEYGEN_BASE}/v2/video/generate",
            json=payload,
            headers={"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"},
            timeout=30,
        )

        if r.status_code == 200:
            data = r.json().get("data", {})
            video_id = data.get("video_id", "")
            return {
                "status": "processing",
                "video_id": video_id,
                "message": "Video generation started. It will be ready in a few minutes.",
            }
        else:
            return {"status": "error", "message": f"HeyGen API error: {r.status_code} - {r.text[:200]}"}
    except Exception as e:
        logger.error(f"HeyGen generate error: {e}")
        return {"status": "error", "message": str(e)}


def check_video_status(video_id: str) -> dict:
    if not HEYGEN_API_KEY:
        return {"status": "not_configured"}
    try:
        r = requests.get(
            f"{HEYGEN_BASE}/v1/video_status.get?video_id={video_id}",
            headers={"X-Api-Key": HEYGEN_API_KEY},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            return {
                "status": data.get("status", "unknown"),
                "video_url": data.get("video_url", ""),
                "duration": data.get("duration", 0),
            }
    except Exception as e:
        logger.error(f"HeyGen status check error: {e}")
    return {"status": "error"}
