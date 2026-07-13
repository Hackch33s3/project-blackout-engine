"""
Deletion plan generator for the Project Blackout FB scan.

The engine does NOT delete posts. Facebook has no public API for deleting
posts on a user's profile, and automated browser-automation against
facebook.com violates Meta's Platform Terms section 3.2. The product
delivers a structured DELETION PLAN that the customer executes manually
via Facebook's Activity Log.

The Activity Log deep-link shape we generate is:
  https://www.facebook.com/<username>/allactivity?activity_history=false&p=<encoded_id>

The exact shape varies by post type and FB changes it without notice;
the generated instructions say "open your Activity Log, search for the
post by date and text, click the three dots, click Delete" rather than
relying on a single deep-link working. The deep-link is a convenience,
not a guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class DeletionStep:
    post_id: str
    timestamp: int
    timestamp_human: str
    text_excerpt: str
    permalink: Optional[str]
    activity_log_link: str
    instructions: List[str]


def _activity_log_link(post_id: str) -> str:
    # Conservative: link to the all-activity page with a post filter.
    # FB may strip query params; the instructions text is the real
    # mechanism.
    if not post_id:
        return "https://www.facebook.com/me/allactivity/"
    # Strip non-numeric prefix (e.g. "user_12345" -> "12345")
    numeric = "".join(ch for ch in post_id if ch.isdigit())
    if numeric:
        return f"https://www.facebook.com/me/allactivity/?p={numeric}"
    return "https://www.facebook.com/me/allactivity/"


def _ts_human(ts: int) -> str:
    if not ts:
        return "unknown date"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (OverflowError, OSError, ValueError):
        return "unknown date"


def build_steps(findings: List[Dict[str, Any]]) -> List[DeletionStep]:
    steps: List[DeletionStep] = []
    for f in findings:
        ts = int(f.get("timestamp") or 0)
        steps.append(DeletionStep(
            post_id=f.get("post_id", ""),
            timestamp=ts,
            timestamp_human=_ts_human(ts),
            text_excerpt=f.get("text_excerpt", ""),
            permalink=f.get("permalink"),
            activity_log_link=_activity_log_link(f.get("post_id", "")),
            instructions=[
                f"Open your Facebook Activity Log: {_activity_log_link(f.get('post_id', ''))}",
                f"Use the date filter ({_ts_human(ts)}) to find this post",
                "Click the three dots (...) on the post",
                "Click Delete, then confirm",
                f"Reference post ID: {f.get('post_id', 'n/a')}",
                "Screenshot the 'Post deleted' confirmation and email it to confirm@projectblackout.ca for your records",
            ],
        ))
    return steps


# ----------------------------------------------------------------------------
# Filtered plans by user instruction
# ----------------------------------------------------------------------------

def plan_for_keyword(
    findings: List[Dict[str, Any]],
    keyword: str,
    all_posts: Optional[List[Dict[str, Any]]] = None,
) -> List[DeletionStep]:
    """Filter to posts whose text contains the keyword (case-insensitive).

    Scans BOTH the findings list AND `all_posts` (if provided) so the user
    sees every post that mentions their keyword, not just the ones the
    engine also flagged for a statute. The user, not the engine, decides
    which posts to remove.
    """
    kw = (keyword or "").strip().lower()
    if not kw:
        return build_steps(findings)

    matched: List[Dict[str, Any]] = []
    seen: set = set()

    for f in findings:
        if kw in (f.get("text_excerpt", "") or "").lower():
            matched.append(f)
            seen.add(f.get("post_id"))

    if all_posts:
        for p in all_posts:
            pid = p.get("post_id") or ""
            if pid in seen:
                continue
            text = (p.get("text_excerpt") or p.get("post") or p.get("text") or "")
            if isinstance(text, str) and kw in text.lower():
                matched.append({
                    "post_id": pid,
                    "timestamp": p.get("timestamp", 0),
                    "text_excerpt": text[:280],
                    "permalink": p.get("permalink_url") or p.get("permalink"),
                    "tier": 0,
                    "matched_statute": f"Keyword filter: '{keyword}'",
                    "matched_pattern_note": "User-selected keyword, not a risk score",
                    "matched_weight": 0.0,
                    "match_excerpt": "",
                })
                seen.add(pid)

    return build_steps(matched)


def plan_for_categories(
    findings: List[Dict[str, Any]],
    categories: List[str],
    all_posts: Optional[List[Dict[str, Any]]] = None,
) -> List[DeletionStep]:
    """Filter findings to those flagged in the given category list.

    Categories supported: 'political', 'religious', 'hateful'.
    'political' = tier 2 or 3 findings touching political content (anti-gov
                  rhetoric, anti-immigration, extremist framings).
    'religious' = explicit religion-mention in text. Scans BOTH the findings
                  list AND the full `all_posts` list (if provided) so the
                  user sees the religious content the engine decided to
                  leave alone. The user, not the engine, decides what
                  counts as religious.
    'hateful'   = tier 3 findings matching s.319 / s.83.222 statutes, or
                  tier 2 findings that use dehumanising language.
    """
    cats = set(c.lower() for c in categories)
    matched: List[Dict[str, Any]] = []
    seen_post_ids: set = set()

    # First, filter the existing findings
    for f in findings:
        include = False
        if "hateful" in cats and f.get("tier", 0) == 3:
            include = True
        if "political" in cats and f.get("tier", 0) in (2, 3):
            include = True
        if include:
            matched.append(f)
            seen_post_ids.add(f.get("post_id"))

    # Then, optionally scan all posts for category-only matches
    if "religious" in cats and all_posts:
        for p in all_posts:
            pid = p.get("post_id") or ""
            if pid in seen_post_ids:
                continue
            text = (p.get("text_excerpt") or p.get("post") or p.get("text") or "")
            if isinstance(text, str) and any(
                kw in text.lower() for kw in (
                    "jesus", "christ", "christian", "muslim", "islam", "jew",
                    "jewish", "hindu", "buddha", "buddhist", "sikh", "allah",
                    "yahweh", "torah", "quran", "bible", "church", "mosque",
                    "temple", "synagogue", "pastor", "imam", "rabbi", "priest",
                    "atheist", "atheism", "god", "religion", "faith",
                )
            ):
                # Convert raw post to finding shape
                matched.append({
                    "post_id": pid,
                    "timestamp": p.get("timestamp", 0),
                    "text_excerpt": text[:280],
                    "permalink": p.get("permalink_url") or p.get("permalink"),
                    "tier": 0,  # not flagged; user-selected category
                    "matched_statute": "Category filter: religious",
                    "matched_pattern_note": "User-selected category, not a risk score",
                    "matched_weight": 0.0,
                    "match_excerpt": "",
                })
                seen_post_ids.add(pid)

    return build_steps(matched)


def plan_for_clear_all(findings: List[Dict[str, Any]]) -> List[DeletionStep]:
    return build_steps(findings)


if __name__ == "__main__":
    import sys
    print("deletion_planner module. Import to use.")
