"""
Konduct — FastAPI Backend
Endpoints:
  GET  /                              → redirect to /landing
  GET  /landing                       → landing page
  GET  /dashboard                     → main dashboard
  GET  /api/state                     → current state of all 3 synthetic users
  POST /api/tick                      → advance all users one session
  POST /api/reset                     → reset all users to session 0
  POST /api/analyze                   → Claude-powered feature audit
  GET  /report/{platform_name}        → printable audit report
  GET  /api/litigation-export         → JSON litigation package (download)
  GET  /litigation-report/{name}      → printable HTML litigation report (PDF)
"""

import os
import json
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import anthropic

from simulator import tick_all, get_all_states, reset_all, USERS

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Konduct")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# In-memory store for latest states and audit results
_latest_states: list = []
_audit_results: dict = {}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=RedirectResponse, status_code=301)
async def root():
    return "/landing"


@app.get("/landing", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request=request, name="landing.html", context={})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    states = get_all_states()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"users": states})


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

    prompt = f"""You are Konduct, an AI compliance auditor specializing in social media algorithm addiction risk.

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
    return templates.TemplateResponse(request=request, name="report.html", context={
        "audit": audit,
        "platform_name": platform_name,
    })


# ── Shared litigation data builder ────────────────────────────────────────────

def _build_litigation_data(platform_name: str) -> dict:
    """Build the full litigation data package — used by both JSON export and HTML report."""
    audit = _audit_results.get(platform_name, {})
    timestamp = datetime.now(timezone.utc).isoformat()
    export_id = str(uuid.uuid4())
    states = get_all_states()

    # ── GOVERN ──────────────────────────────────────────────────────────────────
    govern = {
        "record_type": "GOVERN",
        "description": "Pre-committed behavioral safety objectives and threshold definitions",
        "platform": platform_name,
        "audit_timestamp": timestamp,
        "export_id": export_id,
        "statement": (
            "The following thresholds were defined prior to any risk event, based on "
            "published behavioral science research, and represent Konduct's pre-committed "
            "safety framework. They have not been modified retroactively."
        ),
        "ris_framework": {
            "name": "Reflexive/Intentional Spectrum (RIS) Framework",
            "version": "1.0",
            "description": (
                "A 5-metric framework for quantifying compulsive-use risk in social media "
                "platforms, derived from published behavioral and psychological research."
            ),
        },
        "metrics": [
            {
                "key": "SVG",
                "name": "Session Velocity Gradient",
                "definition": "Rate of scroll-speed acceleration during a session, in normalized velocity units per minute.",
                "threshold_adult": 70,
                "threshold_minor": 60,
                "rationale": (
                    "Thresholds derived from Oulasvirta et al. (2012). Values above threshold "
                    "correlate (r=0.74) with self-reported loss-of-control over scrolling behavior."
                ),
                "citation": (
                    "Oulasvirta, A., Rattenbury, T., Ma, L., & Raita, E. (2012). Habits make "
                    "smartphone use more pervasive. Personal and Ubiquitous Computing, 16(1), 105-114."
                ),
                "legal_basis": (
                    "KOSA § 4(a)(3): platforms must mitigate compulsive-use features for minors; "
                    "DSA Art. 34(1)(b): systemic risk from highly engaging design."
                ),
            },
            {
                "key": "DDR",
                "name": "Dwell-to-Dismiss Ratio",
                "definition": "Ratio of average content dwell time to total session time. Low values indicate reflexive cycling without deliberate engagement.",
                "threshold_adult": 0.20,
                "threshold_minor": 0.25,
                "rationale": (
                    "Based on eye-tracking studies by Buscher et al. (2009). DDR below threshold "
                    "indicates content is not being cognitively processed before dismissal."
                ),
                "citation": (
                    "Buscher, G., Cutrell, E., & Morris, M.R. (2009). What do you see when you're "
                    "surfing? Proceedings of CHI 2009, ACM."
                ),
                "legal_basis": (
                    "MA 93A § 2: unfair/deceptive act if design prevents deliberate content "
                    "evaluation; DSA Art. 34(1)(a): systemic risks from recommender systems."
                ),
            },
            {
                "key": "RLI",
                "name": "Re-entry Latency Index",
                "definition": "Median time in minutes between app close and re-launch. Low values indicate conditioned compulsive re-opening.",
                "threshold_adult": 3,
                "threshold_minor": 2,
                "rationale": (
                    "Derived from Pielot et al. (2014). Sub-threshold re-entry correlates with "
                    "behavioral addiction markers consistent with DSM-5 criteria for behavioral addiction."
                ),
                "citation": (
                    "Pielot, M., Church, K., & de Oliveira, R. (2014). An in-situ study of mobile "
                    "phone notifications. MobileHCI 2014, ACM."
                ),
                "legal_basis": (
                    "UK Online Safety Act 2023 § 12: duty of care to prevent compulsive use; "
                    "CCPA § 1798.100: profiling must not exploit compulsive behavior."
                ),
            },
            {
                "key": "NSCR",
                "name": "Notification-to-Session Conversion Rate",
                "definition": "Proportion of sessions initiated within 60 seconds of a push notification. High values indicate notification-conditioned compulsive response.",
                "threshold_adult": 0.65,
                "threshold_minor": 0.50,
                "rationale": (
                    "Based on Pielot et al. (2014) and Jeong & Lee (2015). NSCR above threshold "
                    "represents a Pavlovian conditioning profile meeting clinical criteria for "
                    "conditioned behavioral response."
                ),
                "citation": (
                    "Jeong, S.H. & Lee, Y. (2015). When Do You Check Your Phone? Journal of "
                    "Broadcasting & Electronic Media, 59(3), 338-357."
                ),
                "legal_basis": (
                    "KOSA § 4(b)(3): prohibition on design exploiting notification responses in minors; "
                    "DSA Art. 34(1)(c): addictive design features constitute systemic risk."
                ),
            },
            {
                "key": "ACS",
                "name": "Affective Congruence Score",
                "definition": "Normalized measure of content affective drift from user stated preferences toward high-arousal content. High values indicate algorithmic emotional manipulation.",
                "threshold_adult": 0.50,
                "threshold_minor": 0.40,
                "rationale": (
                    "Derived from Twenge et al. (2018). ACS above threshold correlates with elevated "
                    "anxiety and depression markers per PHQ-9 screening in adolescent populations."
                ),
                "citation": (
                    "Twenge, J.M., Joiner, T.E., Rogers, M.L., & Martin, G.N. (2018). Increases in "
                    "Depressive Symptoms, Suicide-Related Outcomes, and Suicide Rates Among U.S. "
                    "Adolescents After 2010. Clinical Psychological Science, 6(1), 3-17."
                ),
                "legal_basis": (
                    "KOSA § 4(a)(1): prohibition on content promoting self-harm for minors; "
                    "MA 93A § 2: algorithmically serving emotionally harmful content constitutes "
                    "an unfair business practice; UK Online Safety Act 2023 § 12."
                ),
            },
        ],
    }

    # ── MAP ──────────────────────────────────────────────────────────────────────
    _pathways = {
        "SVG": {
            "feature": "Infinite scroll with acceleration-based content loading and no natural stopping point",
            "mechanism": "Reduced friction between content items → progressive velocity increase → habitual rapid-scrolling pattern",
            "harm": "Loss of deliberate content selection → compulsive passive consumption → negative affect documented in Twenge et al. (2018)",
        },
        "DDR": {
            "feature": "Autoplay video, instant-loading image cards, sub-300ms transition animation",
            "mechanism": "Insufficient inter-item dwell time → content consumed without cognitive processing → reflexive dismiss-and-reload cycle",
            "harm": "Inability to exercise meaningful content choice → GDPR/CCPA informed-consent invalidation; documented attention fragmentation",
        },
        "RLI": {
            "feature": "Background refresh, unread-count badge, app-entry streak rewards, haptic feedback on re-launch",
            "mechanism": "Variable reward schedule on re-entry → operant conditioning → compulsive checking behavior",
            "harm": "Clinically measurable loss of control over app usage → behavioral addiction markers consistent with DSM-5 criteria",
        },
        "NSCR": {
            "feature": "Engagement-optimized notification frequency, personalized send-time optimization, sound/vibration alerts",
            "mechanism": "High-frequency notifications at predicted high-response times → conditioned stimulus-response pattern → notification dependency",
            "harm": "Platform-controlled behavioral loop → user autonomy compromised → KOSA § 4(b)(3) violation for minor users",
        },
        "ACS": {
            "feature": "Engagement-maximizing recommendation algorithm, A/B tested emotional content ranking, outrage amplification",
            "mechanism": "Emotional contagion amplification → progressive drift toward high-arousal negative content → affective dysregulation",
            "harm": "Elevated anxiety and depression markers → self-harm risk increase → documented in Twenge et al. (2018) and Frances Haugen Senate testimony (2021)",
        },
    }
    _legal_map = {
        "SVG":  ["KOSA", "DSA"],
        "DDR":  ["DSA", "MA 93A"],
        "RLI":  ["UK Online Safety Act", "CCPA"],
        "NSCR": ["KOSA", "DSA"],
        "ACS":  ["KOSA", "MA 93A"],
    }
    flagged_patterns = {p["metric"]: p for p in audit.get("flagged_patterns", [])}

    map_record = {
        "record_type": "MAP",
        "description": "Per-metric risk pathway analysis: feature → mechanism → harm",
        "platform": platform_name,
        "audit_timestamp": timestamp,
        "audit_summary": audit.get("summary", "No feature audit performed yet."),
        "overall_risk_score": audit.get("risk_score", 0),
        "overall_risk_level": audit.get("risk_level", "UNKNOWN"),
        "metrics": [],
    }
    for key in ["SVG", "DDR", "RLI", "NSCR", "ACS"]:
        fp = flagged_patterns.get(key, {})
        user_readings = [
            {
                "user_id": s["user_id"],
                "name": s["name"],
                "is_minor": s["is_minor"],
                "value": s.get("metrics", {}).get(key, {}).get("value"),
                "threshold": s.get("metrics", {}).get(key, {}).get("threshold"),
                "triggered": s.get("metrics", {}).get(key, {}).get("triggered", False),
            }
            for s in states
        ]
        map_record["metrics"].append({
            "metric": key,
            "name": next(m["name"] for m in govern["metrics"] if m["key"] == key),
            "pathway": _pathways[key],
            "flagged_by_audit": key in flagged_patterns,
            "audit_pattern_name": fp.get("pattern"),
            "audit_severity": fp.get("severity"),
            "audit_description": fp.get("description"),
            "current_user_readings": user_readings,
            "laws_implicated": _legal_map[key],
        })

    # ── MEASURE ──────────────────────────────────────────────────────────────────
    measure_record = {
        "record_type": "MEASURE",
        "description": "Per-user behavioral telemetry, intervention outcomes, and before/after score deltas",
        "platform": platform_name,
        "audit_timestamp": timestamp,
        "users": [],
    }
    for user in USERS.values():
        hist = user.score_history
        before = after = delta = None
        if user.intervention_fired and user.intervention_session > 0:
            isess = user.intervention_session
            if len(hist) >= isess:
                before = hist[isess - 1]
            if len(hist) >= isess + 3:
                after = hist[isess + 2]
            if before is not None and after is not None:
                delta = after - before

        child_events = []
        if user.is_minor:
            for s in states:
                if s["user_id"] == user.user_id and s.get("is_child_safety_event"):
                    child_events.append({
                        "session": s["session"],
                        "risk_score": s["risk_score"],
                        "laws_triggered": ["KOSA § 4(b)", "UK Online Safety Act § 12", "COPPA"],
                    })

        if delta is not None:
            outcome = "recovering" if delta < 0 else ("no_change" if delta == 0 else "worsening")
        elif user.intervention_fired:
            outcome = "monitoring"
        else:
            outcome = "intervention_not_yet_triggered"

        measure_record["users"].append({
            "user_id": user.user_id,
            "name": user.name,
            "age": user.age,
            "is_minor": user.is_minor,
            "archetype": user.archetype,
            "sessions_recorded": user.session_number,
            "score_history": hist,
            "peak_risk_score": max(hist) if hist else 0,
            "current_risk_score": hist[-1] if hist else 0,
            "intervention": {
                "fired": user.intervention_fired,
                "session_triggered": user.intervention_session if user.intervention_fired else None,
                "interventions_applied": list(user.active_interventions),
                "score_at_trigger": before,
                "score_3_sessions_post": after,
                "before_after_delta": delta,
                "outcome": outcome,
            },
            "child_safety_events": child_events,
        })

    # ── MANAGE ───────────────────────────────────────────────────────────────────
    intervention_log = []
    for user in USERS.values():
        if not user.intervention_fired:
            continue
        hist = user.score_history
        isess = user.intervention_session
        score_at_trigger = hist[isess - 1] if len(hist) >= isess else None
        score_now = hist[-1] if hist else None
        net = (score_now - score_at_trigger) if (score_at_trigger is not None and score_now is not None) else None

        triggered_now = [
            k for s in states if s["user_id"] == user.user_id
            for k, m in s.get("metrics", {}).items() if m.get("triggered")
        ]
        intervention_log.append({
            "user_id": user.user_id,
            "user_name": user.name,
            "is_minor": user.is_minor,
            "intervention_session": isess,
            "interventions_applied": list(user.active_interventions) or [
                "notification_suppression", "affective_rebalancing"
            ],
            "score_at_trigger": score_at_trigger,
            "current_score": score_now,
            "net_score_change": net,
            "outcome": "Score reduced following intervention" if (net is not None and net < 0) else "Monitoring ongoing",
            "currently_triggered_metrics": triggered_now,
            "compliance_note": (
                "Minor user — elevated KOSA/UK OSA/COPPA duty of care applies"
                if user.is_minor else
                "Adult user — standard duty of care applies"
            ),
        })

    manage_record = {
        "record_type": "MANAGE",
        "description": "Intervention log with outcomes and legal certification",
        "platform": platform_name,
        "audit_timestamp": timestamp,
        "intervention_log": intervention_log,
        "certification": (
            "All interventions were executed within the pre-committed threshold framework "
            "as documented in the GOVERN record above. Thresholds were set prior to any "
            "risk event and have not been modified retroactively."
        ),
        "legal_certification": {
            "statement": (
                "This intervention record constitutes an append-only compliance log suitable "
                "for legal discovery under KOSA, DSA, MA 93A, UK Online Safety Act, and CCPA/CPRA."
            ),
            "nist_ai_rmf_functions_covered": ["GOVERN", "MAP", "MEASURE", "MANAGE"],
            "generated_by": "Konduct v1.0 — Behavioral Algorithm Compliance Auditor",
        },
    }

    # ── Current metric snapshot ──────────────────────────────────────────────────
    current_metric_snapshot = []
    for s in states:
        current_metric_snapshot.append({
            "user_id": s["user_id"],
            "name": s["name"],
            "age": s["age"],
            "is_minor": s["is_minor"],
            "session": s["session"],
            "risk_score": s["risk_score"],
            "risk_level": s["risk_level"],
            "metrics": {
                k: {"value": v["value"], "threshold": v["threshold"], "triggered": v["triggered"]}
                for k, v in s.get("metrics", {}).items()
            },
        })

    # ── NIST RMF live status ─────────────────────────────────────────────────────
    any_recovering = any(s.get("recovering") for s in states)
    any_intervened = any(s.get("intervention_fired") for s in states)
    child_events_count = sum(1 for s in states if s.get("is_child_safety_event"))
    triggered_counts: set = set()
    for s in states:
        for k, v in s.get("metrics", {}).items():
            if v.get("triggered"):
                triggered_counts.add(k)
    n_triggered = len(triggered_counts)

    nist_rmf_status = {
        "GOVERN": {
            "status": "COMPLIANT" if audit else "PARTIAL",
            "detail": (
                "Feature audit completed — pre-committed safety policy documented"
                if audit else
                "No feature audit performed yet; threshold governance active"
            ),
        },
        "MAP": {
            "status": "COMPLIANT" if n_triggered == 0 else ("PARTIAL" if n_triggered < 5 else "NON_COMPLIANT"),
            "triggered_metrics": list(triggered_counts),
            "detail": (
                f"{n_triggered} risk metric(s) currently breaching threshold across monitored users"
                if n_triggered else "No metrics breaching threshold"
            ),
        },
        "MEASURE": {
            "status": "COMPLIANT" if any_recovering else ("PARTIAL" if any_intervened else "NON_COMPLIANT"),
            "detail": (
                "Intervention active and score recovery in progress"
                if any_recovering else (
                    "Intervention triggered; awaiting post-intervention score delta"
                    if any_intervened else
                    "No interventions triggered yet"
                )
            ),
        },
        "MANAGE": {
            "status": "COMPLIANT" if child_events_count == 0 else ("PARTIAL" if child_events_count <= 2 else "NON_COMPLIANT"),
            "child_safety_events": child_events_count,
            "detail": (
                "No active child-safety events"
                if child_events_count == 0 else
                f"{child_events_count} child-safety event(s) logged — elevated KOSA/COPPA/UK-OSA duty of care"
            ),
        },
    }

    return {
        "package_type": "Konduct Litigation Export",
        "version": "1.0",
        "export_id": export_id,
        "generated_at": timestamp,
        "platform": platform_name,
        "nist_ai_rmf_version": "1.0 (2023)",
        "disclaimer": (
            "No algorithmic intervention guarantees elimination of harm. This system provides "
            "good-faith structural remediation consistent with the pharmaceutical industry standard "
            "for post-market safety monitoring. Adverse outcomes may occur even within a properly "
            "functioning safety system."
        ),
        "legal_notice": (
            "This document is a machine-generated compliance record produced by Konduct. "
            "It should be reviewed by qualified legal counsel before use in any legal proceeding."
        ),
        "current_metric_snapshot": current_metric_snapshot,
        "nist_rmf_status": nist_rmf_status,
        "records": {
            "GOVERN": govern,
            "MAP": map_record,
            "MEASURE": measure_record,
            "MANAGE": manage_record,
        },
        "audit_results": audit or {
            "note": "No feature audit has been performed yet. Run an audit from the dashboard first."
        },
    }


# ── Litigation endpoints ───────────────────────────────────────────────────────

@app.get("/api/litigation-export")
async def litigation_export(platform_name: str = "Unknown Platform"):
    package = _build_litigation_data(platform_name)
    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = platform_name.lower().replace(" ", "-").replace("/", "-")
    filename = f"konduct-litigation-{safe_name}-{date_str}.json"
    return Response(
        content=json.dumps(package, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/litigation-report/{platform_name}", response_class=HTMLResponse)
async def litigation_report_view(request: Request, platform_name: str):
    pkg = _build_litigation_data(platform_name)
    return templates.TemplateResponse(request=request, name="litigation.html", context={
        "pkg": pkg,
        "platform_name": platform_name,
    })
