from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from routes import analysis, history, risk


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.GOOGLE_API_KEY:
        print("⚠️  WARNING: GOOGLE_API_KEY not set. AI analysis will fail.")
    if not settings.SUPABASE_URL:
        print("⚠️  WARNING: SUPABASE_URL not set. History/persistence disabled.")
    yield


app = FastAPI(
    title="MediVision AI",
    description="AI-powered medical imaging analysis API",
    version="1.0.0",
    lifespan=lifespan
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(risk.router, prefix="/api", tags=["Risk"])


@app.get("/")
async def root():
    return {"status": "ok", "service": "MediVision AI", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
