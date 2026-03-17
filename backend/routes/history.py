from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from services import supabase_service
from config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/history")
async def get_history(
    user_id: str = Query(...),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    scan_type: Optional[str] = Query(default=None)
):
    if not settings.SUPABASE_URL:
        raise HTTPException(status_code=501, detail="Database not configured")
    supabase = supabase_service.get_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return await supabase_service.get_history(supabase, user_id, page, limit, scan_type)


@router.get("/dashboard/stats")
async def get_dashboard_stats(user_id: str = Query(...)):
    if not settings.SUPABASE_URL:
        raise HTTPException(status_code=501, detail="Database not configured")
    supabase = supabase_service.get_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return await supabase_service.get_dashboard_stats(supabase, user_id)
