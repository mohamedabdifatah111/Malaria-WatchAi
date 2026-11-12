"""MalariaGEN Pf7 sample metadata and drug-resistance genotypes.

Files are global tab-separated tables (~7 MB total); country filtering happens
in build.py. Pf7 reports admin-1 + year per sample, which is the grain the
marker analysis uses (pfkelch13, pfmdr1 N86, pfcrt K76T).
"""
from __future__ import annotations

from pathlib import Path

from mal.fetch._common import download, raw_dir

BASE = "https://www.malariagen.net/wp-content/uploads/2023/11/"
FILES = {
    "pf7_samples": "Pf7_samples.txt",
    "pf7_resistance_status": "Pf7_inferred_resistance_status_classification.txt",
    "pf7_marker_genotypes": "Pf7_drug_resistance_marker_genotypes.txt",
}
LICENCE = "CC BY 4.0 (MalariaGEN Pf7 open release)"


def tsv_rows(p: Path) -> int:
    with open(p, encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f) - 1


def run(force: bool = False) -> None:
    out = raw_dir("pf7")
    for sid, name in FILES.items():
        download(BASE + name, out / name, sid, LICENCE, force=force, count=tsv_rows)
