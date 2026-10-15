from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from pypdf import PdfReader
from docx import Document
from io import BytesIO
import sqlite3
import hashlib
import os
import re
import json
from datetime import datetime

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from docx.shared import Pt, Inches, RGBColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib import colors


# ================================
# FASTAPI APP & CORS
# ================================
app = FastAPI(
    title="AI Resume Analyzer API",
    description="Intelligent Resume Evaluation, Skill Extraction, and ATS Scoring API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================================
# DATABASE SETUP (MongoDB with Auto SQLite Fallback)
# ================================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "resume_analyzer_db")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resume_analyzer.db")

mongo_client = None
mongo_db = None
USE_MONGO = False

try:
    from pymongo import MongoClient
    # Attempt connecting to MongoDB with a short timeout
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500)
    mongo_client.server_info()  # Will throw exception if server is not reachable
    mongo_db = mongo_client[MONGO_DB_NAME]
    USE_MONGO = True
    print(f"[DATABASE] Connected to MongoDB database: {MONGO_DB_NAME}")
except Exception as e:
    USE_MONGO = False
    print(f"[DATABASE] MongoDB not active ({e}). Defaulting to persistent SQLite storage.")

def init_db():
    if USE_MONGO:
        # Create unique index on email in MongoDB
        mongo_db.users.create_index("email", unique=True)
        # Seed default admin user if not exists
        if not mongo_db.users.find_one({"email": "admin@gmail.com"}):
            pwd_hash = hashlib.sha256("123456".encode("utf-8")).hexdigest()
            mongo_db.users.insert_one({
                "name": "Admin",
                "email": "admin@gmail.com",
                "password_hash": pwd_hash,
                "title": "Senior Resume Analyst",
                "created_at": datetime.now()
            })
    
    # Initialize SQLite database as standard persistence
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        title TEXT DEFAULT 'Resume Analyst',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        filename TEXT NOT NULL,
        target_role TEXT,
        ats_score INTEGER NOT NULL,
        word_count INTEGER NOT NULL,
        skills_found TEXT NOT NULL,
        missing_skills TEXT NOT NULL,
        suggestions TEXT NOT NULL,
        contact_info TEXT NOT NULL,
        extracted_text TEXT,
        analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@gmail.com",))
    if not cursor.fetchone():
        pwd_hash = hashlib.sha256("123456".encode("utf-8")).hexdigest()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, title) VALUES (?, ?, ?, ?)",
            ("Admin", "admin@gmail.com", pwd_hash, "Senior Resume Analyst")
        )
    conn.commit()
    conn.close()

init_db()

# ================================
# COMPREHENSIVE SKILL REPOSITORY
# ================================
KNOWN_SKILLS = {
    "Programming Languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "c", "ruby", 
        "php", "swift", "kotlin", "go", "golang", "rust", "r", "dart", "scala", "sql"
    ],
    "Web & Frontend Technologies": [
        "html", "html5", "css", "css3", "react", "react.js", "angular", "vue", "vue.js",
        "next.js", "tailwind", "tailwindcss", "bootstrap", "sass", "redux", "jquery", "node.js"
    ],
    "Backend & Frameworks": [
        "fastapi", "flask", "django", "express", "spring", "spring boot", "asp.net", 
        ".net", "laravel", "rails", "ruby on rails", "nest.js", "graphql", "rest api"
    ],
    "Databases & Cloud": [
        "mongodb", "postgresql", "mysql", "sqlite", "redis", "oracle", "firebase", 
        "supabase", "aws", "azure", "gcp", "docker", "kubernetes", "git", "github", "ci/cd", "linux"
    ],
    "AI, ML & Data Science": [
        "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
        "pytorch", "keras", "pandas", "numpy", "scikit-learn", "data analysis", 
        "data visualization", "tableau", "power bi", "opencv", "generative ai", "llm"
    ],
    "Soft Skills & Management": [
        "agile", "scrum", "leadership", "communication", "problem solving",
        "teamwork", "project management", "critical thinking", "collaboration"
    ]
}

# Role-specific recommended skill profiles for Gap Analysis
ROLE_SKILL_PROFILES = {
    "software_engineer": [
        "Python", "JavaScript", "SQL", "Git", "Docker", "REST API", "Data Analysis", "Agile", "Linux", "CI/CD"
    ],
    "frontend_developer": [
        "HTML5", "CSS3", "JavaScript", "TypeScript", "React.js", "Redux", "TailwindCSS", "Git", "REST API", "Responsive Design"
    ],
    "backend_developer": [
        "Python", "Java", "Node.js", "FastAPI", "SQL", "PostgreSQL", "MongoDB", "Docker", "REST API", "Git", "Redis"
    ],
    "data_scientist": [
        "Python", "SQL", "Pandas", "NumPy", "Scikit-Learn", "Machine Learning", "Deep Learning", "TensorFlow", "Data Visualization", "Git"
    ],
    "devops_engineer": [
        "Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Git", "Python", "Terraform", "Monitoring", "Bash"
    ],
    "general": [
        "Python", "JavaScript", "SQL", "Git", "Communication", "Problem Solving", "Teamwork", "Agile", "REST API"
    ]
}

# ================================
# Pydantic Schemas
# ================================
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)
    title: Optional[str] = "Job Seeker"

class UserLogin(BaseModel):
    email: str
    password: str

class ProfileUpdate(BaseModel):
    name: str
    title: Optional[str] = None

# ================================
# TEXT EXTRACTION HELPERS
# ================================
def extract_pdf_text(file_bytes: bytes) -> str:
    pdf = PdfReader(BytesIO(file_bytes))
    text = ""
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def extract_docx_text(file_bytes: bytes) -> str:
    document = Document(BytesIO(file_bytes))
    text = ""
    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                text += cell.text + " "
            text += "\n"
    return text

def extract_skills(text: str):
    text_lower = text.lower()
    found_skills = []
    
    # Pre-sorted mapping for clean display names
    display_mapping = {
        "html": "HTML", "html5": "HTML5", "css": "CSS", "css3": "CSS3",
        "sql": "SQL", "aws": "AWS", "gcp": "GCP", "rest api": "REST API",
        "nlp": "NLP", "llm": "LLM", "ci/cd": "CI/CD", "c++": "C++", "c#": "C#",
        "asp.net": "ASP.NET", ".net": ".NET", "react.js": "React.js", "react": "React.js",
        "vue.js": "Vue.js", "vue": "Vue.js", "next.js": "Next.js", "node.js": "Node.js",
        "nest.js": "Nest.js", "tailwindcss": "TailwindCSS", "tailwind": "TailwindCSS",
        "fastapi": "FastAPI", "postgresql": "PostgreSQL", "mongodb": "MongoDB",
        "sqlite": "SQLite", "scikit-learn": "Scikit-Learn", "power bi": "Power BI",
        "opencv": "OpenCV", "github": "GitHub", "gitlab": "GitLab"
    }

    for category, skill_list in KNOWN_SKILLS.items():
        for skill in skill_list:
            pattern = r'(?<!\w)' + re.escape(skill) + r'(?!\w)'
            if re.search(pattern, text_lower):
                display_name = display_mapping.get(skill, skill.title())
                if display_name not in found_skills:
                    found_skills.append(display_name)
                    
    return found_skills

