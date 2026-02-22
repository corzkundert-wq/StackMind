import os
import logging
import requests

logger = logging.getLogger("stackmind")
RUNWAY_API_KEY = os.environ.get("RUNWAY_API_KEY")

RUNWAY_BASE = "https://api.dev.runwayml.com/v1"


def is_configured() -> bool:
    return bool(RUNWAY_API_KEY)


def generate_video(prompt: str, duration: int = 5) -> dict:
    if not RUNWAY_API_KEY:
        return {
            "status": "not_configured",
            "message": "Runway API key not set. Add your RUNWAY_API_KEY in Settings to generate videos.",
        }

    try:
        payload = {
            "promptText": prompt[:500],
            "model": "gen3a_turbo",
            "duration": min(duration, 10),
            "watermark": False,
        }

        r = requests.post(
            f"{RUNWAY_BASE}/image_to_video",
            json=payload,
            headers={
                "Authorization": f"Bearer {RUNWAY_API_KEY}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-11-06",
            },
            timeout=30,
        )

        if r.status_code in (200, 201):
            data = r.json()
            task_id = data.get("id", "")
            return {
                "status": "processing",
                "task_id": task_id,
                "message": "Video generation started. It will be ready shortly.",
            }
        else:
            return {"status": "error", "message": f"Runway API error: {r.status_code} - {r.text[:200]}"}
    except Exception as e:
        logger.error(f"Runway generate error: {e}")
        return {"status": "error", "message": str(e)}


def check_task_status(task_id: str) -> dict:
    if not RUNWAY_API_KEY:
        return {"status": "not_configured"}
    try:
        r = requests.get(
            f"{RUNWAY_BASE}/tasks/{task_id}",
            headers={
                "Authorization": f"Bearer {RUNWAY_API_KEY}",
                "X-Runway-Version": "2024-11-06",
            },
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            status = data.get("status", "unknown")
            output = data.get("output", [])
            video_url = output[0] if output else ""
            return {
                "status": status,
                "video_url": video_url,
            }
    except Exception as e:
        logger.error(f"Runway status check error: {e}")
    return {"status": "error"}
