"""Brief generation with the Gemini summary layer (database; Gemini is faked)."""
import json

import pytest

from apps.assistant.models import AssistantRun
from apps.assistant.services import brief_builder
from tests.factories import make_region, make_source
from tests.test_assistant import new_brief, seed_all


def _fake_summarise(text):
    captured = {}

    def fake(config, place_label, findings, uncertainties, opener=None):
        from apps.assistant.services import gemini

        class Opener:
            def __call__(self, request, timeout=None):
                import io
                captured["body"] = json.loads(request.data.decode())
                return io.BytesIO(json.dumps(
                    {"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode())

        return gemini.summarise(config, place_label, findings, uncertainties, opener=Opener())

    return fake, captured


@pytest.mark.django_db
def test_brief_uses_grounded_gemini_summary(client, settings, monkeypatch):
    settings.GEMINI_API_KEY = "test-key"
    region = make_region()
    seed_all(region, make_source())
    # 0.12 is the factory prevalence estimate; written as 12% it must still pass grounding
    fake, captured = _fake_summarise("Modelled PfPR in Nairobi was 12% in 2020, an estimate rather than "
                                     "an observation.")
    monkeypatch.setattr(brief_builder, "summarise", fake)
    data = new_brief(client, region, question="Summarise the evidence for my district office.")
    assert data["summary"].startswith("Modelled PfPR in Nairobi was 12%")
    assert any("Google Gemini" in lim for lim in data["limitations"])
    run = AssistantRun.objects.get()
    gen = run.grounding_result["summary_generation"]
    assert gen["used"] is True and gen["provider"] == "gemini"
    assert "district office" not in json.dumps(captured["body"])  # question never sent


@pytest.mark.django_db
def test_brief_falls_back_when_gemini_invents_a_number(client, settings, monkeypatch):
    settings.GEMINI_API_KEY = "test-key"
    region = make_region()
    seed_all(region, make_source())
    fake, _ = _fake_summarise("About 3.4 million people are infected in Nairobi.")
    monkeypatch.setattr(brief_builder, "summarise", fake)
    data = new_brief(client, region)
    assert data["summary"].startswith("Validated evidence was retrieved")
    gen = AssistantRun.objects.get().grounding_result["summary_generation"]
    assert gen["used"] is False and gen["reason"] == "ungrounded_numbers"


@pytest.mark.django_db
def test_brief_without_key_keeps_template_summary(client):
    region = make_region()
    seed_all(region, make_source())
    data = new_brief(client, region)
    assert data["summary"].startswith("Validated evidence was retrieved")
    assert AssistantRun.objects.get().grounding_result["summary_generation"]["reason"] == "no_api_key"