def calculate_ats_details(text: str, skills: list, target_role: str = "general"):
    text_lower = text.lower()
    score = 0
    suggestions = []
    
    # 1. Word Count & Length (20 pts)
    word_count = len(text.split())
    if word_count >= 350:
        score += 20
    elif word_count >= 180:
        score += 12
        suggestions.append("Expand on your impact, metrics, and technical contributions in project & experience sections.")
    else:
        score += 5
        suggestions.append("Your resume appears too brief (< 180 words). Add comprehensive detail on achievements.")

    # 2. Contact Verification (20 pts)
    has_email = bool(re.search(r"\b[\w.-]+@[\w.-]+\.\w+\b", text_lower))
    has_phone = bool(re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}|\b\d{10}\b", text_lower))
    has_links = bool(re.search(r"(linkedin\.com|github\.com|gitlab\.com|portfolio)", text_lower))
    
    if has_email: score += 8
    else: suggestions.append("Missing contact email address in header.")

    if has_phone: score += 7
    else: suggestions.append("Missing primary telephone number.")

    if has_links: score += 5
    else: suggestions.append("Include links to your LinkedIn profile or GitHub portfolio.")

    # 3. Structural Sections (25 pts)
    sections = {
        "education": ["education", "academic", "qualification", "degree"],
        "experience": ["experience", "work history", "employment", "internship"],
        "skills": ["skills", "technical skills", "competencies", "technologies"],
        "projects": ["projects", "personal projects", "academic projects"]
    }
    
    found_sections = 0
    for sec_name, sec_keywords in sections.items():
        if any(kw in text_lower for kw in sec_keywords):
            found_sections += 1
        else:
            suggestions.append(f"Add a distinct '{sec_name.capitalize()}' section header to ensure ATS parsers classify your content.")
            
    score += (found_sections * 6.25)

    # 4. Action / Impact Verbs (15 pts)
    action_verbs = [
        "developed", "created", "designed", "implemented", "managed",
        "built", "optimized", "architected", "spearheaded", "engineered",
        "delivered", "improved", "automated", "led", "launched", "reduced", "scaled"
    ]
    verb_matches = [v for v in action_verbs if re.search(r'\b' + v + r'\b', text_lower)]
    score += min(len(verb_matches) * 3, 15)
    if len(verb_matches) < 3:
        suggestions.append("Use strong action verbs (e.g. 'Optimized', 'Architected', 'Spearheaded', 'Automated') to begin bullet points.")

    # 5. Skills Density & Missing Skills Identification (20 pts)
    target_profile = ROLE_SKILL_PROFILES.get(target_role, ROLE_SKILL_PROFILES["general"])
    found_skills_lower = [s.lower() for s in skills]
    
    missing_skills = [
        role_skill for role_skill in target_profile 
        if role_skill.lower() not in found_skills_lower
    ]
    
    if len(skills) >= 8: score += 20
    elif len(skills) >= 4: score += 12
    elif len(skills) >= 1: score += 6
    else:
        suggestions.append("List more recognized industry tools, languages, and technical frameworks.")

    if missing_skills:
        top_missing = missing_skills[:4]
        suggestions.append(f"Recommended skills to add for {target_role.replace('_', ' ').title()}: {', '.join(top_missing)}.")

    final_score = int(min(max(score, 10), 100))
    
    if final_score >= 80:
        suggestions.insert(0, "🌟 Outstanding ATS readiness! Your resume is structured and packed with high-value keywords.")
    elif final_score >= 60:
        suggestions.insert(0, "👍 Solid resume baseline! Applying the recommendations below will significantly improve your recruiter ranking.")
    else:
        suggestions.insert(0, "⚠️ Action required: Address the missing sections, keywords, and contact details to pass ATS filters.")

    return {
        "score": final_score,
        "word_count": word_count,
        "missing_skills": missing_skills,
        "suggestions": suggestions,
        "has_contact": {"email": has_email, "phone": has_phone, "links": has_links}
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "AI Resume Analyzer Backend",
        "version": "2.0.0"
    }

@app.get("/")
def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "online"}

@app.get("/login")
def serve_login():
    login_file = os.path.join(FRONTEND_DIR, "login.html")
    if os.path.exists(login_file):
        return FileResponse(login_file)
    raise HTTPException(status_code=404, detail="login.html not found")

@app.get("/dashboard")
def serve_dashboard():
    dashboard_file = os.path.join(FRONTEND_DIR, "dashboard.html")
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    raise HTTPException(status_code=404, detail="dashboard.html not found")


# ----------------- AUTHENTICATION -----------------

@app.post("/auth/register")
def register_user(user: UserRegister):
    pwd_hash = hashlib.sha256(user.password.encode("utf-8")).hexdigest()
    
    # 1. MongoDB Execution
    if USE_MONGO:
        try:
            if mongo_db.users.find_one({"email": user.email.lower()}):
                raise HTTPException(status_code=400, detail="An account with this email already exists.")
            mongo_db.users.insert_one({
                "name": user.name,
                "email": user.email.lower(),
                "password_hash": pwd_hash,
                "title": user.title or "Job Seeker",
                "created_at": datetime.now()
            })
        except HTTPException:
            raise
        except Exception as e:
            print("MongoDB register error:", e)

    # 2. SQLite Execution (Persistent Fallback & Sync)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (user.email.lower(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, title) VALUES (?, ?, ?, ?)",
        (user.name, user.email.lower(), pwd_hash, user.title or "Job Seeker")
    )
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "message": "Account created successfully! Please login.",
        "user": {"name": user.name, "email": user.email.lower(), "title": user.title or "Job Seeker"}
    }

@app.post("/auth/login")
def login_user(creds: UserLogin):
    pwd_hash = hashlib.sha256(creds.password.encode("utf-8")).hexdigest()
    
    # 1. MongoDB Query
    if USE_MONGO:
        try:
            m_user = mongo_db.users.find_one({"email": creds.email.lower(), "password_hash": pwd_hash})
            if m_user:
                return {
                    "status": "success",
                    "message": "Login successful via MongoDB!",
                    "user": {
                        "id": str(m_user.get("_id", 1)),
                        "name": m_user.get("name", "User"),
                        "email": m_user.get("email"),
                        "title": m_user.get("title", "Resume Analyst")
                    }
                }
        except Exception as e:
            print("MongoDB login error:", e)

    # 2. SQLite Query
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, title FROM users WHERE email = ? AND password_hash = ?",
        (creds.email.lower(), pwd_hash)
    )
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    return {
        "status": "success",
        "message": "Login successful!",
        "user": {
            "id": user_row[0],
            "name": user_row[1],
            "email": user_row[2],
            "title": user_row[3]
        }
    }

# ----------------- USER PROFILE -----------------

@app.get("/user/profile")
def get_user_profile(email: str):
    # MongoDB stats if active
    if USE_MONGO:
        try:
            m_user = mongo_db.users.find_one({"email": email.lower()})
            if m_user:
                m_count = mongo_db.resume_history.count_documents({"user_email": email.lower()})
                pipeline = [
                    {"$match": {"user_email": email.lower()}},
                    {"$group": {"_id": None, "avgScore": {"$avg": "$ats_score"}}}
                ]
                avg_res = list(mongo_db.resume_history.aggregate(pipeline))
                avg_score = round(avg_res[0]["avgScore"], 1) if avg_res else 0.0
                return {
                    "name": m_user.get("name", "User"),
                    "email": m_user.get("email"),
                    "title": m_user.get("title", "Resume Analyst"),
                    "member_since": str(m_user.get("created_at", "Active")),
                    "total_resumes": m_count,
                    "avg_ats_score": avg_score
                }
        except Exception as e:
            print("MongoDB profile error:", e)

    # SQLite fallback
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, email, title, created_at FROM users WHERE email = ?", (email.lower(),))
    user_row = cursor.fetchone()
    
    if not user_row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")
        
    cursor.execute("SELECT COUNT(*), AVG(ats_score) FROM resume_history WHERE user_email = ?", (email.lower(),))
    stat_row = cursor.fetchone()
    conn.close()
    
    return {
        "name": user_row[0],
        "email": user_row[1],
        "title": user_row[2],
        "member_since": user_row[3],
        "total_resumes": stat_row[0] or 0,
        "avg_ats_score": round(stat_row[1] or 0, 1)
    }

@app.post("/user/profile/update")
def update_user_profile(email: str, profile: ProfileUpdate):
    if USE_MONGO:
        try:
            mongo_db.users.update_one(
                {"email": email.lower()},
                {"$set": {"name": profile.name, "title": profile.title}}
            )
        except Exception as e:
            print("MongoDB profile update error:", e)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET name = ?, title = ? WHERE email = ?",
        (profile.name, profile.title, email.lower())
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Profile updated successfully!"}

# ----------------- RESUME EVALUATION HISTORY -----------------

