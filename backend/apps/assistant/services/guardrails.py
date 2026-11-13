import re

_MEDICAL_ADVICE = [
    r"\bdos(e|es|age|ing)\b",
    r"\bhow (much|many) (mg|milligrams?|tablets?|pills?|doses?)\b",
    r"\bprescri(be|bed|ption)\b",
    r"\bwhat (medicine|medication|drug|treatment) should (i|we|he|she|they)\b",
    r"\bshould (i|we|he|she|they) (take|give|use)\b",
    r"\b(do|does) (i|he|she|they|my \w+) have malaria\b",
    r"\bdiagnos(e|ed|is)\b.{0,40}\b(me|my|him|her|them|patient|child|baby)\b",
    r"\btreat(ing)? (me|my|him|her|them|this patient)\b",
    r"\bmy (child|son|daughter|baby|mother|father|wife|husband|patient)\b",
]

_INJECTION = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"(reveal|show|print|leak).{0,40}(system prompt|password|secret|api key|token|credential)",
    r"\b(drop|delete|truncate) table\b",
    r"(run|execute).{0,30}(sql|shell|command)",
]


def check_question(question):
    """Return (allowed, reason). A first-layer keyword filter, not the only defence."""
    for pattern in _MEDICAL_ADVICE:
        if re.search(pattern, question, re.IGNORECASE):
            return False, "individual_medical_advice"
    for pattern in _INJECTION:
        if re.search(pattern, question, re.IGNORECASE):
            return False, "prompt_injection_suspected"
    return True, ""