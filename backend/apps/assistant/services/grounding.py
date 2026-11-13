"""Number-level grounding check for AI-written text (no Django imports).

Every number in the generated text must match a number in the evidence it was
given, at the precision it is written with (0.0558 may appear as 5.6% or 0.06),
allowing proportion <-> percent conversion. A number that appears nowhere in the
evidence - an invented statistic or the model's own arithmetic - makes the text
ungrounded. Digits inside evidence identifiers (E10005) and short list numbering
are ignored. Ported from ml/src/grounding.py so the backend has no ML dependency.
"""
from __future__ import annotations

import math
import re

_NUM = re.compile(
    r"(?<![\w.])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)"
    r"(\s*(?:%|percent\b|per\s+cent\b|million\b|thousand\b|[mk]\b))?",
    re.IGNORECASE,
)
_ID = re.compile(r"\bE\d{3,}\b|\b[A-Z][A-Z0-9]*(?:-[A-Z0-9.]+)+\b")


def extract_numbers(text: str) -> list[dict]:
    spans = [(m.start(), m.end()) for m in _ID.finditer(text or "")]
    out = []
    for m in _NUM.finditer(text or ""):
        if any(a <= m.start() < b for a, b in spans):
            continue
        raw = m.group(1).replace(",", "")
        unit = re.sub(r"\s+", "", (m.group(2) or "")).lower()
        try:
            value = float(raw)
        except ValueError:
            continue
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        scale = 1e6 if unit in ("million", "m") else 1e3 if unit in ("thousand", "k") else 1.0
        out.append({"text": m.group(0).strip(), "value": value * scale, "decimals": decimals, "scale": scale,
                    "percent": unit in ("%", "percent", "percent"), "start": m.start(), "end": m.end()})
    return out


def _numbers_in(obj, sink: list):
    if isinstance(obj, dict):
        for v in obj.values():
            _numbers_in(v, sink)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers_in(v, sink)
    elif isinstance(obj, bool) or obj is None:
        return
    elif isinstance(obj, (int, float)):
        if math.isfinite(float(obj)):
            sink.append(float(obj))
    elif isinstance(obj, str):
        sink.extend(n["value"] for n in extract_numbers(obj))


def _matches(claim: dict, value: float) -> bool:
    tol = 0.5 * 10 ** (-claim["decimals"]) * claim["scale"]
    candidates = [value, value * 100.0] if claim["percent"] else [value]
    return any(abs(c - claim["value"]) <= tol * (1 + 1e-9) for c in candidates)


def _is_list_marker(text: str, claim: dict) -> bool:
    line_start = text.rfind("\n", 0, claim["start"]) + 1
    prefix = text[line_start:claim["start"]].strip()
    nxt = text[claim["end"]:claim["end"] + 1]
    return (prefix in ("", "-", "*") and nxt in (")", ".") and claim["decimals"] == 0
            and not claim["percent"] and claim["value"] < 50)


def check_numbers(text: str, evidence) -> dict:
    """Return {"grounded": bool, "n_numbers": int, "unsupported": [...]}."""
    pool: list[float] = []
    _numbers_in(evidence, pool)
    supported, unsupported = 0, []
    for c in extract_numbers(text):
        if _is_list_marker(text, c):
            continue
        if any(_matches(c, v) for v in pool):
            supported += 1
        else:
            unsupported.append(c["text"])
    return {"grounded": not unsupported, "n_numbers": supported + len(unsupported), "unsupported": unsupported}
