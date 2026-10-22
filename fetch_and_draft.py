import os
import csv
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import google.generativeai as genai

# Configuration constants
DRAFT_SCORE_THRESHOLD = 80
CLEANUP_DAYS = 7
DASHBOARD_FILE = "tracking_dashboard.csv"

def get_master_assets():
    """Reads your master files and detailed portfolio project data from the repository."""
    assets = {"resume": "", "cover_letter": "", "portfolio": ""}
    try:
        with open("resume.md", "r", encoding="utf-8") as f:
            assets["resume"] = f.read()
        with open("cover_letter.md", "r", encoding="utf-8") as f:
            assets["cover_letter"] = f.read()
        
        # Upgraded Layer: Read your main portfolio file to extract your 10 detailed projects
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                assets["portfolio"] = f.read()
        elif os.path.exists("html.md"):
            with open("html.md", "r", encoding="utf-8") as f:
                assets["portfolio"] = f.read()
    except Exception as e:
        print(f"Error loading foundational assets: {e}")
    return assets

def fetch_raw_listings():
    """Pulls recent developer postings from free global remote streams."""
    listings = []
    # Using a free aggregated technical remote feed as an agnostic starting point
    url = "https://remotive.com"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for job in data.get('jobs', []):
                listings.append({
                    "id": str(job.get('id')),
                    "title": job.get('title'),
                    "company": job.get('company_name'),
                    "description": job.get('description'),
                    "url": job.get('url'),
                    "date": job.get('publication_date', datetime.utcnow().strftime('%Y-%m-%d'))
                })
    except Exception as e:
        print(f"Primary API feed stream paused or unavailable: {e}")
    return listings

def process_pipeline():
    """Executes the ingestion, evaluation, drafting, and 7-day cleanup rules."""
    assets = get_master_assets()
    if not assets["resume"]:
        return

    # Configure the free Gemini API instance
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("Missing GEMINI_API_KEY secret environment variable.")
        return
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    raw_jobs = fetch_raw_listings()
    existing_rows = []
    existing_ids = set()

    # Load existing rows from your tracking file
    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
            existing_ids = {row['Job_ID'] for row in existing_rows}

    # Execute the 7-day cleanup rule for unapproved discovered positions
    today = datetime.utcnow()
    cleaned_rows = []
    for row in existing_rows:
        try:
            row_date = datetime.strptime(row['Date_Logged'], '%Y-%m-%d')
            is_expired = (today - row_date).days >= CLEANUP_DAYS
            if row['Status'] == 'Discovered' and is_expired:
                # If a drafted file folder was made for this expired job, remove it here
                continue 
        except ValueError:
            pass
        cleaned_rows.append(row)

    # Evaluate new incoming jobs against your strict profile metrics
    new_logs = []
    for job in raw_jobs[:10]:  # Evaluate the 10 newest items to conserve cloud rate limits
        if job['id'] in existing_ids:
            continue

               prompt = f"""
        You are Mueni Kitoko's Strategic Personal AI Agent. Review this job description against her Master Resume, and Full Portfolio Project Details.
        
        RESUME SUMMARY CONTEXT:
        {assets['resume']}

        DETAILED PORTFOLIO & 10 PROJECT DRAWERS CONTEXT:
        {assets['portfolio']}
        
        JOB TO EVALUATE:
        Company: {job['company']} | Title: {job['title']}
        Description: {job['description']}
        ...
        
        INSTRUCTIONS:
        1. Rate how strongly Mueni can solve this company's operational problems out of 100.
        2. Identify the core business pain point they are facing (e.g. data losses, scaling issues, un-automated pipelines).
        3. Draft a tailored cover letter variations by substituting relevant tokens from her master template. Position her as a definitive technical expert with high certainty of outcome.
        
        Return your analysis strictly in clean JSON format matching these exact keys:
        {{
            "score": integer_value,
            "extracted_problem": "short_sentence_on_their_pain_point",
            "custom_cover_letter_draft": "full_customized_text_of_the_letter"
        }}
        """
        try:
            response = model.generate_content(prompt)
            clean_text = response.text.strip().lstrip("```json").rstrip("```").strip()
            analysis = json.loads(clean_text)
            
            score = int(analysis.get('score', 0))
            status = "Discovered"
            draft_path = "N/A"

            # If it's a high-probability fit, write down the custom tailored assets immediately
            if score >= DRAFT_SCORE_THRESHOLD:
                folder_name = f"drafts/{job['company'].replace(' ', '_')}_{job['id']}"
                os.makedirs(folder_name, exist_ok=True)
                
                # Write the dynamic custom letter to its own workspace text file
                with open(f"{folder_name}/tailored_cover_letter.txt", "w") as f_cl:
                    f_cl.write(analysis.get('custom_cover_letter_draft', ''))
                
                draft_path = folder_name
                print(f" High match detected ({score}%). Application materials drafted for {job['company']}.")

            new_logs.append({
                "Job_ID": job['id'],
                "Company": job['company'],
                "Title": job['title'],
                "Score": str(score),
                "Status": status,
                "Identified_Problem": analysis.get('extracted_problem', ''),
                "Draft_Artifacts_Path": draft_path,
                "URL": job['url'],
                "Date_Logged": today.strftime('%Y-%m-%d')
            })
        except Exception as e:
            print(f"Skipping job ID {job['id']} due to parsing error: {e}")

    # Combine historical records with your freshly curated matching opportunities
    final_rows = cleaned_rows + new_logs
    
    # Save the updated data ledger back to your repository tracking dashboard
    fieldnames = ["Job_ID", "Company", "Title", "Score", "Status", "Identified_Problem", "Draft_Artifacts_Path", "URL", "Date_Logged"]
    with open(DASHBOARD_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)
    print("Tracking ledger update completed successfully.")

if __name__ == "__main__":
    process_pipeline()
