from django.db import models
from django.db.models import F, Q

from apps.core.constraints import between
from apps.core.models import TimeStampedModel
from apps.evidence.models import EvidenceSource
from apps.geography.models import Country, Region


class SpeciesRecord(TimeStampedModel):
    """Species evidence. Only 'survey' records carry denominators, and shares are never derived."""

    class Species(models.TextChoices):
        FALCIPARUM = "P. falciparum", "Plasmodium falciparum"
        VIVAX = "P. vivax", "Plasmodium vivax"
        MALARIAE = "P. malariae", "Plasmodium malariae"
        OVALE = "P. ovale", "Plasmodium ovale"
        KNOWLESI = "P. knowlesi", "Plasmodium knowlesi"

    class RecordType(models.TextChoices):
        SURVEY = "survey", "Survey (with denominator)"
        PRESENCE_ONLY = "presence_only", "Presence only"
        MODELLED = "modelled", "Modelled distribution"

    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.PROTECT)
    species = models.CharField(max_length=20, choices=Species.choices)
    record_type = models.CharField(max_length=15, choices=RecordType.choices)
    year = models.PositiveSmallIntegerField()
    positive = models.PositiveIntegerField(null=True, blank=True)
    examined = models.PositiveIntegerField(null=True, blank=True)
    source = models.ForeignKey(EvidenceSource, on_delete=models.PROTECT)

    class Meta:
        ordering = ["country__code", "region__name", "species", "year", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(species__in=[
                    "P. falciparum", "P. vivax", "P. malariae", "P. ovale", "P. knowlesi",
                ]),
                name="species_name_valid",
            ),
            models.CheckConstraint(condition=between("year", 1900, 2100), name="species_year_range"),
            models.CheckConstraint(
                condition=Q(record_type="presence_only", positive__isnull=True, examined__isnull=True)
                | Q(record_type="survey", positive__isnull=False, examined__isnull=False)
                | Q(record_type="modelled"),
                name="species_type_counts",
            ),
            models.CheckConstraint(
                condition=Q(positive__isnull=True)
                | Q(examined__isnull=True)
                | Q(positive__lte=F("examined")),
                name="species_pos_le_exam",
            ),
        ]

    def __str__(self):
        return f"{self.species} {self.record_type} {self.year}"