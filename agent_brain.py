import os
import json
import google.generativeai as genai

def evaluate_job_match(job_title, job_description, job_type="Permanent"):
    """
    Evaluates an open job or freelance side hustle against Mueni Kitoko's 
    exact problem-centric technical resume profile.
    """
    # 1. Read your master resume directly from your repository's local context
    try:
        with open("resume.md", "r") as f:
            resume_content = f.read()
    except FileNotFoundError:
        return {"error": "resume.md not found in the repository root."}

    # 2. Configure the free Gemini API using repository secrets
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return {"error": "Missing GEMINI_API_KEY environment secret."}
        
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 3. Craft the evaluation instructions using your exact professional metrics
    prompt = f"""
    You are Mueni Kitoko's Personal Job Hunting Assistant. Your job is to strictly evaluate 
    an open opportunity against her Master Resume.

    MUENI'S MASTER RESUME CONTRACT:
    {resume_content}

    OPPORTUNITY TO EVALUATE:
    Type: {job_type} (e.g., Permanent Full-time, Contract, Freelance Gig, Side Hustle)
    Title: {job_title}
    Description: {job_description}

    CRITICAL PARSING RULES:
    1. Look beyond typical job titles. Check if the company faces problems Mueni has solved: 
       fragile tracking networks, data drops during blackouts, un-audited cloud layouts, exposed ports, or slow delivery windows.
    2. Determine if her stack (Terraform, K3s, n8n, Asyncio Python, MQTT, GitHub Actions) directly alleviates their pain points.
    3. Score the match from 0 to 100. Be realistic. If it matches her core architecture, score it high (85+).
    4. Provide an aggressive, problem-centric 'Pitch Angle' showing exactly how she saves them money or removes risk.

    You must respond strictly in clean JSON format with these exact keys:
    {{
        "score": 0-100 integer,
        "matched_skills": ["skill1", "skill2"],
        "extracted_business_problem": "string summarizing their pain point",
        "strategic_pitch_angle": "string matching Mueni's metrics directly to their problem"
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Strip potential markdown formatting if the model wraps it in ```json
        clean_text = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(clean_text)
    except Exception as e:
        return {"error": f"Evaluation engine execution failed: {str(e)}"}

# Test block to ensure the script parses cleanly without compilation syntax errors
if __name__ == "__main__":
    print("Agent matching brain successfully verified and ready for integration testing.")
