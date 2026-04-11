"""
AlgoGuard — Synthetic User Telemetry Simulator
Three behavioral archetypes derived from published research:
  Maya (16, minor)  — Twenge et al. (2018), 85th percentile adolescent compulsive use
  James (28, adult) — Oulasvirta et al. (2012), median borderline adult user
  Alex (34, adult)  — Pielot et al. (2014), healthy intentional use baseline
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any


# ── Thresholds ────────────────────────────────────────────────────────────────

THRESHOLDS = {
    "SVG":  {"adult": 70,  "minor": 60},
    "DDR":  {"adult": 0.20, "minor": 0.25},
    "RLI":  {"adult": 3,   "minor": 2},
    "NSCR": {"adult": 0.65, "minor": 0.50},
    "ACS":  {"adult": 0.50, "minor": 0.40},
}


# ── User State ────────────────────────────────────────────────────────────────

@dataclass
class UserState:
    user_id: str
    name: str
    age: int
    is_minor: bool
    archetype: str  # "compulsive" | "borderline" | "healthy"
    session_number: int = 0
    intervention_fired: bool = False
    intervention_session: int = -1
    score_history: List[int] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    active_interventions: List[str] = field(default_factory=list)


def _jitter(value: float, pct: float = 0.08) -> float:
    """Add small random noise to make numbers feel realistic."""
    return value * (1 + random.uniform(-pct, pct))


def compute_metrics(user: UserState) -> Dict[str, Any]:
    """Compute RIS metrics for the current session based on archetype + trajectory."""
    s = user.session_number
    post = s - user.intervention_session if user.intervention_fired else 0

    if user.archetype == "compulsive":
        # Maya: all 5 metrics elevate progressively; child safety event at session 6
        if not user.intervention_fired:
            svg   = _jitter(3.8 + max(0, (s - 4)) * 0.85)   # Elevates session 5+
            ddr   = _jitter(max(0.08, 0.45 - max(0, (s - 4)) * 0.08))
            rli   = max(1, round(_jitter(45 - max(0, (s - 2)) * 10)))
            nscr  = min(0.95, _jitter(0.42 + max(0, (s - 3)) * 0.075))
            acs   = min(0.90, _jitter(0.18 + max(0, (s - 3)) * 0.09))
        else:
            # Exponential recovery
            decay = math.exp(-0.5 * post)
            svg   = _jitter(3.8 + 3.4 * decay)
            ddr   = _jitter(0.45 - 0.33 * (1 - decay))
            rli   = max(10, round(_jitter(4 + 41 * (1 - decay))))
            nscr  = max(0.42, _jitter(0.72 - 0.30 * (1 - decay)))
            acs   = max(0.18, _jitter(0.65 - 0.47 * (1 - decay)))

    elif user.archetype == "borderline":
        # James: only RLI elevates, briefly
        if not user.intervention_fired:
            svg  = _jitter(2.8)
            ddr  = _jitter(0.62)
            rli  = max(10, round(_jitter(90 - max(0, (s - 3)) * 44)))
            nscr = _jitter(0.38)
            acs  = _jitter(0.12)
        else:
            decay = math.exp(-0.9 * post)
            svg  = _jitter(2.8)
            ddr  = _jitter(0.62)
            rli  = max(60, round(_jitter(2 + 88 * (1 - decay))))
            nscr = _jitter(0.38)
            acs  = _jitter(0.12)

    else:
        # Alex: always healthy, no elevation
        svg  = _jitter(2.2)
        ddr  = _jitter(0.75)
        rli  = round(_jitter(180))
        nscr = _jitter(0.28)
        acs  = _jitter(0.08)

    return {"SVG": round(svg, 2), "DDR": round(ddr, 3),
            "RLI": rli, "NSCR": round(nscr, 3), "ACS": round(acs, 3)}


def score_user(metrics: Dict, is_minor: bool) -> int:
    """Compute composite risk score 0-100."""
    tier = "minor" if is_minor else "adult"
    triggered = 0
    weights   = {"SVG": 20, "DDR": 20, "RLI": 20, "NSCR": 20, "ACS": 20}
    for key, w in weights.items():
        v = metrics[key]
        t = THRESHOLDS[key][tier]
        if key == "DDR":
            if v < t:
                triggered += w
        elif key == "RLI":
            if v < t:
                triggered += w
        else:
            if v > t:
                triggered += w
    return min(100, triggered + random.randint(0, 5))


def risk_level(score: int) -> str:
    if score >= 70:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    return "LOW"


def decide_interventions(metrics: Dict, is_minor: bool, score: int) -> List[str]:
    interventions = []
    tier = "minor" if is_minor else "adult"
    if metrics["NSCR"] > THRESHOLDS["NSCR"][tier]:
        interventions.append("notification_suppression")
    if metrics["ACS"] > THRESHOLDS["ACS"][tier]:
        interventions.append("affective_rebalancing")
    if metrics["RLI"] < THRESHOLDS["RLI"][tier]:
        interventions.append("compulsion_signal_quarantine")
    return interventions


def advance_session(user: UserState) -> Dict[str, Any]:
    """Step user one session forward and return full state."""
    user.session_number += 1
    metrics = compute_metrics(user)
    user.metrics = metrics
    score = score_user(metrics, user.is_minor)
    user.score_history.append(score)
    level = risk_level(score)

    # Fire intervention once when user first hits HIGH
    if level == "HIGH" and not user.intervention_fired:
        user.intervention_fired = True
        user.intervention_session = user.session_number
        user.active_interventions = decide_interventions(metrics, user.is_minor, score)
    elif user.intervention_fired:
        # Keep interventions active during recovery
        post = user.session_number - user.intervention_session
        if post >= 5:
            user.active_interventions = []

    is_child_safety = (
        user.is_minor and
        metrics["ACS"] > THRESHOLDS["ACS"]["minor"] and
        metrics["NSCR"] > THRESHOLDS["NSCR"]["minor"]
    )

    metric_detail = {}
    tier = "minor" if user.is_minor else "adult"
    for key, val in metrics.items():
        t = THRESHOLDS[key][tier]
        if key in ("DDR", "RLI"):
            triggered = val < t
        else:
            triggered = val > t
        metric_detail[key] = {"triggered": triggered, "value": val, "threshold": t}

    return {
        "user_id": user.user_id,
        "name": user.name,
        "age": user.age,
        "is_minor": user.is_minor,
        "archetype": user.archetype,
        "session": user.session_number,
        "risk_score": score,
        "risk_level": level,
        "metrics": metric_detail,
        "active_interventions": user.active_interventions,
        "is_child_safety_event": is_child_safety,
        "score_history": user.score_history,
        "intervention_fired": user.intervention_fired,
    }


# ── Global user registry (in-memory state) ───────────────────────────────────

USERS: Dict[str, UserState] = {
    "maya": UserState(
        user_id="user_maya_synthetic_001",
        name="Maya", age=16, is_minor=True, archetype="compulsive"
    ),
    "james": UserState(
        user_id="user_james_synthetic_002",
        name="James", age=28, is_minor=False, archetype="borderline"
    ),
    "alex": UserState(
        user_id="user_alex_synthetic_003",
        name="Alex", age=34, is_minor=False, archetype="healthy"
    ),
}


def get_all_states() -> List[Dict]:
    """Return current state for all users without advancing."""
    results = []
    for user in USERS.values():
        if user.session_number == 0:
            advance_session(user)
        else:
            # Recompute display without advancing
            metrics = compute_metrics(user)
            score = score_user(metrics, user.is_minor)
            level = risk_level(score)
            tier = "minor" if user.is_minor else "adult"
            metric_detail = {}
            for key, val in metrics.items():
                t = THRESHOLDS[key][tier]
                triggered = val < t if key in ("DDR", "RLI") else val > t
                metric_detail[key] = {"triggered": triggered, "value": val, "threshold": t}
            results.append({
                "user_id": user.user_id,
                "name": user.name,
                "age": user.age,
                "is_minor": user.is_minor,
                "archetype": user.archetype,
                "session": user.session_number,
                "risk_score": score,
                "risk_level": level,
                "metrics": metric_detail,
                "active_interventions": user.active_interventions,
                "is_child_safety_event": (
                    user.is_minor and
                    metrics["ACS"] > THRESHOLDS["ACS"]["minor"] and
                    metrics["NSCR"] > THRESHOLDS["NSCR"]["minor"]
                ),
                "score_history": user.score_history,
                "intervention_fired": user.intervention_fired,
            })
            continue
        results.append(advance_session(user) if user.session_number == 1 else results[-1])
    return results


def tick_all() -> List[Dict]:
    """Advance all users one session and return new states."""
    return [advance_session(u) for u in USERS.values()]


def reset_all():
    """Reset all users to session 0."""
    for key, u in USERS.items():
        USERS[key] = UserState(
            user_id=u.user_id,
            name=u.name,
            age=u.age,
            is_minor=u.is_minor,
            archetype=u.archetype,
        )
