import os
import csv
import json
import urllib.request
from datetime import datetime
import google.generativeai as genai

# Configuration constants
DRAFT_SCORE_THRESHOLD = 80
CLEANUP_DAYS = 7
DASHBOARD_FILE = "tracking_dashboard.csv"

def get_master_assets():
    """Reads master resume, cover letter, and Jekyll portfolio context safely."""
    assets = {"resume": "", "cover_letter": "", "portfolio": ""}
    try:
        with open("resume.md", "r", encoding="utf-8") as f:
            assets["resume"] = f.read()
        with open("cover_letter.md", "r", encoding="utf-8") as f:
            assets["cover_letter"] = f.read()
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                assets["portfolio"] = f.read()
    except Exception as e:
        print(f"Error loading foundational assets: {e}")
    return assets

def fetch_active_streams():
    """Ingests data from open technical remote streams safely."""
    listings = []
    # Targeted global remote developer data pipeline channel
    url = "https://workingnomads.com"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            for job in data[:10]: # Extract newest entries to manage processing limits safely
                listings.append({
                    "id": str(job.get('id', job.get('pk'))),
                    "title": job.get('title'),
                    "company": job.get('company_name', 'Enterprise Cloud Target'),
                    "description": job.get('description'),
                    "url": job.get('url', 'https://workingnomads.com'),
                    "sector": "Global Remote Infrastructure"
                })
    except Exception as e:
        print(f"Standard remote technical feed stream paused: {e}")
    return listings

def process_pipeline():
    """Evaluates opportunities based strictly on privacy, resilience, and asset continuity."""
    assets = get_master_assets()
    if not assets["resume"]:
        return

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("Missing GEMINI_API_KEY secret token environment variable.")
        return
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    raw_jobs = fetch_active_streams()
    existing_rows = []
    existing_ids = set()

    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
            existing_ids = {row['JOB_ID'] for row in existing_rows if 'JOB_ID' in row}

    today = datetime.utcnow().strftime('%Y-%m-%d')
    cleaned_rows = []
    for row in existing_rows:
        try:
            row_date = datetime.strptime(row['Date_Logged'], '%Y-%m-%d')
            is_expired = (today - row_date).days >= CLEANUP_DAYS
            if row['Status_Tracking'] == 'Discovered' and is_expired:
                continue 
        except (ValueError, KeyError):
            pass
        cleaned_rows.append(row)

    new_logs = []
    for job in raw_jobs:
        if job['id'] in existing_ids:
            continue

        prompt = f"""
        You are Mueni Kitoko's Personal Strategic Job Agent. Evaluate this posting strictly against her 
        DevOps/Cloud Systems & Automation resume and her 10-project portfolio site layout context.

        RESUME ASSETS:
        {assets['resume']}

        PORTFOLIO ASSETS:
        {assets['portfolio']}

        OPPORTUNITY DESCRIPTION:
        Title: {job['title']}
        Description: {job['description']}

        CRITICAL EVALUATION ENGINE CONSTRAINTS:
        1. Emphasize Security, Privacy, Resilience, and High Availability over corporate agile metrics.
        2. Map the problem to her core pillars: Ultra-Private Sovereign Cloud, Digital Estate Continuity, Smart Estate Automation (K3s/Starlink), or OSINT Reputation Monitoring.
        3. Audit for laptop hardware requirements. If explicitly stated or implied for secure remote travel infrastructure, note it.
        4. Identify the target market sector (Maritime, Aviation, UHNWI Family Office, or Enterprise SaaS).
        5. Draft a highly assertive, problem-centric cover letter template based on her original language patterns.

        Return response STRICTLY in clean JSON matching these exact keys:
        {{
            "score": 0-100 integer,
            "problem_category": "Sovereign Cloud OR Estate Automation OR Dead Man's Switch OR OSINT",
            "extracted_problem": "precise business pain point description",
            "strategic_pitch": "one-sentence aggressive metric-focused alignment statement",
            "platform_stack": "AWS/Bare-Metal/K3s/n8n",
            "income_floor": "$4500+ or High-Value Gig Contract",
            "laptop_provided": "Yes or No or Not Specified",
            "market_sector": "string",
            "custom_cover_letter_draft": "full letter text"
        }}
        """
        try:
            response = model.generate_content(prompt)
            clean_text = response.text.strip().lstrip("```json").rstrip("```").strip()
            analysis = json.loads(clean_text)
            
            score = int(analysis.get('score', 0))
            draft_path = "N/A"

            if score >= DRAFT_SCORE_THRESHOLD:
                folder_name = f"drafts/{job['company'].replace(' ', '_')}_{job['id']}"
                os.makedirs(folder_name, exist_ok=True)
                with open(f"{folder_name}/tailored_cover_letter.txt", "w", encoding="utf-8") as f_cl:
                    f_cl.write(analysis.get('custom_cover_letter_draft', ''))
                repo_env = os.environ.get('GITHUB_REPOSITORY', 'mkmd-systems1git/mkmd_application_assets')
                draft_path = f"https://github.com{repo_env}/tree/main/{folder_name}"

            # Maps rows seamlessly to your exact 14 Airtable spreadsheet dashboard fields
            new_logs.append({
                "JOB_ID": job['id'],
                "Date_Logged": today,
                "Target_Market_Sector": analysis.get('market_sector', job['sector']),
                "Target_Platform": analysis.get('platform_stack', 'Cloud Core'),
                "Company_Name": job['company'],
                "Position_Title": job['title'],
                "Offered_Income_Floor": analysis.get('income_floor', 'Market Rate'),
                "Hardware_Laptop_Required": analysis.get('laptop_provided', 'Not Specified'),
                "Status_Tracking": "Discovered",
                "SCORE": str(score),
                "Problem to solve": analysis.get('extracted_problem', ''),
                "Strategic_Pitch_Angle": analysis.get('strategic_pitch', ''),
                "Draft_Artifacts_Path": draft_path,
                "URL": job['url']
            })
            print(f"✅ Evaluated {job['company']} - Match SCORE: {score}%")
        except Exception as e:
            print(f"Skipping evaluation due to loop formatting: {e}")

    final_rows = cleaned_rows + new_logs
    fieldnames = [
        "JOB_ID", "Date_Logged", "Target_Market_Sector", "Target_Platform", "Company_Name", 
        "Position_Title", "Offered_Income_Floor", "Hardware_Laptop_Required", "Status_Tracking", 
        "SCORE", "Problem to solve", "Strategic_Pitch_Angle", "Draft_Artifacts_Path", "URL"
    ]
    
    with open(DASHBOARD_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)
    print("Tracking ledger update completed successfully.")

if __name__ == "__main__":
    process_pipeline()
v
