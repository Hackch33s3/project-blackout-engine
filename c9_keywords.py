"""
Canadian-law keyword + pattern reference for the Project Blackout FB scan.

SCOPE: Conservative. Flags only content plausibly within the scope of the
following statutes as understood from publicly available text of the bills
and the current Criminal Code:

  - Bill C-9 / Online Harms Act (Parliament of Canada, 2024-2025 session text)
  - Criminal Code s.319 (public incitement of hatred, willful promotion)
  - Criminal Code s.83.218 - s.83.231 (terrorist activity, financing, recruitment)
  - Canadian Human Rights Act s.13 (hate messages, repealed 2013 — INCLUDED FOR
    historical reference only; NOT enforced, included so the engine can
    distinguish "previously actionable" from "currently actionable")

This list is intentionally SMALL. False positives destroy trust with the
customer and create defamation exposure for the operator. Every pattern is
mapped to a specific statute section so the report can cite the law, not
paraphrase it.

This is NOT legal advice. The output of the engine is informational scoring
against the patterns defined here, nothing more. Customers are referred to a
licensed Canadian attorney for any actual legal question.
"""

from dataclasses import dataclass
from typing import List, Pattern
import re


@dataclass(frozen=True)
class KeywordPattern:
    """A single scoring pattern.

    tier:       1 (informational) | 2 (potential issue) | 3 (matches statute)
    statute:    human-readable citation, e.g. "C-9 s.4(1)(b)"
    pattern:    compiled regex, case-insensitive
    weight:     0.0-1.0, contribution within the tier for sorting
    note:       short explanation shown in the report
    """
    tier: int
    statute: str
    pattern: Pattern
    weight: float
    note: str


# ----------------------------------------------------------------------------
# Tier 3 — direct statute hits. Reserved for content that, on its face,
# matches the elements of an indictable offence. The customer MUST be
# referred to counsel.
# ----------------------------------------------------------------------------

_T3_RAW: List[tuple] = [
    # ---- Criminal Code s.83.222 — terrorist propaganda / recruitment ----
    (3, "CC s.83.222(1)(a)", r"\b(join|fight for|recruit(?:ing)?|enlist)\b.{0,40}\b(isis|isil|al[- ]?qaeda|al[- ]?shabaab|hamas|hezbollah|boko haram|taliban|terror(?:ist)? (?:group|cell|organization))\b",
     0.95, "Possible recruitment / encouragement to participate in terrorist activity"),
    (3, "CC s.83.222(1)(b)", r"\b(committing|carry out|carry out|planning|plan a) (a |an )?(terrorist|attack|bombing|massacre|shooting)\b",
     0.95, "Possible counselling to commit a terrorist offence"),
    (3, "CC s.83.222(1)(c)", r"\b(how to|instructions for|recipe for|build a|make a)\b.{0,40}\b(bomb|ied|explosive|poison|nerve agent|bioweapon)\b",
     0.90, "Possible instruction on weapon / explosive manufacture"),

    # ---- Criminal Code s.83.221 — providing / collecting property for terror ----
    (3, "CC s.83.221", r"\b(donate|send|wire|transfer|fund|financ(?:e|ing))\b.{0,40}\b(isis|isil|al[- ]?qaeda|hamas|hezbollah|taliban|terror(?:ist)? (?:group|cell|cause))\b",
     0.90, "Possible terrorist property / financing"),

    # ---- Criminal Code s.319(2) — willful promotion of hatred ----
    (3, "CC s.319(2)", r"\b(genocide|exterminate|eradicate|kill|eliminate|should die|must die|deserve to die)\b.{0,40}\b(jews|muslims|christians|hindus|sikhs|buddhists|immigrants|refugees|blacks|whites|asians|indigenous|aboriginal|queer|gay|trans|lesbian|faggots|niggers|kikes|spics|chinks|pakis|trannies|retards)\b",
     0.90, "Possible incitement / willful promotion of hatred against an identifiable group"),

    # ---- Online Harms Act / Bill C-9 — content categories (s.6 categories) ----
    (3, "C-9 s.6(1) cat.1", r"\b(child sexual|child porn|cp|underage sex|minor sex|jailbait|loli)\b",
     0.99, "Possible child sexual abuse material — REFERRAL TO LAW ENFORCEMENT RECOMMENDED"),
    (3, "C-9 s.6(1) cat.3", r"\b(live stream|livestream|broadcast)\b.{0,40}\b(suicide|self[- ]?harm)\b",
     0.85, "Possible broadcast of self-harm content"),
    (3, "C-9 s.6(1) cat.4", r"\b(advice|how to|methods of|ways to)\b.{0,40}\b(commit suicide|kill yourself|end your life)\b",
     0.80, "Possible suicide instruction / encouragement"),
]


# ----------------------------------------------------------------------------
# Tier 2 — potential issue. Content that does NOT necessarily violate a
# statute but is high-attention-getting under the new Canadian regime:
# political vitriol, anti-government rhetoric, immigration scepticism
# bordering on dehumanisation. Engine flags so the user can decide.
# ----------------------------------------------------------------------------

