# InkGrade AI – Answer Sheet Evaluation

Teachers upload scanned or handwritten answer sheets. The system reads them with OCR, compares each answer with the teacher's model answer and key concepts, suggests marks with feedback, and lets the teacher review, finalize and export a PDF report. Students see only their finalized results.

## Architecture

| Part | Tech | Port |
|---|---|---|
| `frontend/` | React + Vite | 5173 (dev) / 3000 (Docker) |
| `backend/` | FastAPI, SQLAlchemy, JWT security | 8080 |
| `ai-service/` | FastAPI, Tesseract OCR, embeddings | 8001 |
| Database | PostgreSQL 16 | 5432 |

## Prerequisites

**Option A (Docker):** Docker with Compose.

**Option B (run locally):**
- Node.js 20+ and npm
- Python 3.9 to 3.11
- Tesseract OCR (`brew install tesseract` on macOS, `sudo apt install tesseract-ocr` on Ubuntu)
- PostgreSQL 16, or Docker just for the database

## Option A: Run everything with Docker

```bash
git clone <your-repo-url>
cd Answer_evaluation
cp .env.example .env        # edit the secrets if you like
docker compose up --build
```

Open http://localhost:3000.

> If the build fails with `CERTIFICATE_VERIFY_FAILED`, your network (company proxy or VPN) is intercepting HTTPS. Use Option B instead.

## Option B: Run locally

Use one terminal per step.

### 1. Database
```bash
docker compose up -d postgres
```
This creates database `inkgrade` with user `inkgrade`. The compose file publishes port 5432, so the local backend can reach it. The password comes from `.env` (`POSTGRES_PASSWORD`), or defaults to `inkgrade` if you have no `.env`.

Without Docker, install PostgreSQL and run:
```sql
CREATE USER inkgrade WITH PASSWORD 'inkgrade';
CREATE DATABASE inkgrade OWNER inkgrade;
```

### 2. AI service
```bash
cd ai-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
AI_API_KEY=dev-ai-key uvicorn app.main:app --port 8001
```
Check it with `curl localhost:8001/health`.

Optional, for better matching and OCR (about 2 GB): `pip install -r requirements-ml.txt`. Without it, a simple built-in embedder is used.

### 3. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DB_PASSWORD=inkgrade \
AI_API_KEY=dev-ai-key \
SEED_DEMO=true \
uvicorn app.main:app --port 8080
```
- Set `DB_PASSWORD` to match your database password. If you used `.env` with Docker for the database, use the `POSTGRES_PASSWORD` value from it.
- Set `AI_API_KEY` to the same value you used for the AI service.
- Wait for `Application startup complete`. Check it with `curl localhost:8080/actuator/health`.

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The Vite dev server proxies `/api` to the backend on port 8080.

## Default logins

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Teacher | `teacher1` | `Teacher@123` |
| Student | `student1`, `student2` | `Student@123` |

Teacher and student demo accounts exist only when `SEED_DEMO=true`. **Change all passwords and secrets before any real deployment.**

## How to use

1. **Teacher:** create a **Subject**, then an **Exam**, then add **Questions** (text and max marks).
2. For each question, open **Blueprint**. Add the model answer (typed or uploaded) and key concepts with synonyms and weights, then save.
3. Under **Student answer sheets**, pick a student, upload the sheet (PNG, JPG, PDF, TIFF, BMP or TXT), and click **Evaluate**.
4. Open the result under **Evaluations**. Review the OCR text, concept coverage, spelling and grammar mistakes, and AI feedback. Adjust marks, **Finalize**, and download the **PDF report**.
5. **Student:** sees finalized results and performance charts only.
6. **Admin:** manages users and role permissions, and views the audit log.

## Configuration

Backend environment variables (all have development defaults):

| Variable | Default |
|---|---|
| `DB_URL` / `DB_USER` / `DB_PASSWORD` | `postgresql://localhost:5432/inkgrade` / `inkgrade` / `inkgrade` |
| `JWT_SECRET` | dev value, at least 32 characters |
| `AI_SERVICE_URL` / `AI_API_KEY` | `http://localhost:8001` / empty (check disabled) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `Admin@123` |
| `SEED_DEMO` | `false` |
| `STORAGE_ROOT` | `./uploads` |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` |

AI service: `EMBEDDING_BACKEND` (`auto`, `sbert` or `hash`), `OCR_ENGINE` (`tesseract` or `trocr`), `AI_API_KEY`.

## Tests

```bash
cd ai-service && source .venv/bin/activate && pytest
cd frontend && npm test
cd backend && source .venv/bin/activate && pytest
```

## Troubleshooting

- **"address already in use":** the service is already running. Stop it with `lsof -ti :8001 :8080 :5173 | xargs kill`.
- **Backend can't connect to the database:** make sure Postgres is up (`docker ps`) and `DB_PASSWORD` matches.
- **OCR returns nothing:** make sure `tesseract` is installed (`tesseract --version`).
- **Upload button is disabled:** pick a student and a file first. The text box beside the student dropdown only filters the list.
