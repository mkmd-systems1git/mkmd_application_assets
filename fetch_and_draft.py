import os
import csv
import json
import urllib.request
from datetime import datetime
import google.generativeai as genai

# Configuration constants
DRAFT_SCORE_THRESHOLD = 85
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
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                assets["portfolio"] = f.read()
    except Exception as e:
        print(f"Error loading foundational assets: {e}")
    return assets

def fetch_raw_listings():
    """Pulls recent developer postings from the free global Remotive data stream."""
    listings = []
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

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("Missing GEMINI_API_KEY secret environment variable.")
        return
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    raw_jobs = fetch_raw_listings()
    existing_rows = []
    existing_ids = set()

    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
            existing_ids = {row['JOB_ID'] for row in existing_rows if 'JOB_ID' in row}

    today = datetime.utcnow()
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
    for job in raw_jobs[:10]: # Process 10 items per cycle to manage cloud limits safely
        if job['id'] in existing_ids:
            continue

        prompt = f"""
        You are Mueni Kitoko's Strategic Personal AI Agent. Review this job description against her Master Resume and Full Portfolio.
        
        RESUME SUMMARY CONTEXT:
        {assets['resume']}

        DETAILED PORTFOLIO CONTEXT:
        {assets['portfolio']}
        
        JOB TO EVALUATE:
        Company: {job['company']} | Title: {job['title']}
        Description: {job['description']}
        
        INSTRUCTIONS:
        1. Rate how strongly Mueni can solve this company's operational problems out of 100.
        2. Identify the core business pain point they are facing.
        3. Formulate a 1-sentence aggressive technical pitch angle linking her metrics directly to their problem.
        4. Identify the Target Market Sector (e.g., Maritime, Fintech, Logistics, SaaS, Enterprise).
        5. Identify the Target Platform/Cloud Stack requested (e.g., AWS, GCP, K3s Hybrid, Multi-Cloud).
        6. Extract the offered salary or income floor listed. If none is listed, write "Market Rate".
        7. Check if they mention providing a hardware laptop or equipment. Write "Yes", "No", or "Not Specified".
        8. Draft a tailored cover letter by substituting relevant tokens from her master template.
        
        Return your analysis strictly in clean JSON format matching these exact keys:
        {{
            "score": integer_value,
            "extracted_problem": "string_describing_their_pain_point",
            "strategic_pitch": "string_of_one_sentence_pitch",
            "market_sector": "string",
            "platform_stack": "string",
            "income_floor": "string",
            "hardware_required": "string",
            "custom_cover_letter_draft": "full_customized_text_of_the_letter"
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
                # Create a direct link to the folder inside your github repo
                repo_env = os.environ.get('GITHUB_REPOSITORY', 'mkmd-systems1git/mkmd_application_assets')
                draft_path = f"https://github.com{repo_env}/tree/main/{folder_name}"

            # Align rows perfectly with Airtable column headers
            new_logs.append({
                "JOB_ID": job['id'],
                "Date_Logged": today.strftime('%Y-%m-%d'),
                "Target_Market_Sector": analysis.get('market_sector', 'Technical Data'),
                "Target_Platform": analysis.get('platform_stack', 'Cloud Core'),
                "Company_Name": job['company'],
                "Position_Title": job['title'],
                "Offered_Income_Floor": analysis.get('income_floor', 'Market Rate'),
                "Hardware_Laptop_Required": analysis.get('hardware_required', 'Not Specified'),
                "Status_Tracking": "Discovered",
                "SCORE": str(score),
                "Problem to solve": analysis.get('extracted_problem', ''),
                "Strategic_Pitch_Angle": analysis.get('strategic_pitch', ''),
                "Draft_Artifacts_Path": draft_path,
                "URL": job['url']
            })
            print(f"Processed match check for {job['company']}: SCORE {score}%")
        except Exception as e:
            print(f"Skipping job ID {job['id']} due to parsing error: {e}")

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
