import logging
import httpx

logger = logging.getLogger("stackmind")


def send_webhook_payload(url: str, payload: dict) -> dict:
    if not url:
        logger.info("No webhook URL provided, returning mock response")
        return {
            "status": "mock",
            "message": "No webhook URL configured. Payload ready for delivery.",
            "payload": payload,
        }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload)
            return {
                "status": "sent",
                "status_code": response.status_code,
                "response": response.text[:500],
            }
    except Exception as e:
        logger.error(f"Webhook send failed: {e}")
        return {"status": "error", "message": str(e)}
