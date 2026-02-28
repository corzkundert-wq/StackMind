import os
import json
import re
import logging
import hashlib
import time
import threading
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

logger = logging.getLogger("stackmind")

AI_INTEGRATIONS_OPENAI_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
AI_INTEGRATIONS_OPENAI_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")

LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5.2")
LLM_MODEL_FAST = os.environ.get("LLM_MODEL_FAST", "gpt-5-mini")

client = OpenAI(
    api_key=AI_INTEGRATIONS_OPENAI_API_KEY,
    base_url=AI_INTEGRATIONS_OPENAI_BASE_URL,
)

_llm_cache = {}
_cache_lock = threading.Lock()
_CACHE_MAX_SIZE = 200
_CACHE_TTL = 3600

def _cache_key(system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> str:
    raw = f"{model}|{max_tokens}|{system_prompt}|{user_prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()

def _cache_get(key: str):
    with _cache_lock:
        entry = _llm_cache.get(key)
        if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
            return entry["data"]
        if entry:
            del _llm_cache[key]
    return None

def _cache_set(key: str, data: dict):
    with _cache_lock:
        if len(_llm_cache) >= _CACHE_MAX_SIZE:
            oldest = min(_llm_cache, key=lambda k: _llm_cache[k]["ts"])
            del _llm_cache[oldest]
        _llm_cache[key] = {"data": data, "ts": time.time()}

def _repair_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        return {"error": "No JSON object found", "raw": raw[:500]}
    text = raw[start:end]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    text = re.sub(r'"\s*\n\s*"', '",\n"', text)
    text = re.sub(r'}\s*\n\s*"', '},\n"', text)
    text = re.sub(r']\s*\n\s*"', '],\n"', text)
    text = re.sub(r'(true|false|null|\d+)\s*\n\s*"', r'\1,\n"', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        text = re.sub(r'(?<!\\)"([^"]*?)(?<!\\)"', lambda m: '"' + m.group(1).replace('"', '\\"') + '"', text)
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        pass
    depth = 0
    truncated = []
    for ch in text:
        truncated.append(ch)
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
    try:
        return json.loads("".join(truncated))
    except json.JSONDecodeError:
        pass
    logger.error(f"JSON repair failed. Raw content (first 1000 chars): {raw[:1000]}")
    return {"error": "Failed to parse JSON after repair attempts", "raw": raw[:500]}


def is_rate_limit_error(exception):
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True,
)
def llm_structured_call(system_prompt: str, user_prompt: str, schema_hint: str = "", max_tokens: int = 8192, fast: bool = False, use_cache: bool = False) -> dict:
    model = LLM_MODEL_FAST if fast else LLM_MODEL

    if use_cache:
        ck = _cache_key(system_prompt, user_prompt, model, max_tokens)
        cached = _cache_get(ck)
        if cached is not None:
            return cached

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        max_completion_tokens=max_tokens,
    )
    content = response.choices[0].message.content or "{}"
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = _repair_json(content)

    if use_cache:
        _cache_set(ck, result)

    return result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True,
)
def llm_structured_call_streaming(system_prompt: str, user_prompt: str, max_tokens: int = 4096, fast: bool = True, use_cache: bool = True) -> dict:
    model = LLM_MODEL_FAST if fast else LLM_MODEL

    if use_cache:
        ck = _cache_key(system_prompt, user_prompt, model, max_tokens)
        cached = _cache_get(ck)
        if cached is not None:
            return cached

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        max_completion_tokens=max_tokens,
        stream=True,
    )
    chunks = []
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            chunks.append(chunk.choices[0].delta.content)

    content = "".join(chunks) or "{}"
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = _repair_json(content)

    if use_cache:
        _cache_set(ck, result)

    return result


def generate_simple_embedding(text: str) -> list:
    text = text[:2000]
    h = hashlib.md5(text.encode()).hexdigest()
    values = []
    for i in range(0, len(h), 2):
        byte_val = int(h[i:i+2], 16)
        values.append((byte_val - 128) / 128.0)
    while len(values) < 64:
        values.append(0.0)
    return values[:64]


def get_embeddings(texts: list) -> list:
    return [generate_simple_embedding(t) for t in texts]


def cosine_similarity(a: list, b: list) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def web_search_market_data(query: str) -> str:
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": """You are a market research analyst. Based on the query, provide current market trends, 
relevant data points, competitor information, industry benchmarks, and recent developments.
Return valid JSON with key "market_data" containing:
- trends (array of strings - current market trends)
- data_points (array of objects with metric, value, source)
- competitors (array of objects with name, position, notable)
- recent_developments (array of strings)
- industry_outlook (string)
- sources_referenced (array of strings - types of sources you'd reference)"""},
                {"role": "user", "content": f"Research current market trends and data for: {query}"},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=4096,
        )
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
        market_data = result.get("market_data", result)
        parts = []
        if isinstance(market_data, dict):
            for key, val in market_data.items():
                if isinstance(val, list):
                    parts.append(f"\n=== {key.upper()} ===")
                    for item in val:
                        parts.append(f"- {json.dumps(item) if isinstance(item, dict) else str(item)}")
                elif isinstance(val, str):
                    parts.append(f"\n=== {key.upper()} ===\n{val}")
        return "\n".join(parts) if parts else json.dumps(market_data)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return ""


def generate_image(prompt: str, size: str = "1024x1024") -> bytes:
    safe_prompt = f"Professional social media visual card, modern clean design, gradient background: {prompt[:900]}"
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=safe_prompt,
            n=1,
            size=size,
            response_format="b64_json",
        )
        import base64
        b64_data = response.data[0].b64_json
        return base64.b64decode(b64_data)
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True,
)
def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    import base64
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    response = client.chat.completions.create(
        model="gpt-4o-mini-transcribe",
        modalities=["text"],
        messages=[
            {"role": "system", "content": "You are an assistant that performs speech-to-text transcription. Return only the transcribed text."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe the following audio exactly as spoken."},
                    {"type": "input_audio", "input_audio": {"data": audio_base64, "format": "wav"}},
                ],
            },
        ],
    )
    return response.choices[0].message.content or ""
