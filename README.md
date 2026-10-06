# Match Check

Prototype for The Date Crew Product Engineer assessment (Part 3).

**Live demo:** https://datecrew-match-check.netlify.app (runs this repo's Python in the browser via Pyodide, on the mock data below)

**Problem it targets:** about 35% of rejected profiles were rejected for reasons the client had already stated in their preferences. Those rejections cost the client's trust and the matchmaker's time, and they drag acceptance down (31% overall, 21% for Matchmaker B).

**What it does:**

1. **Pre-share preference check.** Before a matchmaker emails a profile, every candidate is checked against the client's stated preferences and deal-breakers (age, height, religion, city/relocation, diet, marital status, education, smoking, drinking, children). Candidates land in three groups:
   - **ready to send:** no misses, ranked by soft fit (profession, income, shared interests, closeness to the preferred age)
   - **near misses:** exactly one non-deal-breaker preference missed ("age 37, client said 28-36"). Clients do accept some of these, so the matchmaker checks with the client instead of the tool hard-blocking them
   - **filtered out:** a deal-breaker (smoking, drinking, children, relocation) or several misses

   If few pass, it says which single preference, if relaxed, unlocks the most near misses.
2. **Rejection feedback structuring.** Free-text rejection feedback is turned into structured reasons, and each rejection is labelled:
   - **avoidable:** the reason matches a stated preference the profile violated (the check would have caught it)
   - **preference gap:** the reason is a stated-type attribute the profile did not violate, so the client's form is stale (the "rejects at first, accepts similar later" clients show up here)
   - **unstated:** looks, personality, career; things the form doesn't capture yet
3. **Preference updates.** When a client accepts a profile that misses their stated preferences, it suggests updating them ("accepted 1 outside age 27-33, widen to 27-35"). This is the "rejects at first, accepts similar later" client from the brief: their form is stale, not their taste.
4. **Audit report.** Acceptance per matchmaker, avoidable rejection rate, reason breakdown, projected acceptance if the check had been used, false blocks (accepted profiles the check would have blocked), and next-share shortlists per client.

## Run

Python 3.9+, standard library only.

```bash
python3 data/generate.py              # regenerate mock data (seeded, deterministic)
python3 -m matchcheck audit           # JSON summary
python3 -m matchcheck shortlist C002  # ranked next profiles for a client + blocked reasons
python3 -m matchcheck reasons "He smokes and lives too far"   # -> ["location", "smoking"]
python3 -m matchcheck report          # writes out/report.html
python3 -m unittest -v                # 13 tests
```

## Mock data

`data/generate.py` builds 12 clients, 600 profiles and 233 shares over a simulated month. Two matchmakers search the pool the way a matrimonial-site filter would (gender, rough age, religion), then differ in how carefully they check the rest of the preferences. It is calibrated to the brief: 30.9% acceptance overall, A 47% vs B 18.8%, 36% of rejections avoidable.

Results on that data:

- **Acceptance if the check had blocked violators:** 30.9% to 40.6% overall; Matchmaker B 18.8% to 26.1%, A 47.0% to 52.3%
- **False blocks:** 9 of 78 blocked shares were accepted anyway, which is why age/height/location ranges should warn, not hard-block, and only deal-breakers should block
- **Top unstated reasons:** profession/income, personality, photos/looks, which tells us what to add to the preference form

## Production version (two weeks, one person)

- Preferences and profiles live in the existing DB or a Google Sheet; the check runs as a sidebar/Apps Script or a small internal web page the matchmaker uses before hitting send.
- The keyword classifier is replaced with an LLM call that returns JSON constrained to the same taxonomy (`matchcheck/feedback.py:TAXONOMY`). The keyword version stays as a baseline and the labelled mock set becomes an eval set.
- Feedback capture becomes a one-click reason picker in the email plus optional free text, so new data is structured at the source.

## Layout

- `matchcheck/prefs.py`: hard checks, soft score, shortlist, unlock suggestions
- `matchcheck/feedback.py`: reason taxonomy and classifier
- `matchcheck/audit.py`: joins shares with checks and feedback, computes metrics and preference-update suggestions
- `matchcheck/__main__.py`: CLI and HTML report
- `matchcheck/web.py` + `index.html`: the live demo (the page loads the package into Pyodide and calls these functions)
- `tests/test_matchcheck.py`: unit tests, plus a check that the mock data matches the brief
