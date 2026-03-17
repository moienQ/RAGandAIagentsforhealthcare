from supabase import create_client, Client
from typing import Optional
import uuid
from datetime import datetime


def get_client(url: str, key: str) -> Client:
    return create_client(url, key)


async def save_analysis(
    supabase: Client,
    user_id: str,
    scan_type: str,
    patient_info: dict,
    result: dict,
    filename: str
) -> str:
    """Save an analysis result to Supabase and return the analysis ID."""
    analysis_id = str(uuid.uuid4())
    data = {
        "id": analysis_id,
        "user_id": user_id,
        "scan_type": scan_type,
        "filename": filename,
        "patient_name": patient_info.get("name", "Anonymous"),
        "patient_age": patient_info.get("age"),
        "patient_gender": patient_info.get("gender"),
        "clinical_history": patient_info.get("clinical_history"),
        "findings": result.get("findings", []),
        "impression": result.get("impression", ""),
        "differentials": result.get("differentials", []),
        "urgency": result.get("urgency", "ROUTINE"),
        "recommendations": result.get("recommendations", []),
        "confidence": result.get("confidence", 0),
        "created_at": datetime.utcnow().isoformat()
    }

    response = supabase.table("analyses").insert(data).execute()
    return analysis_id


async def get_analysis(supabase: Client, analysis_id: str, user_id: str) -> Optional[dict]:
    """Fetch a single analysis record."""
    response = (
        supabase.table("analyses")
        .select("*")
        .eq("id", analysis_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return response.data


async def get_history(
    supabase: Client,
    user_id: str,
    page: int = 1,
    limit: int = 20,
    scan_type: Optional[str] = None
) -> dict:
    """Fetch paginated history of analyses for a user."""
    query = (
        supabase.table("analyses")
        .select("id, scan_type, patient_name, patient_age, patient_gender, urgency, confidence, created_at", count="exact")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range((page - 1) * limit, page * limit - 1)
    )

    if scan_type:
        query = query.eq("scan_type", scan_type)

    response = query.execute()
    return {
        "data": response.data,
        "total": response.count,
        "page": page,
        "limit": limit
    }


async def get_dashboard_stats(supabase: Client, user_id: str) -> dict:
    """Get summary stats for dashboard."""
    from datetime import datetime, timedelta
    month_start = datetime.utcnow().replace(day=1).isoformat()

    total_resp = supabase.table("analyses").select("id", count="exact").eq("user_id", user_id).execute()
    month_resp = (
        supabase.table("analyses")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", month_start)
        .execute()
    )
    critical_resp = (
        supabase.table("analyses")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("urgency", "CRITICAL")
        .execute()
    )

    return {
        "total": total_resp.count or 0,
        "this_month": month_resp.count or 0,
        "critical": critical_resp.count or 0,
    }
