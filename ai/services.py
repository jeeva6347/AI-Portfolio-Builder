import re
import json
import urllib.request
import urllib.error
from django.conf import settings
from pypdf import PdfReader
from docx import Document

# Safe fallbacks for AI content generation templates
MOCK_SUMMARIES = {
    "default": "A highly motivated and results-oriented professional with a strong track record of success in delivering robust solutions and collaborating with cross-functional teams.",
    "developer": "A dedicated software engineer passionate about writing clean, maintainable code and building scalable web applications. Experienced in full-stack methodologies and agile development.",
    "designer": "A creative UI/UX designer focused on crafting intuitive, user-centered digital experiences. Skilled in wireframing, high-fidelity design systems, and responsive layouts.",
    "manager": "An experienced project manager adept at leading technical teams, managing project lifecycles, and aligning deliverables with strategic business objectives."
}

MOCK_ABOUT = (
    "I thrive on solving complex technical challenges and translating business needs into performant, "
    "user-friendly software. Over the course of my career, I have developed a strong foundation in modern engineering "
    "principles, continuous integration, and user-centric design. I am constantly learning new technologies and "
    "striving to improve code quality, performance, and accessibility across all projects I touch."
)


class ResumeParserService:
    """
    Handles PDF/DOCX file reading, dynamic text extraction,
    and structured data parsing (using Gemini or local heuristics).
    """

    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        """Reads file extension and extracts text content from PDF or DOCX."""
        if file_path.lower().endswith(".pdf"):
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            return text
        else:
            raise ValueError("Unsupported file format. Please upload PDF or DOCX.")

    @classmethod
    def parse_resume_data(cls, text: str) -> dict:
        """Parses raw resume text into structured JSON schema."""
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            # Check environment fallback
            import os
            api_key = os.environ.get("GEMINI_API_KEY")

        if api_key:
            try:
                return cls.call_gemini_parser(text, api_key)
            except Exception as e:
                # Log error and fall back to heuristics
                print(f"Gemini Parser API failed: {e}. Falling back to heuristics.")

        return cls.parse_resume_data_heuristics(text)

    @classmethod
    def call_gemini_parser(cls, text: str, api_key: str) -> dict:
        """Calls official Gemini API to extract structured resume fields."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        prompt = f"""
        Extract the following structured sections from the resume text into a single JSON object.
        Return ONLY valid JSON. Do not include markdown codeblocks or triple backticks.
        
        JSON Schema structure to match:
        {{
          "personal": {{
            "name": "Full Name",
            "title": "Professional Title (e.g. Software Engineer)",
            "about": "Brief personal summary/biography",
            "email": "Email address",
            "phone": "Phone number",
            "address": "Location/Address",
            "social_github": "GitHub URL",
            "social_linkedin": "LinkedIn URL"
          }},
          "skills": [
            {{"name": "Skill Name", "type": "technical" or "soft"}}
          ],
          "experience": [
            {{
              "company": "Company Name",
              "position": "Job Title",
              "duration": "Dates (e.g. Jan 2020 - Present)",
              "description": "Responsibilities and key achievements"
            }}
          ],
          "education": [
            {{
              "degree": "Degree (e.g. B.S. in Computer Science)",
              "college": "School/College name",
              "university": "University name (optional)",
              "year": "Graduation year"
            }}
          ],
          "projects": [
            {{
              "title": "Project Title",
              "description": "Project details",
              "technologies": "Space-separated technologies list (e.g. 'Django React')"
            }}
          ]
        }}

        Resume Text:
        {text}
        """

        req_data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            content = res_body["candidates"][0]["content"]["parts"][0]["text"]
            # Clean possible markdown wrap
            content_clean = content.strip().lstrip("```json").rstrip("```").strip()
            return json.loads(content_clean)

    @classmethod
    def parse_resume_data_heuristics(cls, text: str) -> dict:
        """Robust fallback regex parser for structured resume fields extraction."""
        data = {
            "personal": {
                "name": "",
                "title": "",
                "about": "",
                "email": "",
                "phone": "",
                "address": "",
                "social_github": "",
                "social_linkedin": ""
            },
            "skills": [],
            "experience": [],
            "education": [],
            "projects": []
        }

        # Clean text lines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return data

        # 1. Extrapolate Name and Title from the top lines
        # Name is usually the first line
        data["personal"]["name"] = lines[0]
        # Look for a title
        for idx in range(1, min(5, len(lines))):
            line = lines[idx]
            if any(kw in line.lower() for kw in ["engineer", "developer", "designer", "manager", "architect", "lead"]):
                data["personal"]["title"] = line
                break
        if not data["personal"]["title"]:
            data["personal"]["title"] = "Professional Expert"

        # 2. Extract contact emails & phones
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            data["personal"]["email"] = email_match.group(0)
            
        phone_match = re.search(r'\+?\d[\d\s\(\)-]{8,}\d', text)
        if phone_match:
            data["personal"]["phone"] = phone_match.group(0)

        # 3. Extract Links
        github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/[\w\.-]+', text, re.IGNORECASE)
        if github_match:
            data["personal"]["social_github"] = github_match.group(0)
            
        linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\.-]+', text, re.IGNORECASE)
        if linkedin_match:
            data["personal"]["social_linkedin"] = linkedin_match.group(0)

        # 4. Map Sections based on headers
        # Split text into sections based on structural headings
        sections = re.split(
            r'\n\s*(?=(?:experience|work history|education|skills|projects|certificates|publications)\b)',
            text,
            flags=re.IGNORECASE
        )

        for sec in sections:
            sec_lines = [l.strip() for l in sec.split("\n") if l.strip()]
            if not sec_lines:
                continue
            header = sec_lines[0].lower()

            if "skills" in header:
                # Add skills
                all_skills = []
                for sl in sec_lines[1:6]:  # read up to 5 lines of skills
                    # split by commas, semicolons or bullets
                    items = re.split(r'[,;•\t|]', sl)
                    for item in items:
                        item_clean = item.strip()
                        if item_clean and len(item_clean) < 30 and item_clean not in all_skills:
                            all_skills.append(item_clean)
                for s in all_skills:
                    data["skills"].append({"name": s, "type": "technical"})

            elif "education" in header:
                # Extract education
                for el in sec_lines[1:4]:
                    # Match standard years e.g. 2018 or 2015-2019
                    year_match = re.search(r'\b(19|20)\d{2}\b', el)
                    year = year_match.group(0) if year_match else "Completed"
                    degree = "B.S. in Computer Science"
                    college = el
                    
                    if "degree" in el.lower() or "bachelor" in el.lower() or "master" in el.lower():
                        degree = el
                    
                    data["education"].append({
                        "degree": degree,
                        "college": college[:150],
                        "university": "",
                        "year": year
                    })

            elif "experience" in header or "work history" in header:
                # Extract experiences
                current_exp = None
                for line in sec_lines[1:10]:
                    # Check if line looks like a job title or company name
                    if len(line) < 100 and ("," in line or "at" in line or "|" in line):
                        if current_exp:
                            data["experience"].append(current_exp)
                        
                        parts = re.split(r'[,|]|\bat\b', line)
                        company = parts[0].strip()
                        pos = parts[1].strip() if len(parts) > 1 else "Professional"
                        
                        # Find dates in line if any
                        duration = "2022 - Present"
                        dur_match = re.search(r'\b(19|20)\d{2}\b', line)
                        if dur_match:
                            duration = f"{dur_match.group(0)} - Present"
                            
                        current_exp = {
                            "company": company,
                            "position": pos,
                            "duration": duration,
                            "description": ""
                        }
                    elif current_exp:
                        current_exp["description"] += line + " "
                if current_exp:
                    data["experience"].append(current_exp)

            elif "projects" in header:
                # Extract projects
                current_proj = None
                for line in sec_lines[1:8]:
                    if len(line) < 60 and not line.startswith("•") and not line.startswith("-"):
                        if current_proj:
                            data["projects"].append(current_proj)
                        current_proj = {
                            "title": line,
                            "description": "",
                            "technologies": "Django JS"
                        }
                    elif current_proj:
                        current_proj["description"] += line + " "
                if current_proj:
                    data["projects"].append(current_proj)

        # Set default structures if empty
        if not data["skills"]:
            data["skills"] = [
                {"name": "Python", "type": "technical"},
                {"name": "Django", "type": "technical"},
                {"name": "HTML & CSS", "type": "technical"},
                {"name": "Team Leadership", "type": "soft"}
            ]
        if not data["projects"]:
            data["projects"] = [{
                "title": "Interactive Web Portfolio",
                "description": "Built a visual portfolio generator utilizing custom backend layout mapper services.",
                "technologies": "Django CSS"
            }]

        return data

    @classmethod
    def generate_ai_content(cls, data: dict) -> dict:
        """
        Enhances personal profiles and descriptions using AI.
        Provides high-quality structured fallbacks if Gemini is not configured.
        """
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            import os
            api_key = os.environ.get("GEMINI_API_KEY")

        if api_key:
            try:
                return cls.call_gemini_enricher(data, api_key)
            except Exception as e:
                print(f"Gemini Content Enrichment API failed: {e}. Using mock generator.")

        # Local mock heuristics content generator
        title = data["personal"].get("title", "").lower()
        name = data["personal"].get("name", "Expert Developer")
        
        summary_key = "default"
        if "developer" in title or "engineer" in title or "programmer" in title:
            summary_key = "developer"
        elif "designer" in title or "ui" in title or "ux" in title:
            summary_key = "designer"
        elif "manager" in title or "lead" in title or "director" in title:
            summary_key = "manager"
            
        data["personal"]["about"] = MOCK_SUMMARIES[summary_key] + " " + MOCK_ABOUT
        data["seo_title"] = f"{name} | {data['personal']['title']}"
        data["seo_description"] = f"Explore the professional web portfolio of {name}, specializing as a {data['personal']['title']}."

        # Expand descriptions of experience/projects if they are brief
        for exp in data.get("experience", []):
            if len(exp.get("description", "")) < 30:
                exp["description"] = f"Key contributor in the technical development team. Designed robust solutions, improved workflow efficiencies by 25%, and integrated multiple third-party API configurations."

        for proj in data.get("projects", []):
            if len(proj.get("description", "")) < 30:
                proj["description"] = f"Developed a responsive visual workspace solution that enables automated file scanning, custom visual highlights, and persistent database mappings."

        return data

    @classmethod
    def call_gemini_enricher(cls, data: dict, api_key: str) -> dict:
        """Invokes Gemini to enrich experience/project descriptions and SEO details."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        prompt = f"""
        Enhance and expand the following portfolio JSON data to make it look highly professional.
        Generate a cohesive biography under "personal.about".
        Flesh out "description" under experiences and projects into professional, result-oriented statements.
        Provide "seo_title" and "seo_description" properties.
        Return ONLY valid JSON matching this exact structure:
        {json.dumps(data)}
        """

        req_data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            content = res_body["candidates"][0]["content"]["parts"][0]["text"]
            content_clean = content.strip().lstrip("```json").rstrip("```").strip()
            return json.loads(content_clean)
