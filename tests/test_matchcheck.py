import unittest

from matchcheck.audit import enrich, load, summarize
from matchcheck.feedback import classify, extract_reasons
from matchcheck.prefs import check, shortlist

CLIENT = {
    "id": "C1",
    "preferences": {
        "gender": "M",
        "age": [28, 33],
        "height_cm": [165, 190],
        "religion": ["Hindu"],
        "cities": ["Delhi", "Gurugram"],
        "diet": ["veg"],
        "marital_status": ["never_married"],
        "min_education": "postgraduate",
        "dealbreakers": {"no_smoking": True, "wants_children": True},
        "soft": {"professions": ["Doctor"], "min_income_lpa": 20, "interests": ["music", "travel"]},
    },
}


def profile(**kw):
    base = {
        "id": "P1", "gender": "M", "age": 30, "height_cm": 175, "religion": "Hindu", "city": "Delhi",
        "open_to_relocate": False, "diet": "veg", "smokes": False, "drinks": True, "wants_children": True,
        "marital_status": "never_married", "education": "postgraduate", "profession": "Doctor",
        "income_lpa": 25, "interests": ["music", "travel", "art"],
    }
    base.update(kw)
    return base


class PrefsTest(unittest.TestCase):
    def test_clean_profile_passes_and_scores(self):
        r = check(CLIENT, profile())
        self.assertTrue(r.ok)
        self.assertEqual(r.score, 7.4)

    def test_dealbreaker_and_hard_violations(self):
        r = check(CLIENT, profile(smokes=True, age=40, education="graduate"))
        attrs = {v.attribute for v in r.violations}
        self.assertEqual(attrs, {"smoking", "age", "education"})
        self.assertTrue(any(v.dealbreaker for v in r.violations))

    def test_relocation_rescues_other_city(self):
        self.assertFalse(check(CLIENT, profile(city="Pune")).ok)
        self.assertTrue(check(CLIENT, profile(city="Pune", open_to_relocate=True)).ok)

    def test_shortlist_ranks_skips_shared_and_suggests_unlock(self):
        pool = [
            profile(id="P1"),
            profile(id="P2", profession="Lawyer", interests=[]),
            profile(id="P3", diet="non-veg"),
            profile(id="P4", gender="F"),
        ]
        res = shortlist(CLIENT, pool, already_shared=["P1"])
        self.assertEqual([r.profile_id for r in res["passed"]], ["P2"])
        self.assertEqual([r.profile_id for r in res["blocked"]], ["P3"])
        self.assertEqual(res["unlock"], [("diet", 1)])


class FeedbackTest(unittest.TestCase):
    def test_extracts_multiple_reasons(self):
        self.assertEqual(extract_reasons("He smokes and lives too far, photos meh"), ["location", "smoking", "photos_looks"])

    def test_unknown_is_other(self):
        self.assertEqual(extract_reasons("just not feeling it"), ["other"])

    def test_avoidable_vs_preference_gap(self):
        row = {"feedback": "Too old for me, and he smokes"}
        out = classify(row, violated_attrs=["smoking"])
        self.assertTrue(out["avoidable"])
        self.assertEqual(out["avoidable_reasons"], ["smoking"])
        self.assertEqual(out["pref_gap_reasons"], ["age"])


class AuditOnMockDataTest(unittest.TestCase):
    def test_mock_data_matches_scenario_shape(self):
        s = summarize(enrich(*load()))
        self.assertAlmostEqual(s["acceptance_pct"], 31, delta=3)
        self.assertAlmostEqual(s["avoidable_pct_of_rejections"], 35, delta=4)
        mm = s["by_matchmaker"]
        self.assertGreater(mm["A"]["acceptance_pct"], 2 * mm["B"]["acceptance_pct"])
        self.assertGreater(s["acceptance_after_filter_pct"], s["acceptance_pct"])


if __name__ == "__main__":
    unittest.main()
