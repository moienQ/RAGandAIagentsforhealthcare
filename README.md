# RAG and AI Agents for Healthcare (MediVision AI) 🔬

> AI-powered medical imaging analysis for doctors. Upload X-rays, MRI, CT scans, or lab reports and get structured AI diagnostic insights in under 30 seconds. Built with Generative AI and advanced CNN inference.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + React Router v6 |
| Styling | Vanilla CSS (dark theme, glassmorphism) |
| Backend | Python FastAPI |
| AI Brain | Google Gemini |
| Database | Supabase (PostgreSQL + Auth) |
| PDF Export | jsPDF |

---

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- Google AI API key
- Supabase project → [supabase.com](https://supabase.com) *(optional for demo mode)*

---

### 1. Database Setup (Supabase)

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and run the contents of `backend/db_schema.sql`
3. Note your **Project URL** and **anon key** from Settings → API

---

### 2. Backend Setup

```bash
cd "medi Vision/backend"

# Create virtual environment
python -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your keys:
#   GOOGLE_API_KEY=...
#   GEMINI_MODEL=gemini-2.5-flash
#   SUPABASE_URL=https://xxx.supabase.co
#   SUPABASE_KEY=your-anon-key

# Start the backend
uvicorn main:app --reload --port 8000
```

Backend runs at: **http://localhost:8000**  
API docs: **http://localhost:8000/docs**

---

### 3. Frontend Setup

```bash
cd "medi Vision/frontend"

# Install dependencies (already done if you used Vite setup)
npm install

# Configure environment
cp .env.example .env
# Edit .env:
#   VITE_API_URL=http://localhost:8000
#   VITE_SUPABASE_URL=https://xxx.supabase.co
#   VITE_SUPABASE_ANON_KEY=your-anon-key

# Start development server
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## Demo Mode

No Supabase required! Click **"Try Demo Mode"** on the login screen — you can upload scans and see AI analysis without creating an account. History won't be saved.

You still need a **GOOGLE_API_KEY** in the backend `.env`.

---

## Tabular Baseline Training

The backend also includes a separate training script for the Kaggle dataset `klu2000030172/lung-disease-dataset`.

This is a **tabular risk classifier** for the spreadsheet label `Risk`. It is **not** a chest X-ray or MRI image training pipeline.

```bash
cd "medi Vision/backend"

pip install -r requirements-ml.txt
python scripts/train_risk_model.py
```

Artifacts are written to `backend/artifacts/risk_model/`.

---

## Internal Risk Endpoint

After training the tabular baseline, the backend exposes an internal screening endpoint:

```bash
POST /api/predict-risk
```

This endpoint uses the saved `backend/artifacts/risk_model/model.joblib` artifact and is intended for internal experimentation only. It is not a diagnostic medical API.

---

## Screens

| Screen | Route | Description |
|---|---|---|
| Login | `/login` | Email/password auth or demo mode |
| Register | `/register` | Doctor account creation |
| Dashboard | `/dashboard` | Stats, recent analyses, scan type launcher |
| Upload & Analyze | `/upload` | Drag & drop + AI analysis with live animation |
| Report | `/report/:id` | Color-coded findings, differentials, PDF export |
| History | `/history` | Filterable, searchable past analyses |

---

## Supported Scan Types

| Type | Key |
|---|---|
| 🫁 Chest X-Ray | `chest_xray` |
| 🧠 Brain MRI | `mri_brain` |
| 🩻 CT Scan | `ct_scan` |
| 🧪 Lab Report | `lab_report` |
| ❤️ ECG | `ecg` |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Upload file and get AI analysis |
| `GET` | `/api/analyses/{id}` | Fetch a specific analysis |
| `GET` | `/api/history?user_id=...` | Get paginated history |
| `GET` | `/api/dashboard/stats?user_id=...` | Dashboard statistics |

---

## Budget Estimate (MVP)

| Item | Cost |
|---|---|
| Gemini API (~500 analyses @ ₹8–12 each) | ~₹5,000 |
| Domain name | ~₹1,000 |
| Hosting (Railway/Render free tier) | ₹0 |
| Supabase (free tier up to 500MB) | ₹0 |
| **Total** | **~₹6,000** |

---

## ⚠️ Medical Disclaimer

This application provides AI-generated analysis for informational purposes only. It does **not** constitute medical advice and should always be reviewed by a qualified healthcare professional. Do not make clinical decisions based solely on AI output.

---

## Next Steps (Post-MVP)

- [ ] Razorpay payment integration (₹999/month plan)
- [ ] Image viewer with annotation overlay
- [ ] Hospital/clinic multi-user accounts
- [ ] Report sharing via secure link
- [ ] Mobile app (React Native)
- [ ] Integration with PACS/HIS systems
