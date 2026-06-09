# 👔 TechNovance HR Policy Chatbot

An AI-powered Human Resources Policy Assistant built for **TechNovance Solutions Pvt. Ltd.** 
This is a production-grade college team project designed to answer employee policy questions accurately from a local policy document, avoiding AI hallucinations and citing specific policy sections.

---

## 🚀 Key Features
- **Strict Policy Compliance**: The chatbot only answers queries covered in the policy document. If a query is out-of-scope, it redirects users to the HR email (`hr@technovance.com`).
- **Policy Section Citations**: Every policy response automatically cites the exact section (e.g. *"Per Section 2.3 (Sick Leave Policy)..."*).
- **Personal Data Protection**: Questions about individual salaries, leave balances, or appraisal scores are securely redirected to log in to the internal HRMS portal.
- **Scenario-Based Assistance**: Evaluates user situations (e.g. sick family member, weekend work) and recommends the correct policy action (e.g., Casual Leave, Comp-off).
- **Modern Responsive UI**: Built with a sleek, responsive Next.js frontend with Quick Query access buttons for instant policy lookups.

---

## 🛠️ Technology Stack
- **Frontend**: Next.js (TypeScript, React 19, Tailwind CSS, App Router)
- **Backend**: FastAPI (Python 3.11, Uvicorn ASGI server, Pydantic data validation, python-dotenv)
- **AI Core**: Google Gemini 2.0 Flash (configured with strict system instructions)
- **Knowledge Base**: Structured JSON policy database (`backend/data/hr_policies.json`)

---

## 📁 Folder Structure
```text
TEAM 12 PROJECT/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI application routes
│   │   ├── config.py          # App settings and dotenv configuration
│   │   ├── schemas.py         # Request and response schemas
│   │   ├── policies.py        # cached JSON parser using @lru_cache
│   │   └── bot.py             # Gemini Generative AI chatbot connector
│   ├── data/
│   │   └── hr_policies.json   # Structured HR policy database
│   ├── tests/
│   │   ├── test_backend.py    # Automated API unit tests
│   │   ├── run_test_cases.py  # Automation script to evaluate 28 test cases
│   │   └── test_log.md        # Documented test suite results
│   ├── requirements.txt       # Python package requirements
│   └── .env                   # Local settings & Gemini API keys
└── frontend/
    ├── src/
    │   └── app/
    │       ├── layout.tsx     # Page layout with custom SEO metadata
    │       ├── page.tsx       # Modern Tailwind/React Chat interface
    │       └── globals.css    # Global Tailwind styling
    ├── package.json           # Frontend dependencies
    └── tsconfig.json          # TypeScript settings
```

---

## ⚙️ How to Run Locally

### 1. Backend Setup
1. Open a terminal and navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Activate the virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\activate
     ```
   - **Mac/Linux**:
     ```bash
     source venv/bin/activate
     ```
3. Set your Gemini API key in `backend/.env`:
   ```env
   GEMINI_API_KEY=AIzaSy_your_actual_key_here
   ```
4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
   *FastAPI documentation will be running at [http://localhost:8000/docs](http://localhost:8000/docs).*

### 2. Frontend Setup
1. Open a new terminal and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Start the development server:
   ```bash
   npm run dev
   ```
   *The application frontend UI will be running at [http://localhost:3000](http://localhost:3000).*

---

## 📋 Running Automated Tests & QA Log
To run the automated API suite:
```bash
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_backend.py"
```

To run the complete 28-question QA log execution script (which populates the test results in `backend/tests/test_log.md`):
```bash
cd backend
.\venv\Scripts\python.exe tests/run_test_cases.py
```

---

## 👥 Team 12 Project Members
| Member Name | Project Role |
|---|---|
| Nandakishor Kalagarla | Backend & Frontend Architect |
| (Team Member 2) | Knowledge Base Manager |
| (Team Member 3) | Prompt Engineer |
| (Team Member 4) | UI Developer |
| (Team Member 5) | Testing & Deployment |
"# team12" 
