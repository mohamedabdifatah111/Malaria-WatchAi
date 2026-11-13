"""Grounding check for AI briefings: every number must come from a tool result.

    from ml.src.grounding import check_brief
    report = check_brief(draft_text, [prevalence_lookup("Kisumu"), drug_evidence_lookup("Kenya")])
    if not report["grounded"]:
        ...  # block the draft; report["unsupported"] lists the offending numbers

A number in the text is *supported* when it matches a number anywhere in the
tool results (values, intervals, counts, years, numbers inside strings),
allowing for the precision it is written with (0.0558 may be written 5.6% or
0.06) and for proportion <-> percent conversion. Each supported number returns
the evidence_ids of the result it matched, so the UI can link it to its source.

The check is deliberately strict: a number the agent calculated itself (a
difference, ratio or sum not present in the tool results) is unsupported. That
is intended - the agent must obtain numbers from tools. Digits inside evidence
identifiers (e.g. 'WHO-MTM-TES-578') and list numbering ('1.' at line start)
are not treated as claims.
"""
from __future__ import annotations

import math
import re
from typing import Any

_NUM = re.compile(
    r"(?<![\w.])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)"
    r"(\s*(?:%|percent\b|per\s+cent\b|million\b|thousand\b|[mk]\b))?",
    re.IGNORECASE)
_ID = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9.]+)+\b")  # evidence-style identifiers


def _id_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _ID.finditer(text) if any(c.isdigit() for c in m.group(0))]


def extract_numbers(text: str) -> list[dict]:
    spans = _id_spans(text)
    out = []
    for m in _NUM.finditer(text):
        if any(a <= m.start() < b for a, b in spans):
            continue
        raw = m.group(1).replace(",", "")
        unit = re.sub(r"\s+", "", (m.group(2) or "")).lower()
        try:
            v = float(raw)
        except ValueError:
            continue
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        scale = 1e6 if unit in ("million", "m") else 1e3 if unit in ("thousand", "k") else 1.0
        out.append({"text": m.group(0).strip(), "value": v * scale, "decimals": decimals, "scale": scale,
                    "percent": unit in ("%", "percent", "percent"), "start": m.start(),
                    "end": m.end()})
    return out


def _walk(obj: Any, evidence: list[str], sink: list, field: str = ""):
    """Collect (number, evidence_ids, field name) triples from nested tool output."""
    if isinstance(obj, dict):
        ev = obj.get("evidence_ids")
        ev = list(ev) if isinstance(ev, (list, tuple)) and ev else evidence
        for k, v in obj.items():
            if k != "evidence_ids":
                _walk(v, ev, sink, str(k))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _walk(v, evidence, sink, field)
    elif isinstance(obj, bool) or obj is None:
        return
    elif isinstance(obj, (int, float)):
        if math.isfinite(float(obj)):
            sink.append((float(obj), evidence, field))
    elif isinstance(obj, str):
        for n in extract_numbers(obj):
            sink.append((n["value"], evidence, field))
    elif hasattr(obj, "tolist"):
        _walk(obj.tolist(), evidence, sink, field)


def significant_digits(claim: dict) -> int:
    digits = re.sub(r"[^0-9]", "", claim["text"].split()[0].replace(",", ""))
    return len(digits.lstrip("0")) or 1


def tool_numbers(tool_results: list[Any]) -> list[tuple[float, list[str], str]]:
    sink: list = []
    for r in tool_results:
        _walk(r, [], sink)
    return sink


def _matches(claim: dict, value: float) -> bool:
    """True when ``value`` rounds to the claim at the claim's written precision."""
    tol = 0.5 * 10 ** (-claim["decimals"]) * claim["scale"]
    candidates = [value, value * 100.0] if claim["percent"] else [value]
    return any(abs(c - claim["value"]) <= tol * (1 + 1e-9) for c in candidates)


def _is_list_marker(text: str, claim: dict) -> bool:
    line_start = text.rfind("\n", 0, claim["start"]) + 1
    prefix = text[line_start:claim["start"]].strip()
    nxt = text[claim["end"]:claim["end"] + 1]
    return prefix in ("", "-", "*") and nxt in (")", ".") and claim["decimals"] == 0 \
        and not claim["percent"] and claim["value"] < 50


def check_brief(text: str, tool_results: list[Any], ignore_list_markers: bool = True) -> dict:
    pool = tool_numbers(tool_results)
    supported, unsupported = [], []
    for c in extract_numbers(text):
        if ignore_list_markers and _is_list_marker(text, c):
            continue
        hits = [(evs, f) for v, evs, f in pool if _matches(c, v)]
        if hits:
            # Short numbers (1-2 significant digits) can match by coincidence in a
            # large result set: label them weak so a human reviewer checks the field.
            supported.append({"text": c["text"], "value": c["value"],
                              "evidence_ids": sorted({e for evs, _ in hits for e in evs}),
                              "matched_fields": sorted({f for _, f in hits if f})[:8],
                              "strength": "strong" if significant_digits(c) >= 3 else "weak"})
        else:
            unsupported.append({"text": c["text"], "value": c["value"],
                                "context": text[max(0, c["start"] - 40): c["end"] + 40]})
    return {"grounded": not unsupported, "n_numbers": len(supported) + len(unsupported),
            "n_weak_matches": sum(s["strength"] == "weak" for s in supported),
            "supported": supported, "unsupported": unsupported,
            "note": ("'grounded' means every number matches a tool value. 'weak' matches (1-2 significant "
                     "digits) may be coincidental - review matched_fields before approval.")}
