import copy
import json

from .audit import enrich, load, preference_updates, summarize
from .feedback import STATED_ATTRS, extract_reasons
from .prefs import hard_violations, shortlist

_clients, _profiles, _shares = load()


def _profile_card(p, r=None):
    card = {k: p[k] for k in ("id", "name", "age", "height_cm", "city", "religion", "diet", "profession", "income_lpa", "education", "interests")}
    if r is not None:
        card["score"] = r.score
        card["violations"] = [{"attribute": v.attribute, "detail": v.detail, "dealbreaker": v.dealbreaker} for v in r.violations]
    return card


def overview():
    s = summarize(enrich(_clients, _profiles, _shares))
    return json.dumps({
        "summary": s,
        "clients": [{"id": c["id"], "name": c["name"], "age": c["age"], "city": c["city"]} for c in _clients.values()],
        "updates": preference_updates(_clients, _profiles, _shares),
    })


def client_view(client_id, overrides_json="{}", top=8):
    client = copy.deepcopy(_clients[client_id])
    client["preferences"].update(json.loads(overrides_json))
    done = [s["profile_id"] for s in _shares if s["client_id"] == client_id]
    res = shortlist(client, list(_profiles.values()), already_shared=done)
    history = [dict(s, violations=[v.detail for v in hard_violations(client["preferences"], _profiles[s["profile_id"]])])
               for s in _shares if s["client_id"] == client_id]
    return json.dumps({
        "client": client,
        "passed": [_profile_card(_profiles[r.profile_id], r) for r in res["passed"][:top]],
        "warned": [_profile_card(_profiles[r.profile_id], r) for r in res["warned"][:top]],
        "blocked": [_profile_card(_profiles[r.profile_id], r) for r in res["blocked"][:top]],
        "counts": {k: len(res[k]) for k in ("passed", "warned", "blocked")},
        "unlock": res["unlock"][:3],
        "history": history,
    })


def triage(text, client_id="", profile_id=""):
    reasons = extract_reasons(text)
    violated = []
    if client_id and profile_id:
        violated = [v.attribute for v in hard_violations(_clients[client_id]["preferences"], _profiles[profile_id])]
    labelled = []
    for r in reasons:
        if r in violated:
            kind = "avoidable"
        elif r in STATED_ATTRS:
            kind = "preference gap"
        else:
            kind = "unstated"
        labelled.append({"reason": r, "kind": kind})
    return json.dumps({"reasons": labelled, "violated": violated})
