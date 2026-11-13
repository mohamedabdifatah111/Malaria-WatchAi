from django.db import models
from django.db.models import F, Q

from apps.core.constraints import between, null_or_between, null_or_ordered
from apps.core.models import TimeStampedModel
from apps.evidence.models import EvidenceSource
from apps.geography.models import Country, Region

from .stats import wilson_interval


class Marker(TimeStampedModel):
    """Allowlist of validated markers. Populate only from the project's approved list."""

    name = models.CharField(max_length=50, unique=True)
    gene = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ResistanceObservation(TimeStampedModel):
    """Marker counts. Frequency and its interval are computed from the counts."""

    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.PROTECT)
    marker = models.ForeignKey(Marker, on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    n_tested = models.PositiveIntegerField()
    n_mutant = models.PositiveIntegerField()
    source = models.ForeignKey(EvidenceSource, on_delete=models.PROTECT)

    class Meta:
        ordering = ["country__code", "marker__name", "year", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "region", "marker", "year", "source"], name="res_obs_unique"
            ),
            models.CheckConstraint(condition=Q(n_tested__gte=1), name="res_obs_tested_min"),
            models.CheckConstraint(condition=Q(n_mutant__lte=F("n_tested")), name="res_obs_mut_le_tested"),
            models.CheckConstraint(condition=between("year", 1900, 2100), name="res_obs_year_range"),
        ]

    @property
    def frequency(self):
        return self.n_mutant / self.n_tested

    def confidence_interval(self):
        return wilson_interval(self.n_mutant, self.n_tested)

    def __str__(self):
        return f"{self.marker} {self.year} {self.n_mutant}/{self.n_tested}"


class MarkerTrend(TimeStampedModel):
    """Observed and model-predicted marker frequencies (proportions 0 to 1)."""

    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.PROTECT)
    marker = models.ForeignKey(Marker, on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    observed_frequency = models.FloatField(null=True, blank=True)
    predicted_frequency = models.FloatField(null=True, blank=True)
    n_tested = models.PositiveIntegerField(null=True, blank=True)
    confidence_interval_lower = models.FloatField(null=True, blank=True)
    confidence_interval_upper = models.FloatField(null=True, blank=True)
    validation_method = models.CharField(max_length=200, blank=True)
    model_version = models.CharField(max_length=100, blank=True)
    source = models.ForeignKey(EvidenceSource, on_delete=models.PROTECT)

    class Meta:
        ordering = ["country__code", "marker__name", "year", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(observed_frequency__isnull=False) | Q(predicted_frequency__isnull=False),
                name="trend_has_value",
            ),
            models.CheckConstraint(
                condition=null_or_between("observed_frequency", 0, 1)
                & null_or_between("predicted_frequency", 0, 1),
                name="trend_freq_range",
            ),
            models.CheckConstraint(
                condition=null_or_between("confidence_interval_lower", 0, 1)
                & null_or_between("confidence_interval_upper", 0, 1),
                name="trend_ci_range",
            ),
            models.CheckConstraint(
                condition=null_or_ordered("confidence_interval_lower", "confidence_interval_upper"),
                name="trend_ci_order",
            ),
            models.CheckConstraint(
                condition=Q(n_tested__isnull=True) | Q(n_tested__gte=1), name="trend_tested_min"
            ),
            models.CheckConstraint(condition=between("year", 1900, 2100), name="trend_year_range"),
        ]

    def __str__(self):
        return f"{self.marker} {self.year}"