"""End-to-end test of the FB scan + report pipeline.

Run from the engine directory:
    python test_facebook_scan.py

Asserts that:
  - The fixture loads.
  - The expected tier counts are present.
  - The PDF builds without error and is a valid PDF (>1KB).
  - The deletion planner produces one step per finding.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from facebook_scan import run_fb_scan
from report_generator import generate_report
from deletion_planner import build_steps, plan_for_keyword, plan_for_categories, plan_for_clear_all


FIXTURE = os.path.join(HERE, "fixtures", "fb_export_sample.json")


def main():
    if not os.path.exists(FIXTURE):
        print(f"Fixture not found: {FIXTURE}")
        print("Run fixtures/generate_fixture.py first.")
        sys.exit(1)

    with open(FIXTURE, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    print("=" * 70)
    print("STEP 1: Load fixture and run scan")
    print("=" * 70)
    print(f"  Loaded {len(data)} posts from fixture")
    result = run_fb_scan(data)
    summary = result["summary"]
    print(f"  Scanned: {summary['total_posts_scanned']}")
    print(f"  Tier 1: {summary['tier_1_count']}")
    print(f"  Tier 2: {summary['tier_2_count']}")
    print(f"  Tier 3: {summary['tier_3_count']}")
    print(f"  Total flagged: {summary['total_findings']}")

    # Assertions on expected behaviour
    assert summary["tier_3_count"] >= 3, f"Expected >=3 tier 3, got {summary['tier_3_count']}"
    assert summary["tier_2_count"] >= 4, f"Expected >=4 tier 2, got {summary['tier_2_count']}"
    assert summary["tier_1_count"] >= 2, f"Expected >=2 tier 1, got {summary['tier_1_count']}"
    assert summary["tier_3_count"] < 6, f"Tier 3 over-flagging, got {summary['tier_3_count']}"

    print()
    print("=" * 70)
    print("STEP 2: Print top findings")
    print("=" * 70)
    for f in result["findings"][:8]:
        print(f"  T{f['tier']} | {f['matched_statute']:30s} | w={f['matched_weight']:.2f}")
        print(f"    {f['text_excerpt'][:90]}")

    print()
    print("=" * 70)
    print("STEP 3: Build deletion plan (all findings)")
    print("=" * 70)
    steps_all = build_steps(result["findings"])
    print(f"  Built {len(steps_all)} steps")
    assert len(steps_all) == len(result["findings"])

    print()
    print("=" * 70)
    print("STEP 4: Plan for keyword 'immigrant'")
    print("=" * 70)
    raw_posts = [
        {"post_id": p["post_id"], "timestamp": p["timestamp"],
         "post": p.get("post", ""), "permalink_url": p.get("permalink_url")}
        for p in data
    ]
    steps_kw = plan_for_keyword(result["findings"], "immigrant", all_posts=raw_posts)
    print(f"  {len(steps_kw)} steps matched 'immigrant' (any post, not just flagged)")
    assert len(steps_kw) >= 1

    print()
    print("=" * 70)
    print("STEP 5: Plan for categories ['political', 'hateful']")
    print("=" * 70)
    steps_cat = plan_for_categories(result["findings"], ["political", "hateful"], all_posts=raw_posts)
    print(f"  {len(steps_cat)} steps in political+hateful")
    assert len(steps_cat) >= 3

    print()
    print("=" * 70)
    print("STEP 6: Plan for 'religious'")
    print("=" * 70)
    steps_rel = plan_for_categories(result["findings"], ["religious"], all_posts=raw_posts)
    print(f"  {len(steps_rel)} steps in religious")
    # The fixture has 1 explicit religious post ("Merry Christmas / Jesus")
    assert len(steps_rel) >= 1

    print()
    print("=" * 70)
    print("STEP 7: Clear all plan")
    print("=" * 70)
    steps_clear = plan_for_clear_all(result["findings"])
    print(f"  {len(steps_clear)} steps in clear-all")
    assert len(steps_clear) == len(result["findings"])

    print()
    print("=" * 70)
    print("STEP 8: Generate PDF report (full)")
    print("=" * 70)
    pdf_bytes = generate_report(
        customer_name="Test Customer",
        scan_result=result,
        deletion_steps=steps_all,
    )
    out_path = os.path.join(HERE, "fixtures", "test_report.pdf")
    with open(out_path, "wb") as fh:
        fh.write(pdf_bytes)
    print(f"  Wrote {len(pdf_bytes)} bytes to {out_path}")
    assert len(pdf_bytes) > 5_000, f"PDF suspiciously small: {len(pdf_bytes)} bytes"
    assert pdf_bytes[:5] == b"%PDF-", "Not a valid PDF (no %PDF header)"

    print()
    print("=" * 70)
    print("STEP 9: Generate PDF report (deletion-only, custom filter)")
    print("=" * 70)
    pdf_filtered = generate_report(
        customer_name="Test Customer",
        scan_result=result,
        deletion_steps=steps_cat,
    )
    out_path2 = os.path.join(HERE, "fixtures", "test_report_political.pdf")
    with open(out_path2, "wb") as fh:
        fh.write(pdf_filtered)
    print(f"  Wrote {len(pdf_filtered)} bytes to {out_path2}")

    print()
    print("=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)
    print(f"  Open {out_path} to inspect the full report")
    print(f"  Open {out_path2} to inspect the political-only deletion plan")


if __name__ == "__main__":
    main()
