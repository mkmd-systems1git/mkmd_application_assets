#!/usr/bin/env python3
"""
MKMD Autonomous Application Agent
Orchestrator: fetch_and_draft.py
Target Fields: Maritime Edge, Private Aviation, UHNWI Family Offices, Autonomous Startups
Constraints: $0 Cost, Zero Local Compute, 7-Day State Expiration Lifecycle
"""

import os
import re
import csv
import json
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

# --- GLOBAL SYSTEM ENVIRONMENT CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
REPO_ROOT = Path(__file__).resolve().parent
TRACKING_CSV = REPO_ROOT / "tracking_dashboard.csv"
DRAFTS_DIR = REPO_ROOT / "drafts"

GEMINI_ENDPOINT = (
    "https://googleapis.com"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)

# --- STRICT 14-COLUMN AIRTABLE DATA REPLICATOR SCHEMA ---
CSV_COLUMNS = [
    "JOB_ID",
    "Date_Logged",
    "Target_Market_Sector",
    "Target_Platform",
    "Company_Name",
    "Position_Title",
    "Offered_Income_Floor",
    "Hardware_Laptop_Required",
    "Status_Tracking",
    "SCORE",
    "Problem to solve",
    "Strategic_Pitch_Angle",
    "Draft_Artifacts_Path",
    "URL"
]

# --- ASSET INGESTION LAYER (IMMUTABLE RAG VAULT) ---
def load_rag_context() -> dict:
    """
    Reads Mueni's universal application profiles and portfolio data natively.
    Treats assets as a read-only context reservoir for the evaluation brain.
    """
    resume_path = REPO_ROOT / "resume.md"
    cover_letter_path = REPO_ROOT / "cover_letter.md"
    portfolio_path = REPO_ROOT / "index.html"

    # Safely digest files, fallback seamlessly to generic strings if empty
    return {
        "resume": resume_path.read_text(encoding="utf-8") if resume_path.exists() else "Resume file unavailable.",
        "cover_letter_template": cover_letter_path.read_text(encoding="utf-8") if cover_letter_path.exists() else "",
        "portfolio": portfolio_path.read_text(encoding="utf-8") if portfolio_path.exists() else "Portfolio file unavailable."
    }

# --- INGESTION PIPELINE (STREAM & WEBHOOK CONVEYOR) ---
def fetch_rss_feed(url: str, sector_name: str) -> list:
    """
    Parses open technical developer feeds securely.
    Includes error handling and custom headers to bypass scraping blocks.
    """
    jobs = []
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MKMD-Systems-Agent/2.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
            if not xml_data.strip():
                return jobs
            
            tree = ET.fromstring(xml_data)
            for item in tree.findall("./channel/item"):
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                desc = item.findtext("description", "").strip()
                guid = item.findtext("guid", link).strip()
                
                # Sanitize HTML tags out of job descriptions safely
                clean_desc = re.sub(r"<[^>]+>", " ", desc)
                
                if ":" in title:
                    parts = title.split(":", 1)
                    company = parts[0].strip()
                    role = parts[1].strip()
                else:
                    company = "Niche Inefficient Principal"
                    role = title

                jobs.append({
                    "raw_id": guid,
                    "company": company,
                    "role": role,
                    "description": clean_desc.strip()[:4000],
                    "url": link,
                    "sector_hint": sector_name
                })
    except Exception as e:
        print(f"[INGESTION BYPASS] Skipping feed pipeline for {sector_name}: {e}")
    return jobs

def fetch_inbound_webhook_alerts() -> list:
    """
    Consumes raw JSON files pushed from Make.com into the inbound_alerts/ directory.
    Deletes staging alert payloads on processing to keep repository storage at zero.
    """
    alert_dir = REPO_ROOT / "inbound_alerts"
    jobs = []
    if not alert_dir.exists():
        return jobs

    for alert_file in alert_dir.glob("*.json"):
        try:
            # Parse text contents directly from the base64 encrypted webhook payload structure
            raw_content = alert_file.read_text(encoding="utf-8")
            data = json.loads(raw_content)
            
            # Reconstruct variables out of raw email text block
            body_text = data.get("body", "No clear text block parsed.")
            
            jobs.append({
                "raw_id": data.get("id", alert_file.stem).strip(),
                "company": data.get("company", "Stealth Portfolio Network / Private Estate").strip(),
                "role": data.get("title", "Systems & Infrastructure Architect").strip(),
                "description": body_text[:4000],
                "url": data.get("link", "Direct Inbound Mailbox Gateway").strip(),
                "sector_hint": data.get("sector", "Stealth Market (Private Operations)").strip()
            })
            alert_file.unlink() # Purge the staging payload file instantly to prevent double processing loops
            print(f"[WEBHOOK CONSUMED] Safely integrated and cleaned alert payload: {alert_file.name}")
        except Exception as e:
            print(f"[WARN] Inbound alert structure processing error on file {alert_file.name}: {e}")
    return jobs
# --- DETERMINISTIC MEMORY REGISTER & STATE LIFECYCLE ---
def read_ledger() -> list:
    """Reads current tracking repository database file safely."""
    if not TRACKING_CSV.exists():
        return []
    rows = []
    with open(TRACKING_CSV, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def execute_lifecycle_cleanup(rows: list) -> list:
    """
    Maintains clean dashboard boundaries. If an unapproved record hits the 7-day 
    expiration limit, it flips it to Expired instead of deleting the row.
    This protects historical state tracking and prevents duplicate entry logging.
    """
    cutoff_date = datetime.now() - timedelta(days=7)
    for r in rows:
        if r.get("Status_Tracking") == "Discovered":
            try:
                log_time = datetime.strptime(r["Date_Logged"], "%Y-%m-%d")
                if log_time < cutoff_date:
                    r["Status_Tracking"] = "Expired"
                    print(f"[STATE SHIFT] Stale item shifted to Expired status: {r['JOB_ID']} ({r['Company_Name']})")
            except Exception:
                pass
    return rows

def generate_deterministic_id(company: str, raw_link: str) -> str:
    """
    Creates a secure, permanent SHA-256 fingerprint for every job.
    Bypasses volatile runtime hashing, guaranteeing zero duplicate entries across runs.
    """
    clean_company = re.sub(r"[^\w]", "", company.replace(" ", "_")).upper()[:12]
    hasher = hashlib.sha256(raw_link.encode("utf-8")).hexdigest()[:6].upper()
    return f"JOB-{clean_company}-{hasher}"
