# SmartStudy Backend

Production-ready FastAPI backend for the SmartStudy AI exam preparation platform.

## Tech Stack

- **FastAPI** — REST API with OpenAPI/Swagger docs
- **MongoDB Atlas** — Motor async driver
- **Cloudinary** — PDF and file storage
- **OpenAI / Gemini** — AI analysis, notes, and quiz generation
- **JWT** — Authentication

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # Application entry point
│   ├── core/                   # Config, security, middleware, exceptions
│   ├── api/
│   │   ├── deps.py             # Dependency injection
│   │   └── v1/                 # API route modules
│   │       ├── auth.py
│   │       ├── documents.py
│   │       ├── analysis.py
│   │       ├── notes.py
│   │       ├── quiz.py
│   │       └── profile.py
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Business logic layer
│   │   └── ai/                 # OpenAI & Gemini integration
│   ├── repositories/           # MongoDB data access
│   ├── models/                 # Domain enums
│   ├── db/                     # MongoDB connection & indexes
│   └── utils/                  # Text extraction, email
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # Configure your credentials
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, open:

- **Swagger UI:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc
- **Health:** http://localhost:8000/health

## Environment Variables

See `.env.example` for all required variables.

## API Modules

| Module | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/v1/auth` | Register, login, JWT refresh, password reset |
| Documents | `/api/v1/documents` | PDF upload, list, update, delete |
| PYQ Analysis | `/api/v1/analysis/pyq` | AI-powered question paper analysis |
| Notes | `/api/v1/notes` | Generate and simplify notes |
| Quiz | `/api/v1/quiz` | Generate quizzes, submit answers, scoring |
| Profile | `/api/v1/profile` | User profile management |
| Dashboard | `/api/v1/dashboard` | Stats and recent activity |
