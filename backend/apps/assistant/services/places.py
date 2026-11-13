import re
from dataclasses import dataclass

from apps.geography.models import Country, Region

PLACE_RE = re.compile(r"^[\w .'()/\-]{2,100}$")
VALID_CODES = {code for code, _ in Country.CODE_CHOICES}


class ToolArgumentError(ValueError):
    """Raised when a tool argument fails validation."""


@dataclass
class Scope:
    kind: str  # "country" or "region"
    country: Country
    region: Region | None = None

    def filters(self):
        return {"region": self.region} if self.region else {"country": self.country}

    def describe(self):
        return {
            "type": self.kind,
            "country": self.country.code,
            "region_id": self.region.id if self.region else None,
            "name": self.region.name if self.region else self.country.name,
        }


def resolve_scope(place=None, country=None, region_id=None):
    """Return a Scope, or None when the place is not found in KEN, TZA or ETH."""
    if country is not None:
        if not isinstance(country, str) or country.upper() not in VALID_CODES:
            raise ToolArgumentError("country must be one of KEN, TZA or ETH.")
        country = country.upper()

    if region_id is not None:
        if isinstance(region_id, bool) or not isinstance(region_id, int) or region_id < 1:
            raise ToolArgumentError("region_id must be a positive integer.")
        region = Region.objects.select_related("country").filter(pk=region_id).first()
        if region is None or (country and region.country.code != country):
            return None
        return Scope("region", region.country, region)

    if not isinstance(place, str) or not PLACE_RE.fullmatch(place.strip()):
        raise ToolArgumentError("place must be a place name of 2 to 100 plain characters.")

    name = place.strip()
    code = name.upper()
    if code in VALID_CODES:
        found = Country.objects.filter(code=code).first()
    else:
        found = Country.objects.filter(name__iexact=name).first()
    if found and (country is None or found.code == country):
        return Scope("country", found)

    regions = Region.objects.select_related("country").filter(name__iexact=name)
    if country:
        regions = regions.filter(country__code=country)
    matches = list(regions[:2])
    if len(matches) > 1:
        raise ToolArgumentError("The place name is ambiguous; provide country or region_id.")
    if matches:
        return Scope("region", matches[0].country, matches[0])
    return None