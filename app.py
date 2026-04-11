"""
AlgoGuard — FastAPI Backend
Endpoints:
  GET  /              → dashboard
  GET  /api/state     → current state of all 3 synthetic users
  POST /api/tick      → advance all users one session
  POST /api/reset     → reset all users to session 0
  POST /api/analyze   → Claude-powered feature audit
  GET  /report/{uid}  → printable audit report for one user
"""

import os
import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import anthropic

from simulator import tick_all, get_all_states, reset_all, USERS

load_dotenv()

app = FastAPI(title="AlgoGuard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# In-memory store for latest states and audit results
_latest_states: list = []
_audit_results: dict = {}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    states = get_all_states()
    return templates.TemplateResponse("dashboard.html", {"request": request, "users": states})


@app.get("/api/state")
async def api_state():
    states = get_all_states()
    return JSONResponse(content=states)


@app.post("/api/tick")
async def api_tick():
    states = tick_all()
    global _latest_states
    _latest_states = states
    return JSONResponse(content=states)


@app.post("/api/reset")
async def api_reset():
    reset_all()
    return JSONResponse(content={"status": "reset"})


@app.post("/api/analyze")
async def api_analyze(request: Request):
    body = await request.json()
    platform_name = body.get("platform_name", "Unknown Platform")
    features = body.get("features", "")

    prompt = f"""You are AlgoGuard, an AI compliance auditor specializing in social media algorithm addiction risk.

Analyze the following platform features for addiction-risk patterns using the RIS (Reflexive/Intentional Spectrum) framework.

Platform: {platform_name}
Features described: {features}

RIS Framework metrics to consider:
- SVG (Session Velocity Gradient): Does the design accelerate or sustain rapid scrolling?
- DDR (Dwell-to-Dismiss Ratio): Does it reduce deliberate content engagement?
- RLI (Re-entry Latency Index): Does it encourage compulsive app re-opening?
- NSCR (Notification-to-Session Conversion Rate): Does it use notifications to drive compulsive sessions?
- ACS (Affective Content Score): Does the algorithm drift toward high-arousal negative content?

Legal frameworks to flag:
- KOSA (Kids Online Safety Act): special protections for minors
- DSA (EU Digital Services Act): systemic risk and transparency requirements
- MA 93A: unfair/deceptive practices, triple damages
- CCPA/CPRA: behavioral profiling and opt-out rights
- UK Online Safety Act: child safety duty of care

Respond ONLY with valid JSON in this exact format:
{{
  "risk_score": <integer 0-100>,
  "risk_level": "<HIGH|MEDIUM|LOW>",
  "flagged_patterns": [
    {{"pattern": "<name>", "metric": "<SVG|DDR|RLI|NSCR|ACS>", "severity": "<HIGH|MEDIUM|LOW>", "description": "<one sentence>"}}
  ],
  "legal_exposure": [
    {{"framework": "<law name>", "risk": "<HIGH|MEDIUM|LOW>", "detail": "<one sentence>"}}
  ],
  "remediation": [
    "<actionable recommendation>"
  ],
  "summary": "<2-3 sentence plain English summary for executives>"
}}"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw)
    result["platform_name"] = platform_name
    _audit_results[platform_name] = result
    return JSONResponse(content=result)


@app.get("/report/{platform_name}", response_class=HTMLResponse)
async def report(request: Request, platform_name: str):
    audit = _audit_results.get(platform_name, {})
    return templates.TemplateResponse("report.html", {
        "request": request,
        "audit": audit,
        "platform_name": platform_name,
    })
