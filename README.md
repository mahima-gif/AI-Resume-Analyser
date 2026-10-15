# AI Resume Analyzer 🤖

A full-stack, AI-powered Resume Evaluation & ATS (Applicant Tracking System) platform. Built with a high-performance **FastAPI** Python backend, SQLite database persistence, and a modern glassmorphic **HTML5/CSS3/JavaScript** frontend.

---

## 🚀 Key Functional Features

1. **User Authentication & Profiles**:
   - Register new user accounts and login with SHA-256 hashed password authentication.
   - Profile management with customizable name and professional title.
   - Default seeded credentials (`admin@gmail.com` / `123456`).
2. **Multi-Format Resume Text Extraction**:
   - Extract text from `.pdf` documents using `pypdf`.
   - Extract text from `.docx` documents (including tables and structured paragraphs) using `python-docx`.
3. **Advanced Multi-Factor ATS Scoring**:
   - **Content Length & Volume Check** (Word count depth evaluation).
   - **Contact Channels Detection** (Email, Phone number, LinkedIn / GitHub / Portfolio links).
   - **Structural Section Verification** (Education, Experience, Skills, Projects).
   - **Action & Power Verbs Density** (*Developed, Optimized, Engineered, Spearheaded, Automated, etc.*).
4. **Skill & Missing Competency Detection**:
   - Categorized matching across **Programming Languages**, **Frontend/Backend Web Frameworks**, **Cloud & Databases**, and **AI/Data Science Tools**.
   - **Gap Analysis**: Identifies missing skills required for specific target job roles (e.g. *Software Engineer, Frontend Developer, Backend Developer, Data Scientist, DevOps Engineer*).
5. **Resume Evaluation History & Reports**:
   - Persistent storage in SQLite (`resume_analyzer.db`).
   - History table view with score tags, target roles, and delete actions.
6. **Single Page Application (SPA) Dashboard**:
   - Tab views for Dashboard/Analyzer, History Reports, and User Profile.
   - Real-time statistics counters and extracted text preview.

---

## 📁 Final Project Structure

```
AI Resume analyser/
├── backend/
│   ├── main.py              # FastAPI backend API (Auth, Extraction, ATS, Skills, DB)
│   ├── requirements.txt     # Python backend dependencies
│   └── resume_analyzer.db   # SQLite persistent database (Auto-created)
├── dashboard.html           # Main analyzer dashboard UI (SPA views)
├── dashboard.css            # Glassmorphism dashboard styles
├── index.html               # Project landing page
├── style.css                # Landing page styles
├── login.html               # Login & Registration authentication UI
├── login.css                # Authentication page styles
├── login.js                 # Authentication logic & API communication
├── script.js                # Dashboard controller, API bridge & history manager
├── run_backend.bat          # One-click Windows runner script
├── test_e2e.py              # Automated End-to-End backend test suite
└── README.md                # Project documentation
```

---

## 🛠️ How to Run the Project

### **Option 1: Using the One-Click Runner (Windows)**
Double-click [run_backend.bat](file:///c:/Users/Mahima/OneDrive/Desktop/AI%20Resume%20analyser/run_backend.bat) located in the project root folder.

---

### **Option 2: Using the Terminal**

1. **Start the Backend Server**:
   ```powershell
   cd "c:\Users\Mahima\OneDrive\Desktop\AI Resume analyser"
   & ".\venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --port 8000
   ```
   > Backend runs on: `http://127.0.0.1:8000` (API Docs: `http://127.0.0.1:8000/docs`)

2. **Open the Frontend**:
   - Double-click or open [login.html](file:///c:/Users/Mahima/OneDrive/Desktop/AI%20Resume%20analyser/login.html) or [index.html](file:///c:/Users/Mahima/OneDrive/Desktop/AI%20Resume%20analyser/index.html) in any web browser.

---

## ⏹️ How to Stop the Project
- Press `Ctrl + C` in the PowerShell / Command Prompt terminal where the backend server is running.
- Close the browser tab.

---

## 🔐 Credentials & Environment Setup

- **Demo Admin Account**:
  - **Email**: `admin@gmail.com`
  - **Password**: `123456`
- **Database**:
  - No external database server or cloud connection string is needed. The project uses zero-config **SQLite3**, which automatically creates and maintains [backend/resume_analyzer.db](file:///c:/Users/Mahima/OneDrive/Desktop/AI%20Resume%20analyser/backend/resume_analyzer.db) locally and securely.
