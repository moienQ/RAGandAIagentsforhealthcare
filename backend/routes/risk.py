from fastapi import APIRouter, HTTPException

from models.schemas import RiskPredictionRequest, RiskPredictionResponse
from services import risk_model_service

router = APIRouter()


@router.post("/predict-risk", response_model=RiskPredictionResponse)
async def predict_risk(payload: RiskPredictionRequest):
    try:
        return RiskPredictionResponse(
            **risk_model_service.predict_risk(payload.model_dump())
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Risk prediction failed: {exc}"
        ) from exc
