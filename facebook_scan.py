"""
Facebook export parser + scorer for the Project Blackout C-9 risk engine.

INPUT: a Facebook "Download Your Information" archive (ZIP) or the
       extracted `posts/your_posts__check_ins__photos_and_videos_1.json`
       file. The exporter dumps an array of post objects with timestamps,
       text, attachments, titles, and (sometimes) the original permalink.

OUTPUT: a dict with `summary` counts per tier and `findings`, a list of
        individual posts that matched at least one pattern.

DESIGN CHOICES
  - Pure stdlib + the c9_keywords module. No Playwright, no BrightData,
    no external HTTP. This module is safe to run on the engine as a
    long-lived service.
  - Matches are de-duplicated per post (a post can match multiple
    patterns; the report shows the highest tier and the top pattern).
  - The original `post_id` and `creation_timestamp` are preserved so
    the deletion planner can produce deterministic Activity Log deep-links.
  - The customer-uploaded export is NEVER written to disk by this
    module. The caller (the FastAPI endpoint) is responsible for storage
    and 30-day retention; this function just reads the parsed dict.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from c9_keywords import PATTERNS, PATTERNS_BY_TIER, TIER_LABELS, TIER_DISCLAIMERS


# ----------------------------------------------------------------------------
# Export format handling
# ----------------------------------------------------------------------------

def load_export(payload: Any) -> List[Dict[str, Any]]:
    """Normalise a Facebook export to a list of post dicts.

    Accepts:
      - a JSON list of post objects (typical of the .json inside the ZIP)
      - a dict with a top-level key like 'posts' or 'status_updates' or
        'posts_v2'
      - a JSON array of arrays (older exporter format)
    """
    if isinstance(payload, list):
        if payload and isinstance(payload[0], list):
            # old nested format
            flat = []
            for chunk in payload:
                if isinstance(chunk, list):
                    flat.extend(chunk)
            return [p for p in flat if isinstance(p, dict)]
        return [p for p in payload if isinstance(p, dict)]

    if isinstance(payload, dict):
        for key in ("posts", "status_updates", "posts_v2", "your_posts"):
            if key in payload and isinstance(payload[key], list):
                return [p for p in payload[key] if isinstance(p, dict)]
        # single post
        return [payload]

    raise ValueError("Unrecognised Facebook export shape")


# ----------------------------------------------------------------------------
# Post normalisation
# ----------------------------------------------------------------------------

@dataclass
class Post:
    post_id: str
    timestamp: int              # unix seconds
    text: str
    permalink: Optional[str] = None
    title: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_export(cls, obj: Dict[str, Any]) -> "Post":
        ts = obj.get("timestamp") or obj.get("creation_timestamp") or 0
        if isinstance(ts, str):
            try:
                ts = int(ts)
            except ValueError:
                ts = 0
        # FB ID is sometimes int, sometimes string
        pid = str(obj.get("post_id") or obj.get("id") or obj.get("timeline_path") or "")
        text_parts = []
        if obj.get("title"):
            text_parts.append(str(obj["title"]))
        if obj.get("description"):
            text_parts.append(str(obj["description"]))
        if obj.get("post"):
            text_parts.append(str(obj["post"]))
        if obj.get("message"):
            text_parts.append(str(obj["message"]))
        if obj.get("data") and isinstance(obj["data"], list):
            for chunk in obj["data"]:
                if isinstance(chunk, dict) and chunk.get("post"):
                    text_parts.append(str(chunk["post"]))
        if obj.get("attachments") and isinstance(obj["attachments"], list):
            for att in obj["attachments"]:
                if isinstance(att, dict):
                    if att.get("description"):
                        text_parts.append(str(att["description"]))
                    if att.get("title"):
                        text_parts.append(str(att["title"]))
        text = "\n".join([p for p in text_parts if p])
        permalink = obj.get("permalink_url") or obj.get("url") or obj.get("link")
        return cls(
            post_id=pid,
            timestamp=int(ts) if ts else 0,
            text=text,
            permalink=permalink,
            title=obj.get("title"),
            raw=obj,
        )


# ----------------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------------

@dataclass
class Finding:
    post_id: str
    timestamp: int
    text_excerpt: str
    permalink: Optional[str]
    tier: int
    matched_statute: str
    matched_pattern_note: str
    matched_weight: float
    match_excerpt: str  # the actual substring that matched


def _excerpt(text: str, n: int = 280) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    if len(t) <= n:
        return t
    return t[:n].rsplit(" ", 1)[0] + "..."


def _match_excerpt(text: str, pat: "re.Pattern[str]") -> str:
    m = pat.search(text)
    if not m:
        return ""
    s = max(0, m.start() - 40)
    e = min(len(text), m.end() + 40)
    snippet = text[s:e].strip()
    return snippet


def score_posts(posts: List[Post]) -> Dict[str, Any]:
    findings: List[Finding] = []
    total_scanned = len(posts)

    for post in posts:
        if not post.text:
            continue
        # Track the highest-tier match for this post
        best: Optional[Finding] = None
        for p in PATTERNS:
            m = p.pattern.search(post.text)
            if not m:
                continue
            candidate = Finding(
                post_id=post.post_id,
                timestamp=post.timestamp,
                text_excerpt=_excerpt(post.text),
                permalink=post.permalink,
                tier=p.tier,
                matched_statute=p.statute,
                matched_pattern_note=p.note,
                matched_weight=p.weight,
                match_excerpt=_match_excerpt(post.text, p.pattern),
            )
            if best is None:
                best = candidate
            else:
                # Lower tier number = more severe in our convention
                # (3 is worst, 1 is informational). Pick the lowest.
                if candidate.tier > best.tier:
                    best = candidate
                elif candidate.tier == best.tier and candidate.matched_weight > best.matched_weight:
                    best = candidate
        if best:
            findings.append(best)

    # Sort by tier desc (3 first), then by weight desc, then by timestamp desc
    findings.sort(key=lambda f: (-f.tier, -f.matched_weight, -f.timestamp))

    summary = {
        "total_posts_scanned": total_scanned,
        "tier_3_count": sum(1 for f in findings if f.tier == 3),
        "tier_2_count": sum(1 for f in findings if f.tier == 2),
        "tier_1_count": sum(1 for f in findings if f.tier == 1),
        "total_findings": len(findings),
    }

    return {
        "summary": summary,
        "tier_labels": TIER_LABELS,
        "tier_disclaimers": TIER_DISCLAIMERS,
        "findings": [asdict(f) for f in findings],
    }


# ----------------------------------------------------------------------------
# Top-level convenience
# ----------------------------------------------------------------------------

def run_fb_scan(payload: Any) -> Dict[str, Any]:
    raw_posts = load_export(payload)
    posts = [Post.from_export(p) for p in raw_posts]
    return score_posts(posts)


# ----------------------------------------------------------------------------
# Self-test
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "fb_export_sample.json")
    if not os.path.exists(fixture):
        print("No fixture. Run fixtures/generate_fixture.py first.")
    else:
        with open(fixture, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        result = run_fb_scan(data)
        print(json.dumps(result["summary"], indent=2))
        print()
        for f in result["findings"][:10]:
            print(f"  T{f['tier']} | {f['matched_statute']} | w={f['matched_weight']:.2f}")
            print(f"    {f['text_excerpt'][:120]}")
            print(f"    match: ...{f['match_excerpt']}...")
            print()
