"""
PDF report generator for the Project Blackout C-9 risk scan.

Pure ReportLab — no WeasyPrint, no Playwright, no system deps beyond
what the existing Dockerfile already pulls for Chromium.

LAYOUT
  Page 1 — cover: scan name, customer name, date, headline summary
  Page 2 — methodology: what statutes we scored against, what we did
            NOT score against, the disclaimer (NOT legal advice)
  Page 3+ — per-tier findings, sorted tier 3 first
  Final   — deletion plan, in the order the customer should work them

The PDF is the deliverable. Customers do not see the JSON.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT

from c9_keywords import TIER_LABELS, TIER_DISCLAIMERS
from deletion_planner import build_steps, DeletionStep


# ----------------------------------------------------------------------------
# Styles
# ----------------------------------------------------------------------------

styles = getSampleStyleSheet()

STYLE_COVER_TITLE = ParagraphStyle(
    "CoverTitle", parent=styles["Title"],
    fontSize=28, leading=34, textColor=colors.HexColor("#0a0a0a"),
    spaceAfter=12, alignment=TA_LEFT,
)
STYLE_H1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontSize=18, leading=22, textColor=colors.HexColor("#0a0a0a"),
    spaceBefore=18, spaceAfter=8,
)
STYLE_H2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontSize=14, leading=18, textColor=colors.HexColor("#1a1a1a"),
    spaceBefore=12, spaceAfter=6,
)
STYLE_BODY = ParagraphStyle(
    "Body", parent=styles["BodyText"],
    fontSize=10.5, leading=14, textColor=colors.HexColor("#222222"),
    spaceAfter=6, alignment=TA_LEFT,
)
STYLE_DISCLAIMER = ParagraphStyle(
    "Disclaimer", parent=styles["BodyText"],
    fontSize=9, leading=12, textColor=colors.HexColor("#666666"),
    spaceAfter=6, alignment=TA_LEFT,
)
STYLE_SMALL = ParagraphStyle(
    "Small", parent=styles["BodyText"],
    fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"),
    spaceAfter=4, alignment=TA_LEFT,
)
STYLE_TIER_LABEL = {
    1: ParagraphStyle("T1", parent=STYLE_H2, textColor=colors.HexColor("#3b6e3b")),
    2: ParagraphStyle("T2", parent=STYLE_H2, textColor=colors.HexColor("#a05a00")),
    3: ParagraphStyle("T3", parent=STYLE_H2, textColor=colors.HexColor("#8a1c1c")),
}
STYLE_TIER_BG = {
    1: colors.HexColor("#eef6ee"),
    2: colors.HexColor("#fbf2e3"),
    3: colors.HexColor("#fbeaea"),
}


# ----------------------------------------------------------------------------
# Cover
# ----------------------------------------------------------------------------

def _cover_block(customer_name: str, summary: Dict[str, int]) -> List[Any]:
    scan_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story = [
        Spacer(1, 1.0 * inch),
        Paragraph("Project Blackout", STYLE_COVER_TITLE),
        Paragraph("C-9 Risk Scan — Personal Facebook Profile", STYLE_H1),
        Spacer(1, 0.3 * inch),
        Paragraph(f"<b>Prepared for:</b> {customer_name or 'Anonymous'}", STYLE_BODY),
        Paragraph(f"<b>Scan date:</b> {scan_date}", STYLE_BODY),
        Paragraph(f"<b>Posts scanned:</b> {summary.get('total_posts_scanned', 0)}", STYLE_BODY),
        Spacer(1, 0.3 * inch),
        Paragraph("Headline summary", STYLE_H2),
    ]

    table_data = [
        ["Tier", "Label", "Count"],
        ["3", "Statute-level matches (C-9 / CC s.319 / s.83)", str(summary.get("tier_3_count", 0))],
        ["2", "Potentially problematic — review recommended", str(summary.get("tier_2_count", 0))],
        ["1", "Informational / personal-hygiene", str(summary.get("tier_1_count", 0))],
        ["", "TOTAL FLAGGED", str(summary.get("total_findings", 0))],
    ]
    t = Table(table_data, colWidths=[0.6 * inch, 4.0 * inch, 1.0 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a1a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f4f4f4"), colors.white]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eeeeee")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "This report is informational scoring only. It is not legal advice and "
        "creates no attorney-client relationship. Project Blackout is not a law "
        "firm. Consult a licensed Canadian attorney before acting on any item "
        "in this report.",
        STYLE_DISCLAIMER,
    ))
    story.append(PageBreak())
    return story


# ----------------------------------------------------------------------------
# Methodology
# ----------------------------------------------------------------------------

def _methodology_block() -> List[Any]:
    story = [
        Paragraph("Methodology", STYLE_H1),
        Paragraph(
            "Project Blackout scored the text of every post in your Facebook "
            "data export against a curated set of patterns mapped to specific "
            "Canadian statutes. The patterns are conservative — they are "
            "designed to err on the side of missing questionable content rather "
            "than over-flagging protected political or religious expression.",
            STYLE_BODY,
        ),
        Paragraph("Statutes referenced", STYLE_H2),
        Paragraph(
            "• <b>Bill C-9 / Online Harms Act</b> — content categories in proposed s.6(1).",
            STYLE_BODY,
        ),
        Paragraph(
            "• <b>Criminal Code s.319</b> — public incitement of hatred, "
            "willful promotion of hatred against an identifiable group.",
            STYLE_BODY,
        ),
        Paragraph(
            "• <b>Criminal Code s.83.218–83.231</b> — terrorist activity, "
            "recruitment, propaganda, financing.",
            STYLE_BODY,
        ),
        Paragraph(
            "• <b>CSIS / RCMP public advisories</b> — publicly-named extremist "
            "slogans and framings (advisory only; not all of these are criminal).",
            STYLE_BODY,
        ),
        Paragraph("What we did NOT score", STYLE_H2),
        Paragraph(
            "• Images and video frames (text only).<br/>"
            "• Comments made on other people's posts (your export may or may "
            "not include them depending on what you selected).<br/>"
            "• DMs / Messenger conversations (separate download, separate "
            "handling).<br/>"
            "• Public-record context (court rulings, news reports) — context "
            "is your responsibility to add.",
            STYLE_BODY,
        ),
        Paragraph("Three tiers", STYLE_H2),
        Paragraph("<b>Tier 1 — Probably not concerning.</b> Informational; "
                  "flagged for personal-hygiene reasons (venting, personal "
                  "relationships, work).", STYLE_BODY),
        Paragraph("<b>Tier 2 — Potentially problematic.</b> Does not "
                  "necessarily violate a statute but may attract attention "
                  "under the new Canadian regime. Review for context.", STYLE_BODY),
        Paragraph("<b>Tier 3 — Statute-level match.</b> The text matches the "
                  "elements of a Canadian criminal offence on its face. We "
                  "strongly recommend consulting a licensed Canadian attorney.", STYLE_BODY),
        Paragraph(
            "<i>This report is the product. The deletion plan on the final "
            "pages lists every flagged post with instructions to remove it "
            "via Facebook's Activity Log.</i>",
            STYLE_DISCLAIMER,
        ),
        PageBreak(),
    ]
    return story


# ----------------------------------------------------------------------------
# Findings
# ----------------------------------------------------------------------------

def _finding_paragraphs(f: Dict[str, Any]) -> List[Any]:
    from datetime import datetime, timezone
    ts = int(f.get("timestamp") or 0)
    ts_h = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if ts else "unknown date"

    story = []
    # Header line
    header = f"<b>Tier {f.get('tier')}</b> — {f.get('matched_statute','')}"
    story.append(Paragraph(header, STYLE_SMALL))
    story.append(Paragraph(
        f"<b>Date:</b> {ts_h} &nbsp;&nbsp; <b>Post ID:</b> {f.get('post_id','n/a')}", STYLE_SMALL))
    story.append(Paragraph(f"<b>Why flagged:</b> {f.get('matched_pattern_note','')}", STYLE_BODY))
    story.append(Paragraph("<b>Post text:</b>", STYLE_SMALL))
    story.append(Paragraph(f.get("text_excerpt","").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"), STYLE_BODY))
    excerpt = f.get("match_excerpt","").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    if excerpt:
        story.append(Paragraph(f"<b>Matched phrase:</b> …{excerpt}…", STYLE_SMALL))
    if f.get("permalink"):
        link = f.get("permalink").replace("&","&amp;")
        story.append(Paragraph(f"<b>Original post:</b> {link}", STYLE_SMALL))
    story.append(Spacer(1, 0.12 * inch))
    return story


def _findings_block(findings: List[Dict[str, Any]]) -> List[Any]:
    story = [Paragraph("Findings by tier", STYLE_H1)]

    # Group by tier, highest first
    for tier in (3, 2, 1):
        tier_findings = [f for f in findings if f.get("tier") == tier]
        if not tier_findings:
            continue

        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(
            f"Tier {tier} — {TIER_LABELS.get(tier,'')}",
            STYLE_TIER_LABEL.get(tier, STYLE_H2),
        ))
        story.append(Paragraph(TIER_DISCLAIMERS.get(tier, ""), STYLE_DISCLAIMER))

        for f in tier_findings:
            block = _finding_paragraphs(f)
            # Wrap each finding in a coloured background table
            inner = []
            for el in block:
                inner.append(el)
            # Convert the list of flowables into a single-cell table for tinting
            t = Table([[inner]], colWidths=[6.5 * inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), STYLE_TIER_BG.get(tier, colors.whitesmoke)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.06 * inch))

    story.append(PageBreak())
    return story


# ----------------------------------------------------------------------------
# Deletion plan
# ----------------------------------------------------------------------------

def _deletion_block(steps: List[DeletionStep]) -> List[Any]:
    story = [
        Paragraph("Deletion plan", STYLE_H1),
        Paragraph(
            "Facebook has no public API for post deletion. Execute these steps "
            "manually via your Activity Log. If you'd like a Project Blackout "
            "operator to walk you through this on a screenshare, reply to the "
            "delivery email and we'll book a session.",
            STYLE_BODY,
        ),
        Spacer(1, 0.15 * inch),
    ]
    if not steps:
        story.append(Paragraph(
            "No items flagged — nothing to delete. Your profile is clean per "
            "the Project Blackout scoring set.",
            STYLE_BODY,
        ))
        return story

    for i, step in enumerate(steps, 1):
        lines = [f"<b>{i}.</b> {step.timestamp_human}"]
        lines.append(step.text_excerpt.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
        for ins in step.instructions:
            lines.append("&nbsp;&nbsp;• " + ins.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
        story.append(Paragraph("<br/>".join(lines), STYLE_SMALL))
        story.append(Spacer(1, 0.08 * inch))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(
        "<b>Final note.</b> Deleting a post removes it from public view. It does "
        "not retroactively un-prosecute any prior offence, and the recipient of "
        "the original post (e.g., a government agency) may have already cached "
        "a copy. This plan is risk-mitigation, not legal remediation.",
        STYLE_DISCLAIMER,
    ))
    return story


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def generate_report(
    customer_name: str,
    scan_result: Dict[str, Any],
    deletion_steps: Optional[List[DeletionStep]] = None,
) -> bytes:
    """Render the PDF, return raw bytes. Caller writes / emails."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title="Project Blackout — C-9 Risk Scan",
        author="Project Blackout",
    )
    findings: List[Dict[str, Any]] = scan_result.get("findings", [])
    summary = scan_result.get("summary", {})

    if deletion_steps is None:
        deletion_steps = build_steps(findings)

    story = []
    story += _cover_block(customer_name, summary)
    story += _methodology_block()
    story += _findings_block(findings)
    story += _deletion_block(deletion_steps)

    doc.build(story)
    return buf.getvalue()


if __name__ == "__main__":
    print("report_generator module. Import to use.")
