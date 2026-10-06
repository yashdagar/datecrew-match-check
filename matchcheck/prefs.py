from dataclasses import dataclass, field
from collections import Counter
from typing import Dict, List


@dataclass
class Violation:
    attribute: str
    detail: str
    dealbreaker: bool


@dataclass
class CheckResult:
    profile_id: str
    ok: bool
    violations: List[Violation] = field(default_factory=list)
    score: float = 0.0
    notes: List[str] = field(default_factory=list)


EDU_RANK = {"graduate": 1, "postgraduate": 2, "doctorate": 3}


def _in_range(value, rng):
    lo, hi = rng
    return lo <= value <= hi


def hard_violations(prefs: Dict, profile: Dict) -> List[Violation]:
    v = []
    if "gender" in prefs and profile["gender"] != prefs["gender"]:
        v.append(Violation("gender", "wrong gender", True))
    if "age" in prefs and not _in_range(profile["age"], prefs["age"]):
        v.append(Violation("age", "age %d outside %d-%d" % (profile["age"], *prefs["age"]), False))
    if "height_cm" in prefs and not _in_range(profile["height_cm"], prefs["height_cm"]):
        v.append(Violation("height", "height %dcm outside %d-%d" % (profile["height_cm"], *prefs["height_cm"]), False))
    if prefs.get("religion") and profile["religion"] not in prefs["religion"]:
        v.append(Violation("religion", "religion %s not in %s" % (profile["religion"], "/".join(prefs["religion"])), False))
    if prefs.get("cities") and profile["city"] not in prefs["cities"] and not profile.get("open_to_relocate"):
        v.append(Violation("location", "%s, not open to relocating" % profile["city"], False))
    if prefs.get("diet") and profile["diet"] not in prefs["diet"]:
        v.append(Violation("diet", "diet %s not in %s" % (profile["diet"], "/".join(prefs["diet"])), False))
    if prefs.get("marital_status") and profile["marital_status"] not in prefs["marital_status"]:
        v.append(Violation("marital_status", profile["marital_status"], False))
    if prefs.get("min_education") and EDU_RANK[profile["education"]] < EDU_RANK[prefs["min_education"]]:
        v.append(Violation("education", "%s below %s" % (profile["education"], prefs["min_education"]), False))

    db = prefs.get("dealbreakers", {})
    if db.get("no_smoking") and profile["smokes"]:
        v.append(Violation("smoking", "smokes", True))
    if db.get("no_drinking") and profile["drinks"]:
        v.append(Violation("drinking", "drinks", True))
    if "wants_children" in db and profile["wants_children"] != db["wants_children"]:
        want = "wants" if profile["wants_children"] else "does not want"
        v.append(Violation("children", "%s children" % want, True))
    if db.get("must_relocate_to") and profile["city"] != db["must_relocate_to"] and not profile.get("open_to_relocate"):
        v.append(Violation("location", "won't move to %s" % db["must_relocate_to"], True))
    return v


def soft_score(prefs: Dict, profile: Dict) -> float:
    score = 0.0
    soft = prefs.get("soft", {})
    if soft.get("professions") and profile["profession"] in soft["professions"]:
        score += 2
    if soft.get("min_income_lpa") and profile["income_lpa"] >= soft["min_income_lpa"]:
        score += 1.5
    interests = set(soft.get("interests", []))
    if interests:
        score += 3 * len(interests & set(profile["interests"])) / len(interests)
    if prefs.get("age"):
        lo, hi = prefs["age"]
        mid = (lo + hi) / 2
        score += max(0.0, 1 - abs(profile["age"] - mid) / max(1, (hi - lo)))
    return round(score, 2)


def check(client: Dict, profile: Dict) -> CheckResult:
    prefs = client["preferences"]
    v = hard_violations(prefs, profile)
    return CheckResult(profile["id"], ok=not v, violations=v, score=soft_score(prefs, profile))


def shortlist(client: Dict, profiles: List[Dict], already_shared=()) -> Dict[str, List[CheckResult]]:
    passed, warned, blocked = [], [], []
    seen = set(already_shared)
    for p in profiles:
        if p["id"] == client["id"] or p["id"] in seen or p["gender"] != client["preferences"]["gender"]:
            continue
        r = check(client, p)
        if r.ok:
            passed.append(r)
        elif len(r.violations) == 1 and not r.violations[0].dealbreaker:
            warned.append(r)
        else:
            blocked.append(r)
    passed.sort(key=lambda r: -r.score)
    warned.sort(key=lambda r: -r.score)
    unlock = Counter(r.violations[0].attribute for r in warned)
    return {"passed": passed, "warned": warned, "blocked": blocked, "unlock": unlock.most_common()}