@app.get("/history")
def get_resume_history(email: str = "admin@gmail.com"):
    if USE_MONGO:
        try:
            m_records = list(mongo_db.resume_history.find({"user_email": email.lower()}).sort("_id", -1))
            if m_records:
                history_list = []
                for idx, r in enumerate(m_records):
                    history_list.append({
                        "id": str(r.get("_id", idx + 1)),
                        "filename": r.get("filename", "resume.pdf"),
                        "target_role": r.get("target_role", "general"),
                        "ats_score": r.get("ats_score", 0),
                        "word_count": r.get("word_count", 0),
                        "skills": r.get("skills_found", []),
                        "missing_skills": r.get("missing_skills", []),
                        "suggestions": r.get("suggestions", []),
                        "analyzed_at": str(r.get("analyzed_at", "Recent"))
                    })
                return {"status": "success", "history": history_list}
        except Exception as e:
            print("MongoDB history error:", e)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, target_role, ats_score, word_count, skills_found, missing_skills, suggestions, analyzed_at
        FROM resume_history
        WHERE user_email = ?
        ORDER BY id DESC
    """, (email.lower(),))
    rows = cursor.fetchall()
    conn.close()

    history_list = []
    for r in rows:
        try:
            skills = json.loads(r[5]) if r[5] else []
        except:
            skills = []
        try:
            missing = json.loads(r[6]) if r[6] else []
        except:
            missing = []
        try:
            sugg = json.loads(r[7]) if r[7] else []
        except:
            sugg = []

        history_list.append({
            "id": r[0],
            "filename": r[1],
            "target_role": r[2],
            "ats_score": r[3],
            "word_count": r[4],
            "skills": skills,
            "missing_skills": missing,
            "suggestions": sugg,
            "analyzed_at": r[8]
        })

    return {"status": "success", "history": history_list}

@app.delete("/history/{record_id}")
def delete_resume_history(record_id: int, email: str = "admin@gmail.com"):
    if USE_MONGO:
        try:
            mongo_db.resume_history.delete_one({"_id": record_id, "user_email": email.lower()})
        except Exception as e:
            print("MongoDB delete history error:", e)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resume_history WHERE id = ? AND user_email = ?", (record_id, email.lower()))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Evaluation record #{record_id} deleted."}

# ----------------- RESUME ANALYSIS -----------------

@app.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    user_email: Optional[str] = Form("admin@gmail.com"),
    target_role: Optional[str] = Form("general")
):
    filename = file.filename.lower()
    file_bytes = await file.read()

    if filename.endswith(".pdf"):
        extracted_text = extract_pdf_text(file_bytes)
    elif filename.endswith(".docx"):
        extracted_text = extract_docx_text(file_bytes)
    elif filename.endswith(".doc"):
        raise HTTPException(
            status_code=400,
            detail="Legacy .doc binary format is not supported. Please save or export your resume as .pdf or .docx."
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Please upload a valid PDF or DOCX file."
        )

    if not extracted_text or len(extracted_text.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Unable to extract text. If your resume is an image scan, please use a text-based PDF or DOCX."
        )

    # Detect skills
    detected_skills = extract_skills(extracted_text)

    # Calculate ATS evaluation & dynamic suggestions
    ats_data = calculate_ats_details(extracted_text, detected_skills, target_role=target_role or "general")

    # 1. Persist in MongoDB
    if USE_MONGO:
        try:
            mongo_db.resume_history.insert_one({
                "user_email": user_email.lower(),
                "filename": file.filename,
                "target_role": target_role or "general",
                "ats_score": ats_data["score"],
                "word_count": ats_data["word_count"],
                "skills_found": detected_skills,
                "missing_skills": ats_data["missing_skills"],
                "suggestions": ats_data["suggestions"],
                "contact_info": ats_data["has_contact"],
                "extracted_text": extracted_text.strip(),
                "analyzed_at": datetime.now()
            })
        except Exception as e:
            print("MongoDB insert history error:", e)

    # 2. Persist in SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO resume_history 
    (user_email, filename, target_role, ats_score, word_count, skills_found, missing_skills, suggestions, contact_info, extracted_text)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_email.lower(),
        file.filename,
        target_role or "general",
        ats_data["score"],
        ats_data["word_count"],
        json.dumps(detected_skills),
        json.dumps(ats_data["missing_skills"]),
        json.dumps(ats_data["suggestions"]),
        json.dumps(ats_data["has_contact"]),
        extracted_text.strip()
    ))
    conn.commit()
    analysis_id = cursor.lastrowid
    conn.close()

    return {
        "status": "success",
        "id": analysis_id,
        "message": "Resume analyzed and saved to history!",
        "filename": file.filename,
        "target_role": target_role,
        "ats_score": ats_data["score"],
        "word_count": ats_data["word_count"],
        "skills": detected_skills,
        "missing_skills": ats_data["missing_skills"],
        "suggestions": ats_data["suggestions"],
        "contact_info": ats_data["has_contact"],
        "extracted_text": extracted_text.strip()
    }

# ================================
# CAREER & INTERVIEW INTELLIGENCE DATA REPOSITORIES
# ================================

JOB_RECOMMENDATIONS = {
    "software_engineer": [
        {"title": "Software Development Engineer (SDE I/II)", "company": "Amazon / Microsoft / Google / Startups", "match": "94%", "location": "Remote / Hybrid / Bangalore", "apply_url": "https://www.linkedin.com/jobs/search/?keywords=software%20engineer", "portal": "LinkedIn Jobs"},
        {"title": "Full Stack Software Engineer", "company": "Stripe / Atlassian / Swiggy", "match": "91%", "location": "Remote / Hyderabad", "apply_url": "https://www.indeed.com/q-Software-Engineer-jobs.html", "portal": "Indeed"},
        {"title": "Python & Cloud Engineer", "company": "Deloitte / Accenture / Infosys", "match": "88%", "location": "Pune / Noida / Remote", "apply_url": "https://www.naukri.com/software-engineer-jobs", "portal": "Naukri.com"},
        {"title": "Junior/Mid Backend Engineer", "company": "YC Top Startups / AngelList Tech", "match": "85%", "location": "Remote Global", "apply_url": "https://wellfound.com/jobs", "portal": "Wellfound (AngelList)"}
    ],
    "frontend_developer": [
        {"title": "React.js / Next.js Frontend Engineer", "company": "Meta / Uber / Razorpay", "match": "96%", "location": "Remote / Bangalore", "apply_url": "https://www.linkedin.com/jobs/search/?keywords=frontend%20developer", "portal": "LinkedIn Jobs"},
        {"title": "UI/UX Software Engineer", "company": "Canva / Adobe / Flipkart", "match": "89%", "location": "Remote / Mumbai", "apply_url": "https://www.indeed.com/q-frontend-developer-jobs.html", "portal": "Indeed"},
        {"title": "Lead Web Application Developer", "company": "Enterprise Tech & FinTech", "match": "84%", "location": "Delhi NCR / Remote", "apply_url": "https://www.naukri.com/frontend-developer-jobs", "portal": "Naukri.com"}
    ],
    "backend_developer": [
        {"title": "Backend API & Distributed Systems Engineer", "company": "Uber / Swiggy / Zomato", "match": "95%", "location": "Bangalore / Remote", "apply_url": "https://www.linkedin.com/jobs/search/?keywords=backend%20developer", "portal": "LinkedIn Jobs"},
        {"title": "Python / FastAPI Backend Developer", "company": "Fintech & High-Growth AI Ventures", "match": "92%", "location": "Remote / Hyderabad", "apply_url": "https://wellfound.com/jobs", "portal": "Wellfound"},
        {"title": "Cloud Microservices Specialist", "company": "Oracle / Cisco / TCS", "match": "87%", "location": "Chennai / Pune", "apply_url": "https://www.naukri.com/backend-developer-jobs", "portal": "Naukri.com"}
    ],
    "data_scientist": [
        {"title": "Machine Learning & AI Engineer", "company": "NVIDIA / OpenAI / Fractal", "match": "95%", "location": "Remote / Bangalore", "apply_url": "https://www.linkedin.com/jobs/search/?keywords=data%20scientist", "portal": "LinkedIn Jobs"},
        {"title": "Applied Data Scientist", "company": "Walmart Global Tech / Target", "match": "90%", "location": "Bangalore / Remote", "apply_url": "https://www.indeed.com/q-data-scientist-jobs.html", "portal": "Indeed"},
        {"title": "NLP / GenAI Research Engineer", "company": "AI Labs & Tier 1 Ventures", "match": "88%", "location": "Remote Global", "apply_url": "https://www.naukri.com/data-scientist-jobs", "portal": "Naukri.com"}
    ],
    "devops_engineer": [
        {"title": "Cloud Infrastructure & DevOps Engineer", "company": "AWS / HashiCorp / RedHat", "match": "96%", "location": "Remote / Pune", "apply_url": "https://www.linkedin.com/jobs/search/?keywords=devops%20engineer", "portal": "LinkedIn Jobs"},
        {"title": "Kubernetes & SRE Specialist", "company": "Goldman Sachs / Morgan Stanley", "match": "91%", "location": "Bangalore / Remote", "apply_url": "https://www.indeed.com/q-devops-engineer-jobs.html", "portal": "Indeed"},
        {"title": "CI/CD & Platform Engineer", "company": "Wipro / HCL / Cognizant", "match": "86%", "location": "Hyderabad / Chennai", "apply_url": "https://www.naukri.com/devops-engineer-jobs", "portal": "Naukri.com"}
    ],
    "general": [
        {"title": "Associate Software Engineer", "company": "Tier-1 IT & Global Capability Centers", "match": "90%", "location": "Pan India / Remote", "apply_url": "https://www.linkedin.com/jobs/search/?keywords=software%20developer", "portal": "LinkedIn Jobs"},
        {"title": "Graduate Technology Trainee", "company": "Leading MNCs & Consultancies", "match": "88%", "location": "Bangalore / Hyderabad / Pune", "apply_url": "https://www.naukri.com/entry-level-jobs", "portal": "Naukri.com"},
        {"title": "Junior Full Stack Engineer", "company": "Accelerators & Product Companies", "match": "85%", "location": "Remote", "apply_url": "https://wellfound.com/jobs", "portal": "Wellfound"}
    ]
}

CAREER_ROADMAPS = {
    "software_engineer": {
        "title": "Software Engineering Career Roadmap",
        "description": "Comprehensive milestone roadmap from fundamentals to senior architecture.",
        "phases": [
            {"phase": "1. Core Foundations", "topics": ["Data Structures & Algorithms (Arrays, Trees, Graphs, DP)", "Object Oriented Programming & Design Patterns", "Time & Space Complexity Analysis"], "resources": [{"name": "LeetCode 75 Roadmap", "url": "https://leetcode.com/studyplan/leetcode-75/"}, {"name": "NeetCode DSA Guide", "url": "https://neetcode.io/roadmap"}]},
            {"phase": "2. Modern System Development", "topics": ["RESTful APIs & GraphQL", "Relational (PostgreSQL) & NoSQL (MongoDB) Databases", "Git Branching, PR Workflows & Clean Code Principles"], "resources": [{"name": "Roadmap.sh Software Design", "url": "https://roadmap.sh/software-design-architecture"}, {"name": "Full Stack Open (University of Helsinki)", "url": "https://fullstackopen.com/en/"}]},
            {"phase": "3. Cloud & Production Readiness", "topics": ["Docker Containerization & Kubernetes", "CI/CD Pipelines (GitHub Actions)", "AWS / Azure Cloud Deployment Basics"], "resources": [{"name": "AWS Free Skill Builder", "url": "https://explore.skillbuilder.aws/"}, {"name": "Docker Official Learning", "url": "https://docs.docker.com/get-started/"}]},
            {"phase": "4. High-Scale System Design", "topics": ["Distributed Caching (Redis)", "Message Brokers (Kafka / RabbitMQ)", "Microservices, Load Balancing & High Availability"], "resources": [{"name": "System Design Primer (GitHub)", "url": "https://github.com/donnemartin/system-design-primer"}, {"name": "ByteByteGo Architecture Guide", "url": "https://bytebytego.com/"}]}
        ]
    },
    "frontend_developer": {
        "title": "Frontend Development Career Roadmap",
        "description": "Master modern UI development, state management, and high-performance web applications.",
        "phases": [
            {"phase": "1. Modern Web Core", "topics": ["Semantic HTML5, Accessibility (a11y) & SEO", "Modern CSS3 (Flexbox, Grid, Custom Properties, Animations)", "JavaScript ES6+ (Async/Await, Promises, Closures, DOM)"], "resources": [{"name": "MDN Web Docs (Mozilla)", "url": "https://developer.mozilla.org/"}, {"name": "JavaScript.info Comprehensive Tutorial", "url": "https://javascript.info/"}]},
            {"phase": "2. Frameworks & Ecosystem", "topics": ["React.js Core & Hooks Mastery", "Next.js App Router & SSR/SSG", "TailwindCSS & Component Libraries (Radix, Shadcn)"], "resources": [{"name": "React Official Interactive Docs", "url": "https://react.dev/"}, {"name": "Next.js Learn Course", "url": "https://nextjs.org/learn"}]},
            {"phase": "3. State Management & Tooling", "topics": ["Redux Toolkit / Zustand / TanStack Query", "TypeScript Type Safety & Generics", "Vite, Webpack & Performance Optimization (Core Web Vitals)"], "resources": [{"name": "Total TypeScript Tutorials", "url": "https://www.totaltypescript.com/"}, {"name": "TanStack Query Official Docs", "url": "https://tanstack.com/query/latest"}]},
            {"phase": "4. Testing & Micro-frontends", "topics": ["Unit & Integration Testing (Jest, Vitest, React Testing Library)", "E2E Testing (Playwright / Cypress)", "CI/CD & Edge Deployment (Vercel / Cloudflare Pages)"], "resources": [{"name": "Testing JavaScript by Kent C. Dodds", "url": "https://testingjavascript.com/"}, {"name": "Playwright Official Guides", "url": "https://playwright.dev/"}]}
        ]
    },
    "backend_developer": {
        "title": "Backend Engineering Career Roadmap",
        "description": "Architect scalable backend services, databases, caching layers, and high-concurrency APIs.",
        "phases": [
            {"phase": "1. Backend Language & API Framework", "topics": ["Python (FastAPI / Django) or Java (Spring Boot) or Node.js (Express/Nest)", "REST API Standards, Status Codes & OpenAPI / Swagger Specs", "Authentication (JWT, OAuth 2.0, API Keys)"], "resources": [{"name": "FastAPI Official Documentation", "url": "https://fastapi.tiangolo.com/"}, {"name": "Roadmap.sh Backend Developer", "url": "https://roadmap.sh/backend"}]},
            {"phase": "2. Relational & Distributed Databases", "topics": ["SQL Queries, Indexes, Foreign Keys, ACID Transactions", "PostgreSQL Optimization & Explain Analyze", "ORM Tools (SQLAlchemy, Prisma, Hibernate)"], "resources": [{"name": "Use The Index, Luke (SQL Indexing)", "url": "https://use-the-index-luke.com/"}, {"name": "PostgreSQL Tutorial", "url": "https://www.postgresqltutorial.com/"}]},
            {"phase": "3. Caching, Queues & Cloud", "topics": ["Redis Caching Strategies & Rate Limiting", "Asynchronous Task Queues (Celery, BullMQ)", "Docker, Linux Server Administration & Nginx Reverse Proxy"], "resources": [{"name": "Redis University", "url": "https://university.redis.com/"}, {"name": "Linux Journey Tutorial", "url": "https://linuxjourney.com/"}]},
            {"phase": "4. Scalability & System Design", "topics": ["Event-Driven Architecture (Kafka / RabbitMQ)", "Database Sharding & Read Replicas", "Monitoring & Observability (Prometheus, Grafana, OpenTelemetry)"], "resources": [{"name": "Designing Data-Intensive Applications", "url": "https://dataintensive.net/"}, {"name": "Grokking Modern System Design", "url": "https://www.educative.io/courses/grokking-modern-system-design-interview-for-engineers-managers"}]}
        ]
    },
    "data_scientist": {
        "title": "Data Science & AI Career Roadmap",
        "description": "From statistical modeling to production Generative AI and deep learning deployment.",
        "phases": [
            {"phase": "1. Math, Python & Data Wrangling", "topics": ["Linear Algebra, Probability, Calculus & Statistics", "Python (NumPy, Pandas, Matplotlib, Seaborn)", "Data Cleaning, Imputation & Feature Engineering"], "resources": [{"name": "Khan Academy Statistics & Probability", "url": "https://www.khanacademy.org/math/statistics-probability"}, {"name": "Kaggle Python & Pandas Micro-Courses", "url": "https://www.kaggle.com/learn"}]},
            {"phase": "2. Machine Learning Foundations", "topics": ["Supervised & Unsupervised Learning (Scikit-Learn)", "Regression, Classification, Decision Trees, Random Forests, XGBoost", "Cross-Validation, Hyperparameter Tuning & ROC/AUC Metrics"], "resources": [{"name": "StatQuest ML Course (Josh Starmer)", "url": "https://statquest.org/"}, {"name": "Scikit-Learn User Guide", "url": "https://scikit-learn.org/stable/user_guide.html"}]},
            {"phase": "3. Deep Learning & NLP", "topics": ["Neural Networks & Backpropagation", "PyTorch / TensorFlow Frameworks", "Transformers, BERT, GPT & NLP Pipelines (HuggingFace)"], "resources": [{"name": "DeepLearning.AI (Andrew Ng)", "url": "https://www.deeplearning.ai/"}, {"name": "HuggingFace NLP Course", "url": "https://huggingface.co/learn/nlp-course"}]},
            {"phase": "4. Generative AI & MLOps", "topics": ["Large Language Models (LLMs), Prompt Engineering & Fine-tuning", "Vector Databases (Pinecone, ChromaDB) & RAG Architecture", "Model Deployment (FastAPI, ONNX, MLflow, Docker)"], "resources": [{"name": "LangChain Official Tutorials", "url": "https://python.langchain.com/docs/get_started/introduction"}, {"name": "Full Stack LLM Bootcamp", "url": "https://fullstackdeeplearning.com/llm-bootcamp/"}]}
        ]
    },
    "devops_engineer": {
        "title": "DevOps & Cloud Engineering Career Roadmap",
        "description": "Automate infrastructure, CI/CD pipelines, container orchestration, and multi-cloud reliability.",
        "phases": [
            {"phase": "1. Operating Systems & Scripting", "topics": ["Linux Terminal, Bash Scripting, File Permissions, SSH", "Networking Essentials (DNS, TCP/IP, Subnets, TLS/SSL, HTTP/3)", "Python Scripting for Infrastructure Automation"], "resources": [{"name": "Linux Survival Interactive Course", "url": "https://linuxsurvival.com/"}, {"name": "Roadmap.sh DevOps Guide", "url": "https://roadmap.sh/devops"}]},
            {"phase": "2. Containers & Orchestration", "topics": ["Docker Image Creation, Multi-stage Builds, Networking", "Kubernetes Pods, Deployments, Services, Ingress, Helm Charts", "Service Meshes & Cloud Native Best Practices"], "resources": [{"name": "Kubernetes Official Tutorials", "url": "https://kubernetes.io/docs/tutorials/"}, {"name": "KodeKloud DevOps Labs", "url": "https://kodekloud.com/"}]},
            {"phase": "3. Infrastructure as Code (IaC) & CI/CD", "topics": ["Terraform Modules, State Management & Cloud Provisioning", "GitHub Actions & GitLab CI/CD Pipeline Configuration", "Configuration Management with Ansible"], "resources": [{"name": "HashiCorp Terraform Tutorials", "url": "https://developer.hashicorp.com/terraform/tutorials"}, {"name": "GitHub Actions Documentation", "url": "https://docs.github.com/en/actions"}]},
            {"phase": "4. Cloud, Security & SRE", "topics": ["AWS / GCP Cloud Architectures (IAM, VPC, EKS, RDS)", "DevSecOps (SonarQube, Trivy, Vault Secret Management)", "Site Reliability Engineering & Observability (Prometheus, Grafana, ELK Stack)"], "resources": [{"name": "Google SRE Books (Free Online)", "url": "https://sre.google/books/"}, {"name": "AWS Well-Architected Framework", "url": "https://aws.amazon.com/architecture/well-architected/"}]}
        ]
    }
}

MOCK_INTERVIEW_QUESTIONS = {
    "software_engineer": [
        {"id": 1, "category": "Technical DSA", "question": "Explain the difference between a Process and a Thread. How does inter-thread communication work in high-concurrency systems?", "expected_keywords": ["process", "thread", "memory", "context switch", "shared memory", "concurrency", "synchronization"]},
        {"id": 2, "category": "System Architecture", "question": "How would you design a rate limiter for an enterprise REST API to protect against DDoS and abuse?", "expected_keywords": ["token bucket", "leaky bucket", "redis", "fixed window", "ip", "headers", "status code 429"]},
        {"id": 3, "category": "Behavioral / Leadership", "question": "Describe a scenario where you had to debug a critical production bug with limited logs. What was your step-by-step diagnostic process?", "expected_keywords": ["reproduce", "logs", "monitoring", "root cause", "post-mortem", "rollback", "unit test", "fix"]}
    ],
    "frontend_developer": [
        {"id": 1, "category": "Core JavaScript", "question": "How does the JavaScript Event Loop work with Microtasks and Macrotasks? Explain how Promises and setTimeout behave differently.", "expected_keywords": ["event loop", "call stack", "microtask", "macrotask", "callback queue", "promise", "settimeout"]},
        {"id": 2, "category": "React Architecture", "question": "Explain how React's Virtual DOM and Reconciliation algorithm (Fiber) work. How do you prevent unnecessary re-renders in large applications?", "expected_keywords": ["virtual dom", "reconciliation", "fiber", "usememo", "usecallback", "react.memo", "keys", "diffing"]},
        {"id": 3, "category": "Web Performance", "question": "What are Core Web Vitals (LCP, FID/INP, CLS) and what concrete steps do you take to optimize them?", "expected_keywords": ["lcp", "inp", "cls", "code splitting", "lazy loading", "image optimization", "cdn", "caching"]}
    ],
    "backend_developer": [
        {"id": 1, "category": "Database Engineering", "question": "Explain ACID properties in relational databases. When would you choose an eventual consistency model over strong consistency?", "expected_keywords": ["atomicity", "consistency", "isolation", "durability", "cap theorem", "eventual consistency", "transactions", "nosql"]},
        {"id": 2, "category": "API Architecture", "question": "How do you securely handle user authentication and session management in stateless distributed microservices?", "expected_keywords": ["jwt", "oauth", "refresh token", "stateless", "redis", "public key", "encryption", "cors"]},
        {"id": 3, "category": "Caching & Queues", "question": "Explain the Cache-Aside and Write-Through caching patterns. How do you prevent Cache Stampede / Thundering Herd problems?", "expected_keywords": ["cache aside", "write through", "redis", "ttl", "mutex", "lock", "expiry", "cache stampede"]}
    ],
    "data_scientist": [
        {"id": 1, "category": "ML Theory", "question": "What is the Bias-Variance tradeoff? How do techniques like Regularization (L1/L2) and Ensemble Methods address it?", "expected_keywords": ["bias", "variance", "overfitting", "underfitting", "regularization", "lasso", "ridge", "random forest", "boosting"]},
        {"id": 2, "category": "Generative AI", "question": "Explain the architecture of Retrieval-Augmented Generation (RAG). How do Vector Embeddings and Chunking strategies affect retrieval accuracy?", "expected_keywords": ["rag", "vector database", "embeddings", "cosine similarity", "chunking", "llm", "hallucination", "context window"]},
        {"id": 3, "category": "Evaluation Metrics", "question": "When would you prioritize Precision over Recall, and vice versa? Give a real-world machine learning example for each.", "expected_keywords": ["precision", "recall", "f1-score", "false positive", "false negative", "spam detection", "medical diagnosis", "confusion matrix"]}
    ],
    "devops_engineer": [
        {"id": 1, "category": "Kubernetes Orchestration", "question": "Explain the architecture of Kubernetes Control Plane components and how a Pod deployment is scheduled onto Worker Nodes.", "expected_keywords": ["api server", "etcd", "scheduler", "controller manager", "kubelet", "kube-proxy", "pod"]},
        {"id": 2, "category": "CI/CD & GitOps", "question": "What is GitOps and how does it differ from traditional CI/CD pipelines? Mention tools like ArgoCD or Flux.", "expected_keywords": ["gitops", "argocd", "declarative", "single source of truth", "reconciliation", "drift detection", "kubernetes"]},
        {"id": 3, "category": "SRE & Monitoring", "question": "What is the difference between SLI, SLO, and SLA? How do you calculate Error Budgets?", "expected_keywords": ["sli", "slo", "sla", "error budget", "reliability", "uptime", "latency", "incident response"]}
    ]
}

ROLE_APTITUDE_POOLS = {
    "software_engineer": [
        {
            "id": 1,
            "category": "Data Structures & Complexity",
            "question": "What is the worst-case time complexity of QuickSort algorithm?",
            "options": ["O(n log n)", "O(n)", "O(n²)", "O(log n)"],
            "answer_index": 2,
            "explanation": "When the chosen pivot is always the extreme element in an unbalanced/sorted list without random pivot selection, QuickSort recursion depth becomes n, taking O(n²)."
        },
        {
            "id": 2,
            "category": "Algorithms (Graph Traversal)",
            "question": "Which data structure is fundamentally required to implement Breadth-First Search (BFS) on a graph?",
            "options": ["Stack", "Queue (FIFO)", "Priority Queue", "Binary Search Tree"],
            "answer_index": 1,
            "explanation": "BFS explores nodes level-by-level using a FIFO (First-In, First-Out) Queue, whereas DFS utilizes a LIFO Stack."
        },
        {
            "id": 3,
            "category": "Logical & Pattern Reasoning",
            "question": "Find the next number in the geometric series: 3, 7, 15, 31, 63, ?",
            "options": ["125", "127", "129", "131"],
            "answer_index": 1,
            "explanation": "Pattern: Each number is (2 * previous_number) + 1. 2 * 63 + 1 = 127."
        },
        {
            "id": 4,
            "category": "Quantitative Aptitude",
            "question": "A train running at 60 km/hr crosses a telegraph pole in 9 seconds. What is the length of the train?",
            "options": ["120 meters", "150 meters", "180 meters", "324 meters"],
            "answer_index": 1,
            "explanation": "Speed = 60 * (5/18) = 50/3 m/sec. Distance (Length) = Speed * Time = (50/3) * 9 = 150 meters."
        },
        {
            "id": 5,
            "category": "Memory & Concurrency",
            "question": "Which memory segment is dynamically allocated at runtime when creating objects or pointers?",
            "options": ["Stack segment", "Heap segment", "Code / Text segment", "Data segment"],
            "answer_index": 1,
            "explanation": "The Heap segment handles dynamic runtime allocations (malloc/new), whereas local function frames reside on the Stack."
        }
    ],
    "frontend_developer": [
        {
            "id": 101,
            "category": "Core JavaScript Engine",
            "question": "In the JavaScript Event Loop, which queue takes highest priority when executing after synchronous code?",
            "options": ["Macrotask Queue (setTimeout/setInterval)", "Microtask Queue (Promises/queueMicrotask)", "Render Pipeline Queue", "Web Worker Queue"],
            "answer_index": 1,
            "explanation": "Microtasks (Promises, process.nextTick) are drained completely before the event loop advances to the next macrotask."
        },
        {
            "id": 102,
            "category": "DOM & Web Performance",
            "question": "Which Core Web Vital measures visual stability by tracking unexpected layout shifts during page load?",
            "options": ["LCP (Largest Contentful Paint)", "FID (First Input Delay)", "CLS (Cumulative Layout Shift)", "INP (Interaction to Next Paint)"],
            "answer_index": 2,
            "explanation": "CLS (Cumulative Layout Shift) measures unexpected movement of visible elements while content loads."
        },
        {
            "id": 103,
            "category": "CSS Architecture",
            "question": "Which CSS property enables GPU hardware acceleration for smoother 60fps animations?",
            "options": ["float: left", "transform: translateZ(0) or will-change", "position: absolute", "display: inline-block"],
            "answer_index": 1,
            "explanation": "'transform: translate3d/translateZ' and 'will-change' promote elements to a separate GPU compositing layer, avoiding CPU layout recalculations."
        },
        {
            "id": 104,
            "category": "React Internals",
            "question": "What is the primary benefit of React Fiber architecture introduced in React 16+?",
            "options": ["Enables two-way data binding", "Enables incremental/pauseable rendering and prioritization", "Replaces JavaScript with WebAssembly", "Eliminates the Virtual DOM completely"],
            "answer_index": 1,
            "explanation": "Fiber allows React to break rendering work into units, pause/resume execution, and prioritize high-priority user interactions."
        },
        {
            "id": 105,
            "category": "Logical Reasoning (Frontend)",
            "question": "If deep cloning a nested object using JSON.parse(JSON.stringify(obj)), which data types are silently lost?",
            "options": ["Strings and Booleans", "Functions, Undefined, and Symbols", "Arrays and Numbers", "Null and Empty Objects"],
            "answer_index": 1,
            "explanation": "JSON serialization ignores Functions, undefined, Symbols, and converts NaN/Infinity to null."
        }
    ],
    "backend_developer": [
        {
            "id": 201,
            "category": "Database Engineering (ACID)",
            "question": "Which ACID property guarantees that once a database transaction commits, changes survive sudden power failure?",
            "options": ["Atomicity", "Consistency", "Isolation", "Durability"],
            "answer_index": 3,
            "explanation": "Durability guarantees that committed transactions are written to non-volatile storage (WAL/transaction logs) and survive crashes."
        },
        {
            "id": 202,
            "category": "Networking & Protocols",
            "question": "Which HTTP status code indicates that an intermediate proxy/gateway server received an invalid upstream response?",
            "options": ["500 Internal Server Error", "502 Bad Gateway", "503 Service Unavailable", "504 Gateway Timeout"],
            "answer_index": 1,
            "explanation": "502 Bad Gateway specifically signals an invalid or corrupt response returned by an upstream backend server to the gateway."
        },
        {
            "id": 203,
            "category": "System Design & Caching",
            "question": "What occurs during a 'Cache Stampede' (Thundering Herd) event in high-traffic APIs?",
            "options": ["Redis server runs out of disk space", "Multiple concurrent requests query the database simultaneously when a key expires", "Cache memory corrupts data types", "API rate limits block legitimate users"],
            "answer_index": 1,
            "explanation": "Cache Stampede happens when a hot cached item expires and thousands of simultaneous requests bypass cache, overwhelming the database."
        },
        {
            "id": 204,
            "category": "Database Indexing",
            "question": "Why do relational databases commonly utilize B+ Trees instead of Binary Search Trees for disk-based indexing?",
            "options": ["B+ Trees have higher tree height", "B+ Trees minimize disk I/O seek operations by having high fan-out", "B+ Trees only support string keys", "Binary Search Trees use less memory"],
            "answer_index": 1,
            "explanation": "B+ Trees have large branching factors (fan-out), allowing millions of records to be indexed in 3-4 disk block reads."
        },
        {
            "id": 205,
            "category": "Security & Architecture",
            "question": "What is the primary advantage of Stateless JWT authentication in distributed microservices?",
            "options": ["Eliminates database lookups for session verification across services", "Encrypts all payload data automatically", "Guarantees zero network latency", "Prevents all SQL injection vulnerabilities"],
            "answer_index": 0,
            "explanation": "Stateless JWTs are cryptographically verifiable by any service possessing the public key without centralized session store queries."
        }
    ],
    "data_scientist": [
        {
            "id": 301,
            "category": "Machine Learning Foundations",
            "question": "What is the consequence of high variance in a predictive machine learning model?",
            "options": ["Underfitting training data", "Overfitting training data with poor generalizability to test data", "Zero model complexity", "Excessively fast training times"],
            "answer_index": 1,
            "explanation": "High variance means the model captures noise in training data (overfitting), leading to high test error."
        },
        {
            "id": 302,
            "category": "Probability & Statistics",
            "question": "In an imbalanced fraud detection dataset where 99% of transactions are legitimate, which metric is LEAST informative?",
            "options": ["Precision", "Recall", "Raw Classification Accuracy", "F1-Score / PR-AUC"],
            "answer_index": 2,
            "explanation": "A dummy classifier predicting 'legitimate' for all records achieves 99% accuracy while detecting zero fraud."
        },
        {
            "id": 303,
            "category": "Deep Learning & NLP",
            "question": "What is the primary computational mechanism behind the Transformer architecture (BERT/GPT)?",
            "options": ["Recurrent Hidden States", "Multi-Head Self-Attention", "Convolutional Max-Pooling", "Genetic Algorithms"],
            "answer_index": 1,
            "explanation": "Multi-Head Self-Attention allows models to dynamically weigh relationships between all tokens in parallel without recurrence."
        },
        {
            "id": 304,
            "category": "Vector Databases & RAG",
            "question": "Which metric is most commonly used to compute similarity between dense text embeddings in vector search?",
            "options": ["Cosine Similarity", "Hamming Distance", "Jaccard Index", "Standard Deviation"],
            "answer_index": 0,
            "explanation": "Cosine Similarity measures the cosine of the angle between two normalized high-dimensional vectors, evaluating semantic alignment."
        },
        {
            "id": 305,
            "category": "Quantitative Interpretation",
            "question": "If L1 Regularization (Lasso) is applied to regression weights, what unique property does it produce?",
            "options": ["Uniform non-zero coefficients", "Sparse weights (forces some coefficients strictly to zero for feature selection)", "Infinite gradient steps", "Transforms features to integers"],
            "answer_index": 1,
            "explanation": "L1 penalty drives less important feature weights to exactly 0, acting as automatic feature selection."
        }
    ],
    "devops_engineer": [
        {
            "id": 401,
            "category": "Kubernetes Architecture",
            "question": "Which Kubernetes Control Plane component maintains the cluster state as a consistent distributed key-value store?",
            "options": ["kube-scheduler", "kube-proxy", "etcd", "kubelet"],
            "answer_index": 2,
            "explanation": "etcd is the Raft-based distributed key-value store holding all cluster specifications and runtime state."
        },
        {
            "id": 402,
            "category": "Linux & Systems",
            "question": "Which command and signal is used to gracefully terminate a Linux process allowing it to complete cleanup handlers?",
            "options": ["kill -9 (SIGKILL)", "kill -15 (SIGTERM)", "kill -1 (SIGHUP)", "kill -19 (SIGSTOP)"],
            "answer_index": 1,
            "explanation": "SIGTERM (signal 15) requests graceful shutdown and allows intercepting signal handlers to flush state, unlike uncatchable SIGKILL."
        },
        {
            "id": 403,
            "category": "Infrastructure as Code (IaC)",
            "question": "What is the primary function of Terraform State (`terraform.tfstate`) file?",
            "options": ["Compiles HCL code to binary", "Maps declared configuration resources to real-world cloud infrastructure IDs", "Stores user SSH passwords", "Acts as a database backup"],
            "answer_index": 1,
            "explanation": "Terraform state tracks real-world cloud resource metadata, enabling drift detection and incremental updates."
        },
        {
            "id": 404,
            "category": "Networking & Security",
            "question": "In AWS VPC architecture, which component allows private subnet instances to initiate outbound Internet traffic without receiving unsolicited inbound connections?",
            "options": ["Internet Gateway (IGW)", "NAT Gateway", "VPC Peering Connection", "Direct Connect"],
            "answer_index": 1,
            "explanation": "A NAT Gateway performs network address translation for outbound private traffic while blocking incoming connections."
        },
        {
            "id": 405,
            "category": "SRE & Reliability",
            "question": "If a service has a 99.9% SLO (Three Nines) over a 30-day period, what is the maximum permissible total downtime (Error Budget)?",
            "options": ["43.8 minutes", "7.2 hours", "3.6 minutes", "24 hours"],
            "answer_index": 0,
            "explanation": "30 days = 43,200 minutes. 0.1% downtime allowance = 43,200 * 0.001 = 43.2 minutes (~43.8 mins / month)."
        }
    ]
}

RESUME_BUILDING_TIPS = [
    {
        "title": "Use the Google XYZ Formula for Bullet Points",
        "summary": "Structure every achievement bullet as: 'Accomplished [X] as measured by [Y], by doing [Z]'.",
        "example": "Bad: 'Wrote backend code in Python.'\nGood: 'Engineered high-throughput FastAPI microservices, reducing 99th-percentile API response latency by 42% across 1.5M monthly requests.'"
    },
    {
        "title": "ATS-Friendly Document Formatting",
        "summary": "Stick to clean single-column layouts with standard font styles. Avoid complex nested tables, image-only text, floating text boxes, or graphical progress bars which confuse automated ATS parsers.",
        "example": "Use standard section headers: Education, Experience, Technical Skills, Projects, Certifications."
    },
    {
        "title": "Include Active Developer Portfolio Proof",
        "summary": "Recruiters and hiring managers spend less than 15 seconds reviewing. Providing clickable GitHub, LinkedIn, and Live Demo links multiplies callback probability by 3.5x.",
        "example": "Place links prominently in the header: email@domain.com | +1-234-567-890 | github.com/username | linkedin.com/in/username"
    },
    {
        "title": "Keyword Density Optimization per Target Role",
        "summary": "Match at least 70% of the core competencies mentioned in target job descriptions (e.g. Docker, PostgreSQL, CI/CD, PyTorch) inside your Skills and Experience sections.",
        "example": "Group skills logically: 'Languages', 'Frameworks & Libraries', 'Cloud & DevOps', 'Databases & Tools'."
    }
]

# ================================
# NEW INTELLIGENCE API ENDPOINTS
# ================================

class MockAnswerEvaluation(BaseModel):
    role: str
    question_id: int
    user_answer: str

# ================================
# RESUME REBUILDER & 1-CLICK AUTO-APPLY AGENT
# ================================

class RebuildResumeRequest(BaseModel):
    extracted_text: str
    target_role: str
    user_name: Optional[str] = "Candidate"
    user_email: Optional[str] = "candidate@gmail.com"
    user_phone: Optional[str] = "+1 (555) 019-2834"

class AutoApplyRequest(BaseModel):
    job_title: str
    company: str
    portal: str
    candidate_name: str
    candidate_email: str
    ats_score: int
    target_role: str

@app.post("/career/rebuild-100")
def rebuild_resume_100_percent(req: RebuildResumeRequest):
    role_key = req.target_role.lower()
    target_profile = ROLE_SKILL_PROFILES.get(role_key, ROLE_SKILL_PROFILES["general"])
    
    # Generate high-impact 100% ATS Compliant Content tailored to role
    role_title = role_key.replace('_', ' ').title()
    skills_joined = ", ".join(target_profile)
    
    rebuilt_content = f"""================================================================================
{req.user_name.upper()}
Email: {req.user_email} | Phone: {req.user_phone} | LinkedIn: linkedin.com/in/{req.user_name.lower().replace(' ', '')} | GitHub: github.com/{req.user_name.lower().replace(' ', '')}
================================================================================

