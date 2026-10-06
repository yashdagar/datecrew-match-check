import csv
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
DILIGENCE_A, DILIGENCE_B, ACCEPT_A, ACCEPT_B = 0.99, 0.88, 0.5, 0.35
CITIES = ["Delhi", "Gurugram", "Mumbai", "Bengaluru", "Pune", "Hyderabad"]
RELIGIONS = ["Hindu", "Sikh", "Jain", "Muslim", "Christian"]
PROFESSIONS = ["Engineer", "Doctor", "Lawyer", "Founder", "Consultant", "Designer", "Banker", "Teacher"]
INTERESTS = ["travel", "fitness", "music", "reading", "cooking", "films", "trekking", "art", "startups", "dogs"]
FIRST = {
    "F": ["Aanya", "Diya", "Isha", "Kavya", "Meera", "Naina", "Riya", "Sara", "Tara", "Zoya", "Pooja", "Neha"],
    "M": ["Aarav", "Arjun", "Dev", "Kabir", "Karan", "Nikhil", "Rohan", "Vivaan", "Aditya", "Sahil", "Vikram", "Ishaan"],
}

TEMPLATES = {
    "age": ["He is too old for me", "Age gap is too much", "She's younger than I'd like", "Not in my age range honestly"],
    "height": ["Height is an issue", "Too short for me", "I wanted someone taller"],
    "religion": ["Family wants same community", "Religion is different, parents won't agree", "Caste mismatch"],
    "location": ["Lives in another city, not doing long distance", "Won't relocate, that's a no", "Too far"],
    "diet": ["I'm pure veg, he eats meat", "Non veg is a problem for my family", "Diet doesn't match"],
    "smoking": ["Smokes, already told you no smokers", "He smokes. dealbreaker", "Smoking is a hard no"],
    "drinking": ["Drinks regularly, not ok", "I don't want someone who drinks"],
    "children": ["Doesn't want kids, I do", "We differ on having children", "Wants kids soon, I'm not sure I do"],
    "education": ["Need someone with a post grad degree", "Education level doesn't match"],
    "marital_status": ["Divorced, family not comfortable", "Not open to second marriage"],
    "photos_looks": ["Didn't feel any attraction from the photos", "Photos don't do it for me", "Not my type looks-wise"],
    "personality": ["Bio feels boring", "Vibe seems off", "Seems like an introvert, I want someone outgoing"],
    "profession_income": ["Career not stable enough", "Startup founder, too risky", "Income is lower than I'd like"],
}


def make_person(rng, pid, gender):
    return {
        "id": pid,
        "name": rng.choice(FIRST[gender]),
        "gender": gender,
        "age": rng.randint(25, 38),
        "height_cm": rng.randint(152, 188) if gender == "M" else rng.randint(148, 175),
        "religion": rng.choices(RELIGIONS, weights=[60, 12, 8, 12, 8])[0],
        "city": rng.choice(CITIES),
        "open_to_relocate": rng.random() < 0.5,
        "diet": rng.choices(["veg", "non-veg", "eggetarian"], weights=[40, 50, 10])[0],
        "smokes": rng.random() < 0.15,
        "drinks": rng.random() < 0.45,
        "wants_children": rng.random() < 0.8,
        "marital_status": "never_married" if rng.random() < 0.9 else "divorced",
        "education": rng.choices(["graduate", "postgraduate", "doctorate"], weights=[45, 45, 10])[0],
        "profession": rng.choice(PROFESSIONS),
        "income_lpa": rng.choice([8, 12, 18, 25, 40, 60]),
        "interests": rng.sample(INTERESTS, 3),
    }


def make_client(rng, cid, gender):
    me = make_person(rng, cid, gender)
    seek = "M" if gender == "F" else "F"
    lo = rng.randint(25, 31)
    prefs = {
        "gender": seek,
        "age": [lo, lo + rng.randint(5, 8)],
        "height_cm": [160, 190] if seek == "M" else [148, 172],
        "religion": [me["religion"]] if rng.random() < 0.4 else [],
        "cities": rng.sample(CITIES, 3),
        "diet": ["veg", "eggetarian"] if me["diet"] == "veg" else [],
        "marital_status": ["never_married"],
        "min_education": rng.choice(["graduate", "graduate", "postgraduate"]),
        "dealbreakers": {"no_smoking": rng.random() < 0.7, "no_drinking": rng.random() < 0.15, "wants_children": True},
        "soft": {
            "professions": rng.sample(PROFESSIONS, 3),
            "min_income_lpa": rng.choice([12, 18, 25]),
            "interests": rng.sample(INTERESTS, 3),
        },
    }
    me["preferences"] = prefs
    return me


def main(seed=7):
    import sys
    sys.path.insert(0, str(HERE.parent))
    from matchcheck.prefs import hard_violations

    rng = random.Random(seed)
    clients = [make_client(rng, "C%03d" % i, "F" if i % 2 else "M") for i in range(1, 13)]
    pool = [make_person(rng, "P%03d" % i, "M" if i % 2 else "F") for i in range(1, 601)]

    matchmakers = {"A": DILIGENCE_A, "B": DILIGENCE_B}
    rows = []
    for i, c in enumerate(clients):
        mm = "A" if i % 2 == 0 else "B"
        diligence = matchmakers[mm]
        pr = c["preferences"]
        candidates = [
            p for p in pool
            if p["gender"] == pr["gender"]
            and pr["age"][0] - 2 <= p["age"] <= pr["age"][1] + 2
            and (not pr["religion"] or p["religion"] in pr["religion"] or rng.random() < 0.3)
        ]
        rng.shuffle(candidates)
        shared = 0
        for p in candidates:
            if shared >= 25:
                break
            v = hard_violations(c["preferences"], p)
            if v and rng.random() < diligence:
                continue
            shared += 1
            if v and rng.random() < 0.75:
                attr = rng.choice(v).attribute
                text = rng.choice(TEMPLATES[attr])
                decision = "rejected"
            elif rng.random() < (ACCEPT_A if mm == "A" else ACCEPT_B):
                decision, text = "accepted", ""
            else:
                attr = rng.choice(["photos_looks", "personality", "profession_income", "age", "location"])
                text = rng.choice(TEMPLATES[attr])
                decision = "rejected"
            rows.append({"client_id": c["id"], "profile_id": p["id"], "matchmaker": mm, "decision": decision, "feedback": text})

    (HERE / "clients.json").write_text(json.dumps(clients, indent=1))
    (HERE / "profiles.json").write_text(json.dumps(pool, indent=1))
    with open(HERE / "shares.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("clients=%d profiles=%d shares=%d" % (len(clients), len(pool), len(rows)))


if __name__ == "__main__":
    main()
