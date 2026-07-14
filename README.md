# FraudShield — Credit Card Fraud Detection

> DEPI Microsoft ML Course | Graduation Project 2025  
> Full-stack fraud detection: FastAPI + Next.js 14 + PostgreSQL + Redis + Scikit-learn

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, Tailwind CSS, TanStack Query, Recharts |
| Backend | FastAPI 0.110, Uvicorn, Celery, SQLAlchemy 2, Alembic |
| ML | scikit-learn 1.4, imbalanced-learn (SMOTE), joblib |
| Database | PostgreSQL 16, Redis 7 |
| Infra | Docker Compose, Nginx, GitHub Actions |

---

## Quick Start

### Prerequisites
- Docker Desktop ≥ 25.0
- Git

### 1. Clone & configure
```bash
git clone https://github.com/your-org/fraud-detection.git
cd fraud-detection
cp .env.example .env        # edit passwords / secrets if needed
```

### 2. Start all services
```bash
docker compose up --build
```

Services started:
- **Frontend** → http://localhost:3000
- **Backend API** → http://localhost:8000
- **API Docs** → http://localhost:8000/docs
- **Nginx proxy** → http://localhost:80

### 3. Train the ML model (first time)
```bash
# Download dataset from Kaggle first:
# https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
# Place creditcard.csv in ml/data/

docker compose exec backend python -m app.ml.pipeline.train
```

The pipeline will:
1. Load & preprocess data
2. Apply SMOTE (training set only)
3. Train Isolation Forest + Logistic Regression
4. Save artifacts to `backend/app/ml/artifacts/`
5. Auto-register model v1.0.0 on next backend restart

### 4. Create your first user
```bash
# Via the UI
open http://localhost:3000/auth/register

# Or via the API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"Admin1234!","full_name":"Admin User","role":"admin"}'
```

---

## Project Structure

```
fraud-detection/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # auth, predict, alerts, analytics
│   │   ├── core/               # config, security, celery
│   │   ├── db/                 # session, Base
│   │   ├── ml/
│   │   │   ├── artifacts/      # .pkl model files (gitignored)
│   │   │   ├── pipeline/       # train.py
│   │   │   └── model_registry.py
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # auth, prediction, tasks (Celery)
│   ├── alembic/                # DB migrations
│   ├── tests/                  # pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── auth/               # login, register
│   │   ├── dashboard/          # KPI + charts
│   │   ├── predict/            # single transaction form
│   │   ├── upload/             # batch CSV upload
│   │   ├── alerts/             # fraud alert management
│   │   └── models/             # model version management
│   ├── components/
│   │   └── shared/             # Sidebar
│   ├── lib/api.ts              # Axios + JWT interceptors
│   ├── types/index.ts          # TypeScript types
│   └── Dockerfile
├── ml/
│   └── data/                   # place creditcard.csv here
├── nginx/nginx.conf
├── scripts/init.sql
├── docker-compose.yml
└── .env
```

---

## Running Tests

```bash
# Backend tests (inside container)
docker compose exec backend pytest -v

# Or locally (requires Python 3.11 + test DB)
cd backend
pip install -r requirements.txt
pytest --cov=app --cov-report=term-missing
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/predict/single` | Predict single transaction |
| POST | `/api/v1/predict/batch` | Upload CSV for batch prediction |
| GET | `/api/v1/predict/batch/{job_id}` | Poll batch job status |
| GET | `/api/v1/alerts` | List fraud alerts |
| PUT | `/api/v1/alerts/{id}` | Update alert status |
| GET | `/api/v1/models` | List model versions |
| POST | `/api/v1/models/{id}/activate` | Activate a model version |
| GET | `/api/v1/analytics/dashboard` | Dashboard KPIs |
| GET | `/api/v1/health` | Health check |

Full interactive docs at: `http://localhost:8000/docs`

---

## ML Pipeline

```
creditcard.csv → EDA → Stratified Split (80/20)
                              ↓
              Train set → StandardScaler → SMOTE
                              ↓
              Isolation Forest + Logistic Regression (GridSearchCV)
                              ↓
              Evaluate on UNTOUCHED test set
                              ↓
              Save .pkl artifacts → Load via ModelRegistry
```

Target metrics:
- Precision ≥ 0.86
- Recall ≥ 0.92  
- AUC-ROC ≥ 0.97

---

## Team

| Name | Role |
|---|---|
| Ahmed Mahmoud Abdelgawad | Team Leader |
| Osama Nasser Mohamed | Data Engineer |
| Roaa Sameh Mohamed | ML Engineer |
| Ziad Mohamed Sayed Abdelsalam | Model Evaluator |
| Antonious Nashaat Hosny Rashed | Documentation Lead |
