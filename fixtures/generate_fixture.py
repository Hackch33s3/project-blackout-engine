"""Generate a synthetic Facebook export fixture for testing."""

import json
import os
import random
from datetime import datetime, timezone, timedelta

random.seed(42)

NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)
SAMPLES = [
    # Tier 3 — should match
    ("2018-03-12", "Anyone know how to build a pressure cooker bomb? Asking for a friend.", "tier3-bomb"),
    ("2019-07-04", "We need to exterminate the immigrants, they are an invasion. Send them all back.", "tier3-exterminate"),
    ("2020-11-22", "Join ISIS, they will pay for your travel. DM me.", "tier3-recruit"),
    # Tier 2 — should match
    ("2021-08-30", "Trudeau is literally Hitler, fascist dictator, must be stopped.", "tier2-hitler"),
    ("2022-02-14", "These refugees are an infestation, like cockroaches. Close the border.", "tier2-infestation"),
    ("2022-05-19", "We need a public hanging of the health officer.", "tier2-hanging"),
    ("2023-01-08", "14/88, the great replacement is real, wake up.", "tier2-1488"),
    ("2023-09-15", "Sovereign citizen here, the government has no jurisdiction over me.", "tier2-sovcit"),
    # Tier 1 — should match
    ("2017-06-12", "Work was so annoying today, my boss is a piece of shit.", "tier1-work"),
    ("2018-09-03", "My ex is crazy, blocked her number finally.", "tier1-ex"),
    ("2019-12-24", "Merry Christmas everyone! Jesus is the reason for the season. Praise God.", "tier1-religious-personal"),
    # Tier 0 — should NOT match
    ("2017-01-15", "Had a great coffee this morning. Life is good."),
    ("2017-04-22", "Just finished a 5k run, new PR!"),
    ("2018-08-11", "Happy birthday mom, love you!"),
    ("2019-02-28", "Loving this new restaurant downtown, try the carbonara."),
    ("2020-05-15", "New puppy, meet Biscuit."),
    ("2021-12-31", "Happy new year everyone, be safe out there."),
    ("2022-07-04", "Watching fireworks with the family, great evening."),
    ("2023-06-18", "Father's day brunch, my dad is the best."),
    ("2024-11-05", "Election day tomorrow, make sure you vote."),
    ("2025-03-14", "Pi day, eat some pie."),
]


def main():
    posts = []
    for i, (date_str, text, *tag) in enumerate(SAMPLES):
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        ts = int(dt.timestamp())
        posts.append({
            "post_id": f"pf_fake_{i:04d}_{ts}",
            "timestamp": ts,
            "title": None,
            "description": None,
            "post": text,
            "attachments": [],
            "permalink_url": f"https://www.facebook.com/me/posts/pf_fake_{i:04d}_{ts}",
            "tag": tag[0] if tag else "tier0",
        })

    # Add filler posts so the report looks realistic
    fillers = [
        "Pizza for dinner tonight, yay or nay?",
        "Anyone else watching the game?",
        "Traffic was terrible this morning.",
        "Coffee #4, the day has only just begun.",
        "Sunsets in the prairies are something else.",
        "My dog learned a new trick today.",
        "Anyone got book recommendations?",
        "Just paid off my student loans!",
        "Work meeting that could have been an email.",
        "Slept 11 hours last night. Needed it.",
        "It is -30 with the windchill, stay warm out there.",
        "Garage sale this weekend, come by.",
        "First snow of the year!",
        "Lost my keys, universe please return them.",
        "Annual physical done, doc says I'm healthy.",
        "BBQ season is upon us.",
    ]
    base = NOW - timedelta(days=2000)
    for i, t in enumerate(fillers):
        dt = base + timedelta(days=i*7 + random.randint(0, 6))
        ts = int(dt.timestamp())
        posts.append({
            "post_id": f"pf_filler_{i:04d}_{ts}",
            "timestamp": ts,
            "post": t,
            "permalink_url": f"https://www.facebook.com/me/posts/pf_filler_{i:04d}_{ts}",
            "tag": "filler",
        })

    payload = posts
    out = os.path.join(os.path.dirname(__file__), "fb_export_sample.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"Wrote {len(posts)} posts to {out}")


if __name__ == "__main__":
    main()
