#!/usr/bin/env python3
"""
End-to-end test flow: auth → create chart → run analyses.

Usage:
    python scripts/test_flow.py --email you@example.com --password yourpass
    python scripts/test_flow.py --email you@example.com --password yourpass --section career
    python scripts/test_flow.py --email you@example.com --password yourpass --all-sections
"""

import argparse
import os
import sys
from dotenv import load_dotenv

import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
API_BASE = "http://localhost:8000/api"

VALID_SECTIONS = [
    "personality", "mind", "career", "skills", "wealth", "foreign",
    "romance", "marriage", "business", "property", "health", "education",
    "parents", "siblings", "children", "spirituality",
]

# ── Birth data (edit as needed) ───────────────────────────────────────────────

BIRTH_DATA = {
    "name": "Aadarsh Gaikwad",
    "dob": "1996-12-03",
    "tob": "23:50:12",
    "pob_name": "Hyderabad, India",
    "pob_lat": 17.3850,
    "pob_lon": 78.4867,
    "timezone": 5.5,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def step(msg: str):
    print(f"\n{'─'*60}\n  {msg}\n{'─'*60}")

def ok(msg: str):
    print(f"  ✓  {msg}")

def fail(msg: str):
    print(f"  ✗  {msg}")
    sys.exit(1)


# ── Steps ─────────────────────────────────────────────────────────────────────

def authenticate(email: str, password: str) -> str:
    step("1. Authenticating with Supabase")
    resp = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=15,
    )
    if resp.status_code != 200:
        fail(f"Auth failed [{resp.status_code}]: {resp.text}")
    token = resp.json().get("access_token")
    if not token:
        fail(f"No access_token in response: {resp.text}")
    ok(f"Got JWT for {email}")
    return token


def create_chart(token: str) -> str:
    step("2. Creating chart")
    resp = httpx.post(
        f"{API_BASE}/charts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=BIRTH_DATA,
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        fail(f"Create chart failed [{resp.status_code}]: {resp.text}")
    chart = resp.json()
    chart_id = chart["id"]
    ok(f"Chart created → id: {chart_id}")
    return chart_id


def run_analysis(token: str, chart_id: str, section: str):
    step(f"3. Running analysis: {section}")
    resp = httpx.post(
        f"{API_BASE}/charts/{chart_id}/analyze/{section}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    if resp.status_code != 200:
        fail(f"Analysis failed [{resp.status_code}]: {resp.text}")
    result = resp.json()
    cached = result.get("cached", False)
    content = result.get("content", "")
    ok(f"Section '{section}' done (cached={cached})")
    print(f"\n{content}\n")
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cosmos API end-to-end flow")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--section", default="personality", choices=VALID_SECTIONS,
                        help="Single section to analyze (default: personality)")
    parser.add_argument("--all-sections", action="store_true",
                        help="Run all 16 analysis sections")
    parser.add_argument("--chart-id", help="Skip chart creation, use existing chart ID")
    args = parser.parse_args()

    token = authenticate(args.email, args.password)

    chart_id = args.chart_id or create_chart(token)

    sections = VALID_SECTIONS if args.all_sections else [args.section]
    for section in sections:
        run_analysis(token, chart_id, section)

    step("Done")
    ok(f"Chart ID: {chart_id}")
    ok(f"Sections run: {', '.join(sections)}")


if __name__ == "__main__":
    main()
