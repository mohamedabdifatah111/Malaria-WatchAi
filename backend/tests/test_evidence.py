import pytest
from django.db import IntegrityError, transaction

from apps.evidence.models import EvidenceSource


def make_evidence(**overrides):
    data = dict(
        evidence_id="E001",
        provider="Test provider",
        source_name="Test dataset",
        evidence_type="survey",
    )
    data.update(overrides)
    return EvidenceSource.objects.create(**data)


@pytest.mark.django_db
def test_evidence_defaults():
    source = make_evidence()
    assert source.license == "VERIFY_LICENSE"
    assert source.limitations == []


@pytest.mark.django_db
def test_period_start_cannot_exceed_end():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_evidence(period_start_year=2020, period_end_year=2010)


@pytest.mark.django_db
def test_evidence_id_is_unique():
    make_evidence()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_evidence()