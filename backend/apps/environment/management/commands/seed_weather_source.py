from django.core.management.base import BaseCommand

from apps.evidence.models import EvidenceSource


class Command(BaseCommand):
    help = "Create the Open-Meteo evidence source record if it does not exist."

    def handle(self, *args, **options):
        existing = EvidenceSource.objects.filter(provider="Open-Meteo", evidence_type="weather").first()
        if existing:
            self.stdout.write(f"Already exists: {existing.evidence_id}")
            return

        number = 900
        while EvidenceSource.objects.filter(evidence_id=f"E{number}").exists():
            number += 1

        source = EvidenceSource.objects.create(
            evidence_id=f"E{number}",
            provider="Open-Meteo",
            source_name="Open-Meteo weather API (forecast and historical archive)",
            source_url="https://open-meteo.com/",
            evidence_type="weather",
            license="VERIFY_LICENSE",
            geographic_coverage="Coordinate queries within Kenya, Tanzania and Ethiopia",
            limitations=[
                "Current conditions are model-based, not station observations.",
                "Historical values are reanalysis; confirm the model and resolution on open-meteo.com.",
                "The free tier is for non-commercial use; check the licence and attribution terms.",
            ],
        )
        self.stdout.write(self.style.SUCCESS(f"Created {source.evidence_id}"))
        self.stdout.write("Set accessed_at and confirm the licence text in /admin/ (evidence sources).")