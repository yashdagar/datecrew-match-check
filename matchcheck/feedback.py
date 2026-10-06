import re
from typing import Dict, List

TAXONOMY = {
    "age": [r"\bage\b", r"\btoo old\b", r"\btoo young\b", r"\bolder\b", r"\byounger\b", r"\byears? (?:older|younger)\b"],
    "height": [r"\bheight\b", r"\btall\b", r"\bshort\b", r"\bshorter\b"],
    "religion": [r"\breligion\b", r"\bcaste\b", r"\bcommunity\b", r"\bfaith\b", r"\binterfaith\b"],
    "location": [r"\bcity\b", r"\blocation\b", r"\brelocat\w*", r"\blong[- ]distance\b", r"\bfar\b", r"\babroad\b", r"\bmove\b"],
    "diet": [r"\bveg\w*\b", r"\bnon[- ]?veg\w*\b", r"\bvegan\b", r"\bdiet\b", r"\beats meat\b", r"\bmeat\b"],
    "smoking": [r"\bsmok\w*\b", r"\bcigarette\w*\b"],
    "drinking": [r"\bdrink\w*\b", r"\balcohol\b"],
    "children": [r"\bkids?\b", r"\bchild\w*\b", r"\bfamily planning\b"],
    "education": [r"\beducat\w*\b", r"\bdegree\b", r"\bqualification\w*\b", r"\bmba\b", r"\bpost ?grad\w*\b"],
    "marital_status": [r"\bdivorc\w*\b", r"\bwidow\w*\b", r"\bmarried before\b", r"\bsecond marriage\b"],
    "profession_income": [r"\bjob\b", r"\bcareer\b", r"\bsalary\b", r"\bincome\b", r"\bearn\w*\b", r"\bprofession\b", r"\bstartup\b", r"\bbusiness\b"],
    "photos_looks": [r"\bphotos?\b", r"\bpics?\b", r"\blooks?\b", r"\battract\w*\b", r"\bchemistry\b"],
    "personality": [r"\bvibe\b", r"\bpersonality\b", r"\bbio\b", r"\bboring\b", r"\bintrovert\w*\b", r"\bextrovert\w*\b", r"\bvalues\b"],
    "family": [r"\bfamily background\b", r"\bjoint family\b", r"\bin-?laws\b"],
}

COMPILED = {k: [re.compile(p, re.I) for p in pats] for k, pats in TAXONOMY.items()}

# Attributes a client can already state in their preference form.
STATED_ATTRS = {"age", "height", "religion", "location", "diet", "smoking", "drinking", "children", "education", "marital_status"}


def extract_reasons(text: str) -> List[str]:
    found = []
    for reason, pats in COMPILED.items():
        if any(p.search(text) for p in pats):
            found.append(reason)
    return found or ["other"]


def classify(row: Dict, violated_attrs) -> Dict:
    reasons = extract_reasons(row["feedback"])
    violated = set(violated_attrs)
    avoidable = [r for r in reasons if r in violated]
    unstated = [r for r in reasons if r not in STATED_ATTRS]
    stated_not_violated = [r for r in reasons if r in STATED_ATTRS and r not in violated]
    return {
        **row,
        "reasons": reasons,
        "avoidable": bool(avoidable),
        "avoidable_reasons": avoidable,
        "unstated_reasons": unstated,
        "pref_gap_reasons": stated_not_violated,
    }
