# AlgoGuard

A real-time social media algorithm compliance auditing tool. Built with claude code in 5 hours at the Claremont Accelerator Hackathon (April 2026).

## What It Does

AlgoGuard analyzes social media platform algorithm designs for addiction-risk patterns and legal exposure. It monitors simulated user behavioral data in real time, scores risk across five behavioral metrics, and generates a printable compliance audit report with legal citations and remediation recommendations.

This was built in the context of the March 2026 *K.G.M. v. Meta & YouTube* verdict — the first jury trial win for social media addiction plaintiffs ($6M award, Meta found 70% liable). With 2,465+ pending suits nationwide, platforms need a way to audit their own algorithm mechanics before they ship.

## Features
- **Live dashboard** — monitors three synthetic users (minor, young adult, adult) with auto-refreshing behavioral metrics
- **RIS risk scoring** — five behavioral metrics scored in real time:
  - SVG (Session Volume Growth)
  - DDR (Disengagement Detection Rate)
  - RLI (Reward Loop Intensity)
  - NSCR (Negative Sentiment Correlation Rate)
  - ACS (Affective Capture Score)
- **Child safety detection** — flags when a minor simultaneously breaches ACS and NSCR thresholds
- **AI-powered audit** — Claude API analyzes platform behavior and returns flagged patterns, legal exposure, and remediation steps
- **Printable compliance report** — structured audit output covering flagged patterns, NIST AI RMF mapping (GOVERN/MAP/MEASURE/MANAGE), and regulatory exposure (KOSA, DSA, MA 93A, CCPA/CPRA, UK Online Safety Act)

## Tech Stack

- **Backend:** FastAPI, SQLite, Python
- **Frontend:** Plain HTML/CSS/JS (no frameworks)
- **AI:** Anthropic Claude API (`claude-opus-4-5`)
- **Simulation:** Custom synthetic behavioral engine (no real user data)

## Setup
bash
pip install -r requirements.txt
cp .env.example .env
Add your ANTHROPIC_API_KEY to .env
uvicorn app:app --reload
Then open `http://localhost:8000`.
## Architecture

app.py            — FastAPI server, RIS classifier, Claude API integration
simulator.py      — Synthetic user behavioral engine (Maya/James/Alex)
templates/
  dashboard.html  — Live monitoring dashboard (auto-refreshes every 3s)
  report.html     — Print-to-PDF audit report
static/
  style.css       — Dashboard styling
## Legal Context

Built around the post-*K.G.M. v. Meta* legal landscape. Key regulatory hooks:
- **K.G.M. v. Meta & YouTube** (March 2026) — first jury verdict for social media addiction
- **MA 93A** — unfair/deceptive practices, triple damages
- **KOSA** — Kids Online Safety Act
- **DSA** — EU Digital Services Act
- **NIST AI RMF** — GOVERN/MAP/MEASURE/MANAGE framework

## Built At

Claremont Accelerator Hackathon — April 11, 2026
