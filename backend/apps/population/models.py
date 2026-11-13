from django.db import models

from apps.core.constraints import between
from apps.core.models import TimeStampedModel
from apps.evidence.models import EvidenceSource
from apps.geography.models import Country, Region


class PopulationAtRisk(TimeStampedModel):
    """People living in a region and risk class. NOT a count of infected people."""

    class RiskClass(models.TextChoices):
        VERY_LOW = "very_low", "Very low (PfPR below 1%)"
        LOW = "low", "Low (1% to below 10%)"
        MODERATE = "moderate", "Moderate (10% to below 35%)"
        HIGH = "high", "High (35% and above)"

    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    risk_class = models.CharField(max_length=10, choices=RiskClass.choices)
    population = models.PositiveBigIntegerField()
    population_source = models.CharField(max_length=200)
    prevalence_model_version = models.CharField(max_length=100)
    uncertainty_status = models.CharField(max_length=50, blank=True)
    source = models.ForeignKey(EvidenceSource, on_delete=models.PROTECT)

    class Meta:
        ordering = ["country__code", "region__name", "year", "risk_class"]
        verbose_name_plural = "population at risk"
        constraints = [
            models.UniqueConstraint(
                fields=["region", "year", "risk_class", "prevalence_model_version"],
                name="par_unique",
            ),
            models.CheckConstraint(condition=between("year", 1900, 2100), name="par_year_range"),
            models.CheckConstraint(
                condition=models.Q(risk_class__in=["very_low", "low", "moderate", "high"]),
                name="par_risk_class_valid",
            ),
        ]

    def __str__(self):
        return f"{self.region_id} {self.year} {self.risk_class}"