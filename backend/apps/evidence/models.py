from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel


class EvidenceSource(TimeStampedModel):
    """Shared evidence object (docs/API.md section 6).

    Every scientific number served by the API must trace back to a row here
    or to an identified model output.
    """

    class EvidenceType(models.TextChoices):
        SURVEY = "survey", "Survey"
        MODEL_OUTPUT = "model_output", "Model output"
        PUBLICATION = "publication", "Publication"
        GUIDELINE = "guideline", "Guideline"
        WEATHER = "weather", "Weather"
        SYNTHETIC = "synthetic", "Synthetic (labelled)"
        OTHER = "other", "Other"

    evidence_id = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r"^E\d{3,}$", "Use the form E001.")],
    )
    provider = models.CharField(max_length=200)
    source_name = models.CharField(max_length=300)
    source_url = models.URLField(max_length=500, blank=True)
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)
    accessed_at = models.DateField(null=True, blank=True)
    license = models.CharField(max_length=200, default="VERIFY_LICENSE")
    evidence_type = models.CharField(max_length=20, choices=EvidenceType.choices)
    country_code = models.CharField(
        max_length=3,
        blank=True,
        choices=[("KEN", "Kenya"), ("TZA", "Tanzania"), ("ETH", "Ethiopia")],
    )
    geographic_coverage = models.CharField(max_length=300, blank=True)
    period_start_year = models.PositiveSmallIntegerField(null=True, blank=True)
    period_end_year = models.PositiveSmallIntegerField(null=True, blank=True)
    limitations = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["evidence_id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(period_start_year__isnull=True)
                | Q(period_end_year__isnull=True)
                | Q(period_start_year__lte=F("period_end_year")),
                name="evidence_period_start_before_end",
            ),
            models.CheckConstraint(
                condition=Q(publication_year__isnull=True)
                | Q(publication_year__gte=1900, publication_year__lte=2100),
                name="evidence_publication_year_range",
            ),
        ]

    def __str__(self):
        return f"{self.evidence_id}: {self.source_name}"