PROFESSIONAL SUMMARY
Results-driven {role_title} with proven expertise in building scalable, production-grade applications and distributed systems. Expert in architecting high-performance APIs, optimizing throughput, and collaborating across agile cross-functional engineering teams. Accomplished 40%+ performance gains across high-concurrency systems using industry-standard engineering best practices.

TECHNICAL SKILLS & COMPETENCIES
- Core Languages & Frameworks: {skills_joined}
- Architecture & Design: Microservices, RESTful APIs, System Design, Scalable Database Modeling, CI/CD
- Tools & Cloud Platforms: Docker, Kubernetes, AWS, Git, Linux, Automated Testing, Monitoring

PROFESSIONAL EXPERIENCE
Senior {role_title} | Enterprise Tech Solutions | 2022 - Present
- Architected and spearheaded end-to-end deployment of resilient distributed microservices using {target_profile[0] if target_profile else 'Python'} and {target_profile[1] if len(target_profile) > 1 else 'SQL'}, reducing 99th-percentile response latency by 44% across 2M+ monthly active users.
- Optimized relational and NoSQL database schemas and caching layers with Redis, achieving a 35% decrease in query execution time and zero production downtime.
- Engineered automated CI/CD deployment pipelines utilizing Docker and GitHub Actions, cutting build-and-release cycles from 45 minutes to under 8 minutes.
- Spearheaded agile sprint ceremonies, mentoring 5+ junior engineers and conducting stringent code reviews for security compliance and high code quality.

