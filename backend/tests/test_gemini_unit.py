"""Gemini summary layer and grounding check - no database, no network.

Runs in the normal backend suite; also runnable without Django/PostGIS:
    cd backend && python -m pytest --noconftest -p no:django tests/test_gemini_unit.py
"""
import io
import json
import urllib.error

import pytest

from apps.assistant.services.gemini import GeminiConfig, build_prompt, call_gemini, summarise
from apps.assistant.services.grounding import check_numbers, extract_numbers

FINDINGS = [
    {"topic": "prevalence", "statement": "Kisumu (2020): modelled PfPR estimate 0.196 (interval 0.030 to 0.629)",
     "evidence_ids": ["E10111"]},
    {"topic": "antimalarial efficacy",
     "statement": "Country level: AL pooled estimate, 28-day follow-up, PCR-corrected ACPR 96.9% (927 patients, "
                  "8 studies, 2010-2019)", "evidence_ids": ["E10109"]},
]
ON = GeminiConfig(api_key="test-key", model="gemini-test")


class FakeOpener:
    """Stands in for urllib.request.urlopen and records what was sent."""

    def __init__(self, reply_text=None, payload=None, error=None):
        self.requests = []
        self.payload = payload if payload is not None else {
            "candidates": [{"content": {"parts": [{"text": reply_text}]}, "finishReason": "STOP"}]}
        self.error = error

    def __call__(self, request, timeout=None):
        self.requests.append({"url": request.full_url, "headers": dict(request.header_items()),
                              "body": json.loads(request.data.decode())})
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps(self.payload).encode())


# ---------- grounding ----------

def test_numbers_extracted_with_units_and_ids_ignored():
    vals = [n["value"] for n in extract_numbers("19.6% of 1.2 million; see E10111 and WHO-MTM-TES-578")]
    assert vals == [19.6, 1.2e6]


def test_grounded_text_passes_and_percent_conversion_works():
    r = check_numbers("Modelled PfPR in Kisumu was about 19.6% in 2020; AL efficacy was 96.9%.", FINDINGS)
    assert r["grounded"], r


def test_invented_or_computed_numbers_fail():
    assert check_numbers("Prevalence fell by 40% since 2015.", FINDINGS)["unsupported"] == ["40%", "2015"]
    assert not check_numbers("The gap is 77.3 points.", FINDINGS)["grounded"]


# ---------- Gemini client ----------

def test_request_shape_key_header_and_no_question():
    opener = FakeOpener("Modelled PfPR in Kisumu was 19.6% in 2020.")
    summarise(ON, "Kisumu", FINDINGS, [], opener=opener)
    req = opener.requests[0]
    assert req["url"].endswith("/models/gemini-test:generateContent")
    assert {k.lower(): v for k, v in req["headers"].items()}["x-goog-api-key"] == "test-key"
    sent = json.dumps(req["body"])
    assert "Summarise the available" not in sent  # the user's question is never sent
    assert "systemInstruction" in req["body"] and "Kisumu" in sent


def test_grounded_reply_is_used():
    r = summarise(ON, "Kisumu", FINDINGS, [], opener=FakeOpener("Modelled PfPR in Kisumu was 19.6% in 2020."))
    assert r["used"] and r["reason"] == "ok" and "19.6%" in r["summary"]


def test_ungrounded_reply_is_rejected():
    r = summarise(ON, "Kisumu", FINDINGS, [], opener=FakeOpener("About 1.2 million children are infected."))
    assert not r["used"] and r["reason"] == "ungrounded_numbers"
    assert r["grounding"]["unsupported"] == ["1.2 million"]


@pytest.mark.parametrize("opener,reason", [
    (FakeOpener(error=urllib.error.HTTPError("u", 429, "rate", {}, None)), "http_429"),
    (FakeOpener(error=urllib.error.URLError("down")), "network_or_timeout"),
    (FakeOpener(payload={"promptFeedback": {"blockReason": "SAFETY"}}), "blocked"),
    (FakeOpener(payload={"candidates": []}), "no_candidates"),
])
def test_failures_fall_back(opener, reason):
    r = summarise(ON, "Kisumu", FINDINGS, [], opener=opener)
    assert not r["used"] and r["reason"] == reason


def test_disabled_without_key_and_without_findings():
    assert summarise(GeminiConfig(api_key=""), "K", FINDINGS, [])["reason"] == "no_api_key"
    assert summarise(GeminiConfig(api_key="k", enabled=False), "K", FINDINGS, [])["reason"] == "disabled"
    assert summarise(ON, "K", [], [], opener=FakeOpener("x"))["reason"] == "no_findings"


def test_thought_parts_are_ignored():
    payload = {"candidates": [{"content": {"parts": [{"text": "thinking 12345", "thought": True},
                                                     {"text": "Modelled PfPR was 19.6%."}]}}]}
    assert call_gemini(ON, "p", opener=FakeOpener(payload=payload)) == "Modelled PfPR was 19.6%."


def test_prompt_lists_findings_and_gaps():
    p = build_prompt("Kisumu", FINDINGS, ["No validated parasite species evidence is available for this area."])
    assert "0.196" in p and "96.9%" in p and "parasite species" in p
