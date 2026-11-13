
from django.db import models
from django.db.models import Q

from apps.core.constraints import between, null_or_between, null_or_ordered
from apps.core.models import TimeStampedModel
from apps.evidence.models import EvidenceSource
from apps.geography.models import Country, Region


class DrugEfficacyRecord(TimeStampedModel):
    """Study-level rows and pooled meta-analysis rows, kept apart by record_type.

    Percent values are PCR-corrected ACPR and failure as supplied by the study or
    pooled analysis. Different follow-up days are separate rows and are never merged.
    """

    class RecordType(models.TextChoices):
        STUDY = "study", "Study"
        POOLED = "pooled", "Pooled estimate"

    record_type = models.CharField(max_length=10, choices=RecordType.choices)
    study_id = models.CharField(max_length=100, blank=True, default="")

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
    )

    region = models.ForeignKey(
        Region,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    site = models.CharField(max_length=200, blank=True)
    drug = models.CharField(max_length=20)
    followup_days = models.PositiveSmallIntegerField()
    n_patients = models.PositiveIntegerField()

    acpr_percent = models.FloatField()
    failure_percent = models.FloatField(null=True, blank=True)

    confidence_interval_lower = models.FloatField(null=True, blank=True)
    confidence_interval_upper = models.FloatField(null=True, blank=True)

    prediction_interval_lower = models.FloatField(null=True, blank=True)
    prediction_interval_upper = models.FloatField(null=True, blank=True)

    heterogeneity_i2 = models.FloatField(null=True, blank=True)
    study_count = models.PositiveIntegerField(null=True, blank=True)

    study_year_start = models.PositiveSmallIntegerField()
    study_year_end = models.PositiveSmallIntegerField()

    source = models.ForeignKey(
        EvidenceSource,
        on_delete=models.PROTECT,
    )

    class Meta:
        ordering = [
            "country__code",
            "drug",
            "followup_days",
            "record_type",
            "id",
        ]

        constraints = [
            # Prevent duplicate study records.
            models.UniqueConstraint(
                fields=[
                    "source",
                    "study_id",
                    "drug",
                    "followup_days",
                ],
                condition=Q(record_type="study"),
                name="eff_unique_study",
            ),

            # Only valid record types are allowed.
            models.CheckConstraint(
                condition=Q(record_type__in=["study", "pooled"]),
                name="eff_type_valid",
            ),

            # Study records must have a study ID.
            models.CheckConstraint(
                condition=(
                    Q(record_type="pooled")
                    | ~Q(study_id="")
                ),
                name="eff_study_needs_id",
            ),

            # Study records must not have study_count.
            # Pooled records must have study_count >= 1.
            models.CheckConstraint(
                condition=(
                    (
                        Q(record_type="study")
                        & Q(study_count__isnull=True)
                    )
                    |
                    (
                        Q(record_type="pooled")
                        & Q(study_count__isnull=False)
                        & Q(study_count__gte=1)
                    )
                ),
                name="eff_study_count_rules",
            ),

            # Patient count must be at least 1.
            models.CheckConstraint(
                condition=Q(n_patients__gte=1),
                name="eff_patients_min",
            ),

            # Follow-up must be at least 1 day.
            models.CheckConstraint(
                condition=Q(followup_days__gte=1),
                name="eff_followup_min",
            ),

            # ACPR percentage must be between 0 and 100.
            models.CheckConstraint(
                condition=between("acpr_percent", 0, 100),
                name="eff_acpr_range",
            ),

            # Failure percentage must be between 0 and 100.
            models.CheckConstraint(
                condition=null_or_between("failure_percent", 0, 100),
                name="eff_fail_range",
            ),

            # Confidence interval validation.
            models.CheckConstraint(
                condition=(
                    null_or_between("confidence_interval_lower", 0, 100)
                    & null_or_between("confidence_interval_upper", 0, 100)
                ),
                name="eff_ci_range",
            ),

            # Prediction interval validation.
            models.CheckConstraint(
                condition=(
                    null_or_between("prediction_interval_lower", 0, 100)
                    & null_or_between("prediction_interval_upper", 0, 100)
                ),
                name="eff_pi_range",
            ),

            # Confidence interval lower bound must not exceed upper bound.
            models.CheckConstraint(
                condition=null_or_ordered(
                    "confidence_interval_lower",
                    "confidence_interval_upper",
                ),
                name="eff_ci_order",
            ),

            # Prediction interval lower bound must not exceed upper bound.
            models.CheckConstraint(
                condition=null_or_ordered(
                    "prediction_interval_lower",
                    "prediction_interval_upper",
                ),
                name="eff_pi_order",
            ),

            # Heterogeneity I2 must be between 0 and 100.
            models.CheckConstraint(
                condition=null_or_between("heterogeneity_i2", 0, 100),
                name="eff_i2_range",
            ),

            # Study start year must not exceed end year.
            models.CheckConstraint(
                condition=Q(
                    study_year_start__lte=models.F("study_year_end")
                ),
                name="eff_years_order",
            ),
        ]

    @property
    def year_range(self):
        if self.study_year_start == self.study_year_end:
            return str(self.study_year_start)

        return f"{self.study_year_start}-{self.study_year_end}"

    def __str__(self):
        return f"{self.record_type} {self.drug} d{self.followup_days}"
