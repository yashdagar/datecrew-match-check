import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

from .feedback import classify
from .prefs import hard_violations

DATA = Path(__file__).resolve().parent.parent / "data"


def load(data_dir: Path = DATA):
    clients = {c["id"]: c for c in json.loads((data_dir / "clients.json").read_text())}
    profiles = {p["id"]: p for p in json.loads((data_dir / "profiles.json").read_text())}
    with open(data_dir / "shares.csv") as f:
        shares = list(csv.DictReader(f))
    return clients, profiles, shares


def enrich(clients: Dict, profiles: Dict, shares: List[Dict]) -> List[Dict]:
    out = []
    for s in shares:
        v = hard_violations(clients[s["client_id"]]["preferences"], profiles[s["profile_id"]])
        row = dict(s, violations=[x.detail for x in v], would_block=bool(v))
        if s["decision"] == "rejected":
            row = classify(row, [x.attribute for x in v])
        out.append(row)
    return out


def _rate(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def summarize(rows: List[Dict]) -> Dict:
    total = len(rows)
    accepted = sum(r["decision"] == "accepted" for r in rows)
    rejected = [r for r in rows if r["decision"] == "rejected"]
    avoidable = [r for r in rejected if r.get("avoidable")]
    kept = [r for r in rows if not r["would_block"]]
    kept_acc = sum(r["decision"] == "accepted" for r in kept)
    blocked_acc = sum(r["decision"] == "accepted" for r in rows if r["would_block"])

    by_mm = defaultdict(lambda: {"shared": 0, "accepted": 0, "avoidable": 0, "would_block": 0})
    for r in rows:
        m = by_mm[r["matchmaker"]]
        m["shared"] += 1
        m["accepted"] += r["decision"] == "accepted"
        m["avoidable"] += bool(r.get("avoidable"))
        m["would_block"] += r["would_block"]
    for m in by_mm.values():
        m["acceptance_pct"] = _rate(m["accepted"], m["shared"])
        m["avoidable_pct_of_shared"] = _rate(m["avoidable"], m["shared"])
    for mm in by_mm:
        k = [r for r in rows if r["matchmaker"] == mm and not r["would_block"]]
        by_mm[mm]["acceptance_after_filter_pct"] = _rate(sum(r["decision"] == "accepted" for r in k), len(k))

    reasons = Counter(x for r in rejected for x in r["reasons"])
    gaps = defaultdict(Counter)
    for r in rejected:
        for g in r["pref_gap_reasons"] + r["unstated_reasons"]:
            gaps[r["client_id"]][g] += 1

    return {
        "shared": total,
        "accepted": accepted,
        "acceptance_pct": _rate(accepted, total),
        "rejected": len(rejected),
        "avoidable_rejections": len(avoidable),
        "avoidable_pct_of_rejections": _rate(len(avoidable), len(rejected)),
        "would_block": total - len(kept),
        "accepted_but_would_block": blocked_acc,
        "acceptance_after_filter_pct": _rate(kept_acc, len(kept)),
        "by_matchmaker": dict(sorted(by_mm.items())),
        "reasons": reasons.most_common(),
        "client_pref_gaps": {c: g.most_common(3) for c, g in sorted(gaps.items()) if sum(g.values()) >= 2},
    }
