from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.core.models import TimeStampedModel


class AdminLevel(models.TextChoices):
    ADM1 = "ADM1", "Administrative level 1"
    ADM2 = "ADM2", "Administrative level 2"


class Country(TimeStampedModel):
    CODE_CHOICES = [("KEN", "Kenya"), ("TZA", "Tanzania"), ("ETH", "Ethiopia")]

    code = models.CharField(max_length=3, unique=True, choices=CODE_CHOICES)
    name = models.CharField(max_length=100)
    boundary = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "countries"
        constraints = [
            models.CheckConstraint(
                condition=Q(code__in=["KEN", "TZA", "ETH"]),
                name="country_code_supported",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.name})"


class Region(TimeStampedModel):
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="regions")
    name = models.CharField(max_length=200)
    admin_level = models.CharField(max_length=4, choices=AdminLevel.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    # Stable external boundary identifier (for example from the boundary dataset).
    external_id = models.CharField(max_length=100)
    boundary = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["country__code", "admin_level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "admin_level", "external_id"],
                name="region_unique_country_level_external",
            ),
            models.CheckConstraint(
                condition=Q(admin_level__in=["ADM1", "ADM2"]),
                name="region_valid_admin_level",
            ),
            models.CheckConstraint(
                condition=~Q(admin_level="ADM1", parent__isnull=False),
                name="region_adm1_has_no_parent",
            ),
        ]
        indexes = [
            models.Index(fields=["country", "admin_level"], name="region_country_level_idx"),
            models.Index(fields=["name"], name="region_name_idx"),
        ]

    def clean(self):
        super().clean()
        if self.parent_id:
            if self.parent.country_id != self.country_id:
                raise ValidationError("Parent region must belong to the same country.")
            if self.admin_level == AdminLevel.ADM1:
                raise ValidationError("An ADM1 region cannot have a parent.")

    def __str__(self):
        return f"{self.name} ({self.country.code} {self.admin_level})"