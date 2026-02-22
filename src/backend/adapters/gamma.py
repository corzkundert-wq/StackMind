import os
import logging
import requests

logger = logging.getLogger("stackmind")
GAMMA_API_KEY = os.environ.get("GAMMA_API_KEY")

GAMMA_BASE = "https://api.gamma.app"


def is_configured() -> bool:
    return bool(GAMMA_API_KEY)


def generate_presentation(title: str, markdown_content: str, theme: str = "professional") -> dict:
    if not GAMMA_API_KEY:
        return {
            "status": "not_configured",
            "message": "Gamma API key not set. Add your GAMMA_API_KEY in Settings to auto-generate presentations. You can still download the markdown and paste it into Gamma manually.",
        }

    try:
        payload = {
            "title": title,
            "content": markdown_content,
            "theme": theme,
        }

        r = requests.post(
            f"{GAMMA_BASE}/v1/presentations",
            json=payload,
            headers={
                "Authorization": f"Bearer {GAMMA_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

        if r.status_code in (200, 201):
            data = r.json()
            return {
                "status": "success",
                "presentation_url": data.get("url", ""),
                "presentation_id": data.get("id", ""),
                "message": "Presentation created in Gamma!",
            }
        else:
            return {"status": "error", "message": f"Gamma API error: {r.status_code} - {r.text[:200]}"}
    except Exception as e:
        logger.error(f"Gamma generate error: {e}")
        return {"status": "error", "message": str(e)}
