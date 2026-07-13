from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import os
import json
import tempfile
from typing import List, Optional
from dotenv import load_dotenv

from scanner import run_scan  # heavy: playwright, used by data-broker scan
from facebook_scan import run_fb_scan
from report_generator import generate_report
from deletion_planner import (
    build_steps, plan_for_keyword, plan_for_categories, plan_for_clear_all
)

load_dotenv()

app = FastAPI(title="Project Blackout Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ENGINE_API_KEY = os.getenv("ENGINE_API_KEY")


# ----------------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------------

async def verify_api_key(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.replace("Bearer ", "")
    if token != ENGINE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token


# ----------------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"status": "ok", "service": "project-blackout-engine"}


# ----------------------------------------------------------------------------
# Existing: data-broker scan
# ----------------------------------------------------------------------------

class ScanRequest(BaseModel):
    clientId: str
    full_name: str
    past_city: str
    tier: str = "full"  # "free" = 5-broker teaser, "full" = all brokers


class StopScanRequest(BaseModel):
    clientId: str


@app.post("/start-scan")
async def start_scan(request: ScanRequest, api_key: str = Depends(verify_api_key)):
    try:
        print(f"[+] Data-broker scan triggered for client: {request.clientId} (tier={request.tier})")
        result = await run_scan(
            client_id=request.clientId,
            full_name=request.full_name,
            past_city=request.past_city,
            tier=request.tier,
        )
        return {
            "status": "success",
            "client_id": request.clientId,
            "targets_found": len(result.get("targets", [])),
            "targets": result.get("targets", []),
        }
    except Exception as e:
        print(f"[-] Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop-scan")
async def stop_scan(request: StopScanRequest, api_key: str = Depends(verify_api_key)):
    print(f"[!] Stop-scan requested for client: {request.clientId}")
    return {"status": "stopped", "client_id": request.clientId}


# ----------------------------------------------------------------------------
# New: Facebook post scan + report
# ----------------------------------------------------------------------------

# Form fields for the upload. The customer's name is optional and used only
# for the PDF cover; the export itself is the only required payload.
#
# `mode` controls what comes back:
#   "scan"  -> JSON findings only
#   "report" -> PDF report (full)
#   "plan"   -> PDF report, deletion-plan only, filtered by `keyword`
#                or `categories`
#
# `keyword` is a free-text filter (case-insensitive) used by plan mode.
# `categories` is a comma-separated list. Allowed: political, religious, hateful.
# `all_posts` is "true" if you want the plan to also include non-flagged posts
#              that match the filter (default: true).

ALLOWED_CATEGORIES = {"political", "religious", "hateful"}


def _parse_export_payload(raw: bytes) -> dict:
    """Read a FB export JSON, return a normalised dict of posts.

    Accepts either a raw JSON list of post objects or the nested FB ZIP
    shape (a dict with a top-level posts/status_updates key). Raises
    ValueError on unrecognised shape.
    """
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"Export is not valid UTF-8 JSON: {e}")
    return payload


@app.post("/fb-scan")
async def fb_scan(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
):
    """Score a Facebook export and return JSON findings.

    The caller is responsible for any retention / deletion of the upload.
    This endpoint reads the bytes, scores, and forgets.
    """
    try:
        raw = await file.read()
        payload = _parse_export_payload(raw)
        result = run_fb_scan(payload)
        return {
            "status": "success",
            "filename": file.filename,
            "summary": result["summary"],
            "tier_labels": result["tier_labels"],
            "findings": result["findings"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[-] FB scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fb-report")
async def fb_report(
    file: UploadFile = File(...),
    customer_name: str = Form("Anonymous"),
    keyword: Optional[str] = Form(None),
    categories: Optional[str] = Form(None),
    api_key: str = Depends(verify_api_key),
):
    """Score a Facebook export and return a PDF.

    The PDF always contains the full score breakdown. The deletion plan
    section is filtered by `keyword` or `categories` if provided; if
    neither is given, the plan covers every finding.
    """
    try:
        raw = await file.read()
        payload = _parse_export_payload(raw)
        result = run_fb_scan(payload)
        findings = result["findings"]

        # Build raw-posts list for category / keyword scans
        from facebook_scan import load_export, Post
        raw_posts_objs = load_export(payload)
        raw_posts = [
            {
                "post_id": p.post_id,
                "timestamp": p.timestamp,
                "text_excerpt": p.text[:280] if p.text else "",
                "permalink": p.permalink,
            }
            for p in [Post.from_export(o) for o in raw_posts_objs]
        ]

        # Decide the deletion plan
        if keyword:
            steps = plan_for_keyword(findings, keyword, all_posts=raw_posts)
        elif categories:
            cat_list = [c.strip().lower() for c in categories.split(",") if c.strip()]
            bad = [c for c in cat_list if c not in ALLOWED_CATEGORIES]
            if bad:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown categories: {bad}. Allowed: {sorted(ALLOWED_CATEGORIES)}",
                )
            steps = plan_for_categories(findings, cat_list, all_posts=raw_posts)
        else:
            steps = build_steps(findings)

        pdf_bytes = generate_report(
            customer_name=customer_name,
            scan_result=result,
            deletion_steps=steps,
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="project-blackout-c9-report.pdf"',
                "X-Summary-Tier3": str(result["summary"]["tier_3_count"]),
                "X-Summary-Tier2": str(result["summary"]["tier_2_count"]),
                "X-Summary-Tier1": str(result["summary"]["tier_1_count"]),
                "X-Summary-Total": str(result["summary"]["total_findings"]),
                "X-Deletion-Steps": str(len(steps)),
            },
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[-] FB report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
