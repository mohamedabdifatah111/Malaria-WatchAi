"""Run every fetch script:  python -m mal.fetch [--only NAME ...] [--force] [--full]

Each source is independent: a failure is logged and the rest still run, and
the exit code is non-zero if anything failed. Re-runs skip files whose
SHA-256 matches data/manifest.csv. DATA.md is regenerated at the end.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from mal.fetch import (boundaries, covariates, guidelines, map_surveys, pf7,
                       species, who_gho, who_mtm)
from mal.fetch._common import ManifestLocked, check_manifest_writable
from mal.fetch.data_md import write_data_md

SOURCES = {
    "boundaries": boundaries.run,
    "map_surveys": map_surveys.run,
    "covariates": covariates.run,
    "who_mtm": who_mtm.run,
    "pf7": pf7.run,
    "who_gho": who_gho.run,
    "species": species.run,
    "guidelines": guidelines.run,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m mal.fetch")
    ap.add_argument("--only", nargs="+", choices=sorted(SOURCES), help="run only these sources")
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    ap.add_argument("--full", action="store_true", help="also fetch large optional files (HydroLAKES)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s",
                        datefmt="%H:%M:%S")
    log = logging.getLogger("mal.fetch")

    try:
        check_manifest_writable()
    except ManifestLocked as e:
        log.error("%s", e)
        return 2

    failed: list[str] = []
    for name in args.only or SOURCES:
        t = time.time()
        log.info("=== %s", name)
        try:
            if name == "covariates":
                covariates.run(force=args.force, full=args.full)
            else:
                SOURCES[name](force=args.force)
            log.info("=== %s ok (%.0f s)", name, time.time() - t)
        except ManifestLocked as e:
            log.error("%s", e)
            return 2
        except Exception:
            log.exception("=== %s FAILED", name)
            failed.append(name)

    write_data_md()
    if failed:
        log.error("failed sources: %s (see fallbacks in DATA.md)", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