_T2_RAW: List[tuple] = [
    # Anti-government / political — short of incitement, beyond normal politics
    (2, "CC s.319(2) (context)", r"\b(treason|treasonous|treacherous)\b.{0,40}\b(government|pm|trudeau|poilievre|freeland|minister|premier)\b",
     0.55, "Use of 'treason' framing against elected officials — context-dependent"),
    (2, "C-9 s.6(1) (context)", r"\b(tyrann(?:y|ical)|dictatorship|fascist|fascism|nazi)\b.{0,40}\b(trudeau|poilievre|government|canada|liberals|conservatives|ndp)\b",
     0.50, "Dehumanising comparison of Canadian elected officials — protected expression but high-attention"),

    # Immigration / refugee dehumanisation (short of s.319)
    (2, "CC s.319(2) (context)", r"\b(invasion|infest(?:ed|ation)|swarms?|plague|vermin|cockroaches?|parasites?)\b.{0,40}\b(immigrants|refugees|migrants|asylum seekers|newcomers)\b",
     0.65, "Dehumanising framing of immigrants / refugees — flagged under s.319 risk"),
    (2, "CC s.319(2) (context)", r"\b(deport(?:ation)? all|send them all back|close the border|shut the border)\b",
     0.40, "Strong anti-immigration rhetoric — protected expression, included for visibility"),

    # Public-health / public-officer threat-adjacent (not direct threat)
    (2, "CC s.264.1 (context)", r"\b(hang|lynch|shot at|executed at|public hanging|need a (?:hang|rope|wall))\b.{0,40}\b(trudeau|poilievre|fauci|public health|health officer|premier|minister)\b",
     0.75, "Threatening / violent imagery against a public official or officer"),

    # Recognised extremist signals (public CSIS / RCMP advisories, public-facing only)
    (2, "CSIS public advisory", r"\b(14/88|1488|boogaloo|accelerationism|accelerationist|day of the rope|white ethnostate|replacement theory|great replacement)\b",
     0.85, "Recognised extremist slogan / framing"),

    # Conspiracy / "Freeman-on-the-land" sovereign-citizen style — context only
    (2, "Context flag", r"\b(sovereign citizen|freeman on the land|standing army|maritime law|common law court|one people(?:'s)? tribunal)\b",
     0.35, "Sovereign-citizen / pseudolaw framing — flag for visibility, not criminal"),
]


# ----------------------------------------------------------------------------
# Tier 1 — informational. Low-risk political / religious / general content
# the user might want to review before, e.g., a job search or PR event.
# Not flagged for legal risk; flagged for personal-hygiene reasons.
# ----------------------------------------------------------------------------

_T1_RAW: List[tuple] = [
    (1, "Personal-hygiene", r"\b(shitpost|shit posting|drunk at|work was|my boss|fired|quit my job)\b",
     0.20, "Casual venting — consider for personal-hygiene cleanup"),
    (1, "Personal-hygiene", r"\b(ex|ex[- ]girlfriend|ex[- ]boyfriend|ex wife|ex husband|crazy ex|blocked by)\b",
     0.25, "Personal relationships — consider for personal-hygiene cleanup"),
    (1, "Personal-hygiene", r"\b(stupid (?:coworker|colleague|manager|client|customer)|asshole|fuck you)\b",
     0.15, "Workplace / interpersonal venting"),
]


# ----------------------------------------------------------------------------
# Compile
# ----------------------------------------------------------------------------

def _compile_all() -> List[KeywordPattern]:
    out: List[KeywordPattern] = []
    for src in (_T3_RAW, _T2_RAW, _T1_RAW):
        for tier, statute, pat, weight, note in src:
            out.append(KeywordPattern(
                tier=tier,
                statute=statute,
                pattern=re.compile(pat, re.IGNORECASE | re.UNICODE),
                weight=weight,
                note=note,
            ))
    return out


PATTERNS: List[KeywordPattern] = _compile_all()
PATTERNS_BY_TIER = {1: [], 2: [], 3: []}
for p in PATTERNS:
    PATTERNS_BY_TIER[p.tier].append(p)


# ----------------------------------------------------------------------------
# Public data
# ----------------------------------------------------------------------------

TIER_LABELS = {
    1: "Probably not concerning",
    2: "Potentially problematic — review recommended",
    3: "Blatantly anti-government / immigration / matches statute — referral recommended",
}

TIER_DISCLAIMERS = {
    1: "These items are informational. They are flagged for personal-hygiene review, not legal exposure.",
    2: "These items do not necessarily violate a Canadian statute, but may attract attention under the Online Harms Act (Bill C-9) and related provisions. Review for context.",
    3: "These items appear to match the elements of a Canadian criminal offence. This report is NOT legal advice. Project Blackout strongly recommends that you consult a licensed Canadian attorney before taking or refraining from any action.",
}


if __name__ == "__main__":
    # quick sanity check
    print(f"Loaded {len(PATTERNS)} patterns")
    for tier in (3, 2, 1):
        print(f"  Tier {tier}: {len(PATTERNS_BY_TIER[tier])} patterns")
