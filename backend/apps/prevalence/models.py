from django.db import models
from django.db.models import F, Q

from apps.core.constraints import between, null_or_between, null_or_ordered
from apps.core.models import TimeStampedModel
from apps.evidence.models import EvidenceSource
from apps.geography.models import Country, Region


class PrevalenceObservation(TimeStampedModel):
    """Raw survey observation. Counts are validated; no value is derived or invented."""

    survey_id = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.PROTECT)
    longitude = models.FloatField()
    latitude = models.FloatField()
    survey_year = models.PositiveSmallIntegerField()
    n_examined = models.PositiveIntegerField()
    n_positive = models.PositiveIntegerField()
    lower_age = models.FloatField(null=True, blank=True)
    upper_age = models.FloatField(null=True, blank=True)
    diagnostic_method = models.CharField(max_length=100, blank=True)
    source = models.ForeignKey(EvidenceSource, on_delete=models.PROTECT)

    class Meta:
        ordering = ["country__code", "survey_year", "survey_id"]
        constraints = [
            models.UniqueConstraint(fields=["survey_id", "source"], name="prev_obs_unique_survey"),
            models.CheckConstraint(condition=Q(n_examined__gte=1), name="prev_obs_examined_min"),
            models.CheckConstraint(
                condition=Q(n_positive__lte=F("n_examined")), name="prev_obs_pos_le_exam"
            ),
            models.CheckConstraint(condition=between("latitude", -90, 90), name="prev_obs_lat_range"),
            models.CheckConstraint(condition=between("longitude", -180, 180), name="prev_obs_lon_range"),
            models.CheckConstraint(condition=between("survey_year", 1900, 2100), name="prev_obs_year_range"),
            models.CheckConstraint(
                condition=null_or_ordered("lower_age", "upper_age"), name="prev_obs_age_order"
            ),
        ]
        indexes = [models.Index(fields=["country", "survey_year"], name="prev_obs_country_year_idx")]

    def __str__(self):
        return f"{self.survey_id} ({self.survey_year})"


class PrevalenceEstimate(TimeStampedModel):
    """Observed or modelled prevalence for a region and year.

    Values are proportions between 0 and 1 (unit to be confirmed with the ML engineer).
    """

    class SourceType(models.TextChoices):
        OBSERVED = "observed", "Observed"
        MODELLED = "modelled", "Modelled"

    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    indicator = models.CharField(max_length=20, default="PfPR")
    estimate = models.FloatField()
    lower_interval = models.FloatField(null=True, blank=True)
    upper_interval = models.FloatField(null=True, blank=True)
    source_type = models.CharField(max_length=10, choices=SourceType.choices)
    model_version = models.CharField(max_length=100, blank=True)
    nearest_survey_distance_km = models.FloatField(null=True, blank=True)
    survey_density = models.FloatField(null=True, blank=True)
    extrapolation_flag = models.BooleanField(null=True, blank=True)
    reliability_status = models.CharField(max_length=50, blank=True)
    source = models.ForeignKey(EvidenceSource, on_delete=models.PROTECT)

    class Meta:
        ordering = ["country__code", "region__name", "year", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["region", "year", "indicator", "source_type", "model_version"],
                name="prev_est_unique",
            ),
            models.CheckConstraint(condition=between("year", 1900, 2100), name="prev_est_year_range"),
            models.CheckConstraint(condition=between("estimate", 0, 1), name="prev_est_value_range"),
            models.CheckConstraint(
                condition=null_or_between("lower_interval", 0, 1)
                & null_or_between("upper_interval", 0, 1),
                name="prev_est_bounds_range",
            ),
            models.CheckConstraint(
                condition=Q(lower_interval__isnull=True) | Q(lower_interval__lte=F("estimate")),
                name="prev_est_lower_le",
            ),
            models.CheckConstraint(
                condition=Q(upper_interval__isnull=True) | Q(upper_interval__gte=F("estimate")),
                name="prev_est_upper_ge",
            ),
            models.CheckConstraint(
                condition=Q(nearest_survey_distance_km__isnull=True, survey_density__isnull=True)
                | Q(nearest_survey_distance_km__gte=0, survey_density__isnull=True)
                | Q(nearest_survey_distance_km__isnull=True, survey_density__gte=0)
                | Q(nearest_survey_distance_km__gte=0, survey_density__gte=0),
                name="prev_est_unc_nonneg",
            ),
        ]
        indexes = [models.Index(fields=["region", "year"], name="prev_est_region_year_idx")]

    @property
    def interval_width(self):
        if self.lower_interval is None or self.upper_interval is None:
            return None
        return self.upper_interval - self.lower_interval

    def __str__(self):
        return f"{self.indicator} {self.region_id} {self.year}"