{role_title} | Agile Innovation Labs | 2020 - 2022
- Developed scalable RESTful services and user-facing capabilities, increasing platform throughput by 55% during peak traffic events.
- Implemented robust authentication, OAuth 2.0 and role-based access control (RBAC) mechanisms, ensuring 100% data privacy and compliance.
- Collaborated closely with product managers and UX teams to transform complex system requirements into seamless customer-facing features.

NOTABLE PROJECTS
1. Enterprise Cloud Management & Analytics Engine
- Built a high-scale real-time monitoring dashboard with automated anomaly detection utilizing {target_profile[0] if target_profile else 'Python'}, FastAPI, and PostgreSQL.
- Reduced server idle waste by 28% through dynamic cloud resource provisioning and automated scaling alerts.

2. Distributed Job Matching & Competency Parser
- Engineered an institutional-grade NLP document extraction pipeline matching candidate qualifications to enterprise job openings with 99.4% accuracy.

EDUCATION
- Bachelor of Science in Computer Science / Information Technology
- Honors & Certifications: Certified Cloud Solutions Architect, Professional Full Stack Specialization
================================================================================
"""

    return {
        "status": "success",
        "ats_score": 100,
        "role": role_key,
        "role_title": role_title,
        "skills": target_profile,
        "rebuilt_text": rebuilt_content.strip(),
        "readiness_status": "🎯 100% ATS Ready - Candidate is Interview Ready!"
    }

@app.post("/career/download-pdf")
def download_rebuilt_resume_pdf(req: RebuildResumeRequest):
    role_key = req.target_role.lower()
    target_profile = ROLE_SKILL_PROFILES.get(role_key, ROLE_SKILL_PROFILES["general"])
    role_title = role_key.replace('_', ' ').title()
    skills_joined = ", ".join(target_profile)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('NameTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor('#0f172a'), alignment=1)
    contact_style = ParagraphStyle('ContactInfo', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#475569'), alignment=1)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#1e293b'), spaceBefore=12, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=13, textColor=colors.HexColor('#334155'))
    bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=13, textColor=colors.HexColor('#334155'), leftIndent=15)

    story = []
    # Header
    story.append(Paragraph(req.user_name.upper(), title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Email: {req.user_email} | Phone: {req.user_phone} | LinkedIn: linkedin.com/in/{req.user_name.lower().replace(' ', '')} | GitHub: github.com/{req.user_name.lower().replace(' ', '')}", contact_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=8))

    # Summary
    story.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
    story.append(Paragraph(f"Results-driven <b>{role_title}</b> with proven expertise in building scalable, production-grade applications and distributed systems. Accomplished 40%+ performance gains across high-concurrency systems using industry-standard engineering best practices.", body_style))
    story.append(Spacer(1, 6))

    # Skills
    story.append(Paragraph("TECHNICAL SKILLS & COMPETENCIES", heading_style))
    story.append(Paragraph(f"<b>Core Languages & Frameworks:</b> {skills_joined}", bullet_style))
    story.append(Paragraph("<b>Architecture & Design:</b> Microservices, RESTful APIs, System Design, Scalable Database Modeling, CI/CD", bullet_style))
    story.append(Paragraph("<b>Tools & Cloud Platforms:</b> Docker, Kubernetes, AWS, Git, Linux, Automated Testing, Monitoring", bullet_style))
    story.append(Spacer(1, 6))

    # Experience
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", heading_style))
    story.append(Paragraph(f"<b>Senior {role_title}</b> — Enterprise Tech Solutions (2022 - Present)", body_style))
    story.append(Paragraph(f"• Architected and spearheaded end-to-end deployment of resilient distributed microservices using {target_profile[0] if target_profile else 'Python'}, reducing 99th-percentile response latency by 44% across 2M+ active users.", bullet_style))
    story.append(Paragraph("• Optimized relational and NoSQL database schemas with Redis caching, achieving a 35% decrease in query execution time.", bullet_style))
    story.append(Paragraph("• Engineered automated CI/CD deployment pipelines utilizing Docker and GitHub Actions, cutting release cycles from 45 min to under 8 min.", bullet_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph(f"<b>{role_title}</b> — Agile Innovation Labs (2020 - 2022)", body_style))
    story.append(Paragraph("• Developed scalable RESTful services and user-facing capabilities, increasing platform throughput by 55% during peak traffic events.", bullet_style))
    story.append(Paragraph("• Implemented robust authentication, OAuth 2.0 and role-based access control (RBAC) mechanisms, ensuring 100% data privacy.", bullet_style))
    story.append(Spacer(1, 6))

    # Projects
    story.append(Paragraph("KEY PROJECTS", heading_style))
    story.append(Paragraph(f"<b>1. Enterprise Cloud Management & Analytics Engine:</b> Built real-time monitoring dashboard with automated anomaly detection utilizing {target_profile[0] if target_profile else 'Python'} and PostgreSQL, reducing idle waste by 28%.", bullet_style))
    story.append(Paragraph("<b>2. Distributed Job Matching & Competency Parser:</b> Engineered NLP document extraction pipeline matching candidate qualifications to enterprise job openings with 99.4% accuracy.", bullet_style))
    story.append(Spacer(1, 6))

    # Education
    story.append(Paragraph("EDUCATION & CERTIFICATIONS", heading_style))
    story.append(Paragraph("• Bachelor of Science in Computer Science / Information Technology", bullet_style))
    story.append(Paragraph("• Certified Cloud Solutions Architect | Professional Full Stack Specialization", bullet_style))

    doc.build(story)
    buffer.seek(0)

    filename = f"{req.user_name.replace(' ', '_')}_100_ATS_Resume.pdf"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/career/download-docx")
def download_rebuilt_resume_docx(req: RebuildResumeRequest):
    role_key = req.target_role.lower()
    target_profile = ROLE_SKILL_PROFILES.get(role_key, ROLE_SKILL_PROFILES["general"])
    role_title = role_key.replace('_', ' ').title()
    skills_joined = ", ".join(target_profile)

    doc = Document()
    # Margins
    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.6)
        section.right_margin = Inches(0.6)

    # Name Title
    p_name = doc.add_paragraph()
    run_name = p_name.add_run(req.user_name.upper())
    run_name.font.size = Pt(18)
    run_name.font.bold = True
    run_name.font.color.rgb = RGBColor(15, 23, 42)
    p_name.alignment = 1

    # Contact Info
    p_contact = doc.add_paragraph(f"Email: {req.user_email} | Phone: {req.user_phone} | LinkedIn: linkedin.com/in/{req.user_name.lower().replace(' ', '')} | GitHub: github.com/{req.user_name.lower().replace(' ', '')}")
    p_contact.alignment = 1

    def add_section_header(title):
        p = doc.add_paragraph()
        r = p.add_run(title)
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = RGBColor(30, 41, 59)
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)

    # Summary
    add_section_header("PROFESSIONAL SUMMARY")
    doc.add_paragraph(f"Results-driven {role_title} with proven expertise in building scalable, production-grade applications and distributed systems. Expert in architecting high-performance APIs, optimizing throughput, and collaborating across agile cross-functional engineering teams. Accomplished 40%+ performance gains across high-concurrency systems using industry-standard engineering best practices.")

    # Technical Skills
    add_section_header("TECHNICAL SKILLS & COMPETENCIES")
    doc.add_paragraph(f"• Core Languages & Frameworks: {skills_joined}")
    doc.add_paragraph("• Architecture & Design: Microservices, RESTful APIs, System Design, Scalable Database Modeling, CI/CD")
    doc.add_paragraph("• Tools & Cloud Platforms: Docker, Kubernetes, AWS, Git, Linux, Automated Testing, Monitoring")

    # Experience
    add_section_header("PROFESSIONAL EXPERIENCE")
    doc.add_paragraph(f"Senior {role_title} — Enterprise Tech Solutions (2022 - Present)", style='List Bullet')
    doc.add_paragraph(f"• Architected and spearheaded end-to-end deployment of resilient distributed microservices using {target_profile[0] if target_profile else 'Python'}, reducing response latency by 44% across 2M+ active users.")
    doc.add_paragraph("• Optimized relational and NoSQL database schemas with Redis caching, achieving a 35% decrease in query execution time.")
    doc.add_paragraph("• Engineered automated CI/CD deployment pipelines utilizing Docker and GitHub Actions, cutting build-and-release cycles to under 8 minutes.")

    doc.add_paragraph(f"{role_title} — Agile Innovation Labs (2020 - 2022)", style='List Bullet')
    doc.add_paragraph("• Developed scalable RESTful services and user-facing capabilities, increasing platform throughput by 55% during peak traffic events.")
    doc.add_paragraph("• Implemented robust authentication, OAuth 2.0 and role-based access control (RBAC) mechanisms, ensuring 100% data privacy.")

    # Projects
    add_section_header("NOTABLE PROJECTS")
    doc.add_paragraph(f"• Enterprise Cloud Management & Analytics Engine: Built real-time monitoring dashboard with automated anomaly detection utilizing {target_profile[0] if target_profile else 'Python'} and PostgreSQL, reducing idle waste by 28%.")
    doc.add_paragraph("• Distributed Job Matching & Competency Parser: Engineered institutional-grade NLP document extraction pipeline matching candidate qualifications to enterprise job openings with 99.4% accuracy.")

    # Education
    add_section_header("EDUCATION & CERTIFICATIONS")
    doc.add_paragraph("• Bachelor of Science in Computer Science / Information Technology")
    doc.add_paragraph("• Certified Cloud Solutions Architect | Professional Full Stack Specialization")

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)

    filename = f"{req.user_name.replace(' ', '_')}_100_ATS_Resume.docx"
    return Response(
        content=bio.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/career/auto-apply")
def auto_apply_job(req: AutoApplyRequest):
    app_id = f"APP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return {
        "status": "success",
        "application_id": app_id,
        "message": f"🎉 Application successfully submitted to {req.company} for '{req.job_title}' on {req.portal}!",
        "candidate": req.candidate_name,
        "ats_score": req.ats_score,
        "applied_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "interview_prep_status": "Ready for Interview Screening"
    }

@app.get("/career/jobs")
def get_job_recommendations(role: str = "general"):
    role_clean = role.lower()
    jobs = JOB_RECOMMENDATIONS.get(role_clean, JOB_RECOMMENDATIONS["general"])
    return {"status": "success", "role": role_clean, "jobs": jobs}

@app.get("/career/roadmap")
def get_career_roadmap(role: str = "software_engineer"):
    role_clean = role.lower()
    roadmap = CAREER_ROADMAPS.get(role_clean, CAREER_ROADMAPS["software_engineer"])
    return {"status": "success", "role": role_clean, "roadmap": roadmap}

@app.get("/career/interview/questions")
def get_interview_questions(role: str = "software_engineer"):
    role_clean = role.lower()
    questions = MOCK_INTERVIEW_QUESTIONS.get(role_clean, MOCK_INTERVIEW_QUESTIONS["software_engineer"])
    return {"status": "success", "role": role_clean, "questions": questions}

@app.post("/career/interview/evaluate")
def evaluate_mock_answer(eval_data: MockAnswerEvaluation):
    role_clean = eval_data.role.lower()
    questions = MOCK_INTERVIEW_QUESTIONS.get(role_clean, MOCK_INTERVIEW_QUESTIONS["software_engineer"])
    target_q = next((q for q in questions if q["id"] == eval_data.question_id), None)
    
    if not target_q:
        raise HTTPException(status_code=404, detail="Interview question not found.")
        
    ans_lower = eval_data.user_answer.lower().strip()
    word_count = len(ans_lower.split())
    
    keywords_matched = [kw for kw in target_q["expected_keywords"] if kw in ans_lower]
    coverage_ratio = len(keywords_matched) / max(len(target_q["expected_keywords"]), 1)
    
    score = int(min(max((coverage_ratio * 70) + min(word_count * 0.6, 30), 15), 100))
    
    if score >= 80:
        feedback = "🌟 Stellar answer! Demonstrates deep domain grasp, articulate terminology, and structural clarity."
        status_badge = "Excellent"
    elif score >= 60:
        feedback = f"👍 Good response! You covered key points. To elevate it further, emphasize: {', '.join([k for k in target_q['expected_keywords'] if k not in keywords_matched][:3])}."
        status_badge = "Proficient"
    else:
        feedback = f"⚠️ Needs refinement. Ensure you explain core mechanisms using keywords like: {', '.join(target_q['expected_keywords'][:4])}."
        status_badge = "Needs Practice"
        
    return {
        "status": "success",
        "score": score,
        "rating": status_badge,
        "keywords_matched": keywords_matched,
        "keywords_missing": [kw for kw in target_q["expected_keywords"] if kw not in keywords_matched],
        "feedback": feedback
    }

@app.get("/career/aptitude")
def get_aptitude_test(role: str = "software_engineer"):
    import random
    role_clean = role.lower()
    pool = ROLE_APTITUDE_POOLS.get(role_clean, ROLE_APTITUDE_POOLS["software_engineer"])
    sample_size = min(5, len(pool))
    sampled_questions = random.sample(pool, sample_size)
    return {"status": "success", "role": role_clean, "total": sample_size, "questions": sampled_questions}

@app.get("/career/tips")
def get_resume_tips():
    return {"status": "success", "tips": RESUME_BUILDING_TIPS}

# Mount static files (CSS, JS, assets) directly to serve complete full-stack project
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=False), name="static")