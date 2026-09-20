import logging
import threading
import time

import google.generativeai as genai
import groq

from app.config import get_settings
from ml.config import GROQ_MIN_INTERVAL_SECONDS

logger = logging.getLogger("agent.llm_client")


class RateLimiter:
    def __init__(self, min_interval_seconds: float):
        self.min_interval_seconds = min_interval_seconds
        self.last_call_at = 0.0
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            elapsed = time.monotonic() - self.last_call_at
            remaining = self.min_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self.last_call_at = time.monotonic()


_groq_rate_limiter = RateLimiter(GROQ_MIN_INTERVAL_SECONDS)


def call_groq(prompt: str) -> str:
    settings = get_settings()
    _groq_rate_limiter.wait()
    client = groq.Groq(api_key=settings.groq_api_key, timeout=15)
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400,
        extra_body={"reasoning_effort": "low"},
    )
    return response.choices[0].message.content.strip()


def call_gemini(prompt: str) -> str:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key, transport="rest")
    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(
        prompt, request_options={"timeout": 15}
    )
    return response.text.strip()


def generate_explanation(prompt: str) -> tuple[str | None, str]:
    try:
        text = call_groq(prompt)
        if text:
            return text, "groq"
        logger.warning("groq returned empty content, falling back to gemini")
    except groq.RateLimitError:
        logger.warning("groq rate limit hit, falling back to gemini")
    except Exception:
        logger.exception("groq call failed, falling back to gemini")

    try:
        text = call_gemini(prompt)
        if text:
            return text, "gemini"
        logger.warning("gemini returned empty content, falling back to template")
    except Exception:
        logger.exception("gemini call failed, falling back to template")

    return None, "none"
