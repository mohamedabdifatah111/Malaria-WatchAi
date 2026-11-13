"""Google Gemini summary layer for assistant briefs (docs/ARCHITECTURE.md 5.6).

Gemini writes only the brief's short `summary`, from the findings the backend
tools already retrieved. It never produces findings, never sees the user's
question (docs/API.md section 9: no private information to hosted AI services)
and is never the source of a number:

1. Only findings, uncertainties and the place name are sent.
2. The reply passes through `check_numbers`; any number not present in the
   findings rejects the reply.
3. A reply must have finished normally (finishReason STOP) and end with a full
   sentence; a truncated reply (for example when a thinking model spends the
   token budget on reasoning) could otherwise read "... was 0." and still pass
   the number check.
4. On a missing key, timeout, HTTP error, safety block, empty or incomplete
   reply, or failed grounding check, the deterministic template summary is kept.

No Django imports: configuration is passed in, so this is testable without a database.
"""
from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass

from .grounding import check_numbers

logger = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_INSTRUCTION = """You write short malaria surveillance summaries for public-health programme planners.
Rules you must follow:
1. Use ONLY the findings provided. Do not add facts, places, years or sources.
2. Copy every number exactly as written in the findings. Never calculate, add, subtract, round differently or compare numbers to create a new number.
3. Keep each value's place (country level or the named region) and keep the words 'modelled' or 'observed' only where the finding uses them; never add such a label yourself.
4. Population figures are people living in areas at a risk level, never infected people.
5. A resistance marker frequency is not a treatment failure rate.
6. Never give diagnosis, dosing or treatment advice.
7. Mention missing evidence only if it is listed under "Missing or partial evidence"; never claim anything else is unavailable.
Write 3 to 5 plain sentences. No headings, lists, markdown or evidence identifiers."""


class GeminiError(Exception):
    """Any failure to obtain a usable reply."""


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str = ""
    model: str = "gemini-3.8-flash"
    timeout_s: float = 20.0
    # Thinking models count reasoning tokens against this limit; keep it generous.
    max_output_tokens: int = 2048
    thinking_level: str = "low"  # "" omits thinkingConfig (models without thinking)
    enabled: bool = True

    @property
    def active(self) -> bool:
        return bool(self.enabled and self.api_key)


def build_prompt(place_label: str, findings: list[dict], uncertainties: list[str]) -> str:
    lines = [f"Place: {place_label}", "", "Findings:"]
    lines += [f"- ({f.get('topic', 'evidence')}) {f['statement']}" for f in findings]
    if uncertainties:
        lines += ["", "Missing or partial evidence:"] + [f"- {u}" for u in uncertainties]
    lines += ["", "Write the summary now."]
    return "\n".join(lines)


def _request_body(config: GeminiConfig, prompt: str, thinking: bool) -> dict:
    gen = {"temperature": 0.2, "maxOutputTokens": config.max_output_tokens}
    if thinking and config.thinking_level:
        gen["thinkingConfig"] = {"thinkingLevel": config.thinking_level}
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": gen,
    }


def call_gemini(config: GeminiConfig, prompt: str, opener=urllib.request.urlopen) -> str:
    try:
        return _call(config, _request_body(config, prompt, thinking=True), opener)
    except GeminiError as exc:
        # A model without thinking support rejects thinkingConfig with HTTP 400: retry once without it.
        if str(exc) == "http_400" and config.thinking_level:
            return _call(config, _request_body(config, prompt, thinking=False), opener)
        raise


def _call(config: GeminiConfig, body: dict, opener) -> str:
    request = urllib.request.Request(
        API_URL.format(model=config.model),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": config.api_key},
        method="POST",
    )
    try:
        with opener(request, timeout=config.timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise GeminiError(f"http_{exc.code}") from None
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        raise GeminiError("network_or_timeout") from None
    except (ValueError, json.JSONDecodeError):
        raise GeminiError("invalid_json") from None

    if payload.get("promptFeedback", {}).get("blockReason"):
        raise GeminiError("blocked")
    candidates = payload.get("candidates") or []
    if not candidates:
        raise GeminiError("no_candidates")
    finish = candidates[0].get("finishReason", "STOP")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    if not text:
        raise GeminiError(f"empty_reply:{finish}")
    if finish != "STOP":
        raise GeminiError(f"incomplete_reply:{finish}")
    if not text.endswith((".", "!", "?", '."', ".)")):
        raise GeminiError("incomplete_reply:no_final_sentence")
    return text


def summarise(config: GeminiConfig, place_label: str, findings: list[dict], uncertainties: list[str],
              opener=urllib.request.urlopen) -> dict:
    """Return {"used": bool, "summary": str|None, "reason": str, "model": str, "grounding": {...}}."""
    result = {"provider": "gemini", "model": config.model, "used": False, "summary": None, "reason": "",
              "grounding": None}
    if not config.active:
        result["reason"] = "disabled" if not config.enabled else "no_api_key"
        return result
    if not findings:
        result["reason"] = "no_findings"
        return result
    try:
        text = call_gemini(config, build_prompt(place_label, findings, uncertainties), opener=opener)
    except GeminiError as exc:
        logger.warning("Gemini summary not used: %s", exc)
        result["reason"] = str(exc)
        return result
    grounding = check_numbers(text, {"findings": findings, "place": place_label})
    result["grounding"] = grounding
    if not grounding["grounded"]:
        result["reason"] = "ungrounded_numbers"
        return result
    result.update(used=True, summary=text, reason="ok")
    return result
