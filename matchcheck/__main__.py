import argparse
import html
import json
import sys
from pathlib import Path

from .audit import enrich, load, summarize
from .feedback import extract_reasons
from .prefs import shortlist

OUT = Path(__file__).resolve().parent.parent / "out"


def cmd_shortlist(args):
    clients, profiles, shares = load()
    c = clients[args.client]
    done = [s["profile_id"] for s in shares if s["client_id"] == c["id"]]
    res = shortlist(c, list(profiles.values()), already_shared=done)
    print("%s (%s, %d) seeks %s age %s, %d pass, %d near misses to check with the client, %d filtered out" % (
        c["id"], c["name"], c["age"], c["preferences"]["gender"], c["preferences"]["age"], len(res["passed"]), len(res["warned"]), len(res["blocked"])))
    print("\nTop %d to share:" % args.top)
    for r in res["passed"][:args.top]:
        p = profiles[r.profile_id]
        print("  %s %-8s %d %s %-10s %-11s score=%.2f" % (p["id"], p["name"], p["age"], p["city"], p["profession"], p["religion"], r.score))
    if res["unlock"]:
        print("\nRelaxing one preference would unlock: %s" % ", ".join("%s +%d" % u for u in res["unlock"][:3]))
    print("\nNear misses (one non-deal-breaker preference missed), check with the client:")
    for r in res["warned"][:args.top]:
        print("  %s: %s" % (r.profile_id, "; ".join(v.detail for v in r.violations)))
    print("\nFiltered out (deal-breaker or several misses):")
    for r in res["blocked"][:args.top]:
        print("  %s: %s" % (r.profile_id, "; ".join(v.detail for v in r.violations)))


def cmd_reasons(args):
    text = " ".join(args.text) or sys.stdin.read()
    print(json.dumps(extract_reasons(text)))


def cmd_audit(args):
    s = summarize(enrich(*load()))
    print(json.dumps(s, indent=1))


def _bar(label, n, mx):
    w = int(240 * n / mx) if mx else 0
    return '<div class="bar"><span>%s</span><i style="width:%dpx"></i><b>%d</b></div>' % (html.escape(label), w, n)


def cmd_report(args):
    clients, profiles, shares = load()
    s = summarize(enrich(clients, profiles, shares))
    mx = s["reasons"][0][1] if s["reasons"] else 1
    parts = [
        "<h1>Match Check: rejection audit</h1>",
        '<div class="tiles">',
        '<div><b>%s%%</b>acceptance today</div>' % s["acceptance_pct"],
        '<div><b>%s%%</b>of rejections were avoidable (violated stated prefs)</div>' % s["avoidable_pct_of_rejections"],
        '<div><b>%s%%</b>acceptance if pre-share check had blocked violators</div>' % s["acceptance_after_filter_pct"],
        '<div><b>%d / %d</b>accepted profiles the check would have blocked (false blocks)</div>' % (s["accepted_but_would_block"], s["would_block"]),
        "</div><h2>By matchmaker</h2><ul>",
    ]
    for mm, m in s["by_matchmaker"].items():
        parts.append("<li><b>Matchmaker %s</b>: %d shared, acceptance %s%%, avoidable rejections %s%% of shares, acceptance after filter %s%%</li>" % (
            mm, m["shared"], m["acceptance_pct"], m["avoidable_pct_of_shared"], m["acceptance_after_filter_pct"]))
    parts.append("</ul><h2>Structured rejection reasons</h2>")
    parts += [_bar(k, n, mx) for k, n in s["reasons"]]
    parts.append("<h2>Clients whose rejections aren't explained by their stated preferences</h2><ul>")
    for cid, g in s["client_pref_gaps"].items():
        parts.append("<li><b>%s</b>: %s, ask the matchmaker to update this client's profile</li>" % (cid, ", ".join("%s x%d" % (k, n) for k, n in g)))
    parts.append("</ul><h2>Next-share shortlists</h2>")
    for c in clients.values():
        done = [x["profile_id"] for x in shares if x["client_id"] == c["id"]]
        res = shortlist(c, list(profiles.values()), already_shared=done)
        parts.append("<details><summary>%s %s: %d pass, %d to check, %d blocked</summary><ol>" % (
            c["id"], html.escape(c["name"]), len(res["passed"]), len(res["warned"]), len(res["blocked"])))
        for r in res["passed"][:5]:
            p = profiles[r.profile_id]
            parts.append("<li>%s %s, %d, %s, %s (score %.2f)</li>" % (p["id"], html.escape(p["name"]), p["age"], p["city"], p["profession"], r.score))
        if res["unlock"]:
            parts.append("<p>Relaxing one preference would unlock: %s</p>" % ", ".join("%s +%d" % u for u in res["unlock"][:3]))
        parts.append("</ol><p>Blocked e.g.: %s</p></details>" % html.escape(" | ".join(
            "%s: %s" % (r.profile_id, "; ".join(v.detail for v in r.violations)) for r in res["blocked"][:3])))
    css = ("body{font:15px/1.5 system-ui,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#1d2433;background:#fff}"
           ".tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}"
           ".tiles div{border:1px solid #dde;border-radius:8px;padding:12px}.tiles b{display:block;font-size:26px}"
           ".bar{display:flex;align-items:center;gap:8px;margin:3px 0}.bar span{width:150px}.bar i{height:14px;background:#c2410c;border-radius:3px}"
           "details{margin:6px 0}summary{cursor:pointer}")
    OUT.mkdir(exist_ok=True)
    path = OUT / "report.html"
    path.write_text("<!doctype html><meta charset=utf-8><title>Match Check</title><style>%s</style>%s" % (css, "\n".join(parts)))
    print(path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="matchcheck")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("shortlist")
    p.add_argument("client")
    p.add_argument("--top", type=int, default=8)
    p.set_defaults(fn=cmd_shortlist)
    p = sub.add_parser("reasons")
    p.add_argument("text", nargs="*")
    p.set_defaults(fn=cmd_reasons)
    sub.add_parser("audit").set_defaults(fn=cmd_audit)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
