from typing import List, Literal, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientInfo(BaseModel):
    name: Optional[str] = "Anonymous"
    age: Optional[int] = None
    gender: Optional[str] = None
    clinical_history: Optional[str] = None


class Finding(BaseModel):
    description: str
    severity: str  # "CRITICAL", "URGENT", "MONITOR", "NORMAL"
    location: Optional[str] = None


class Differential(BaseModel):
    diagnosis: str
    likelihood: str


class AnalysisResult(BaseModel):
    findings: List[Finding]
    impression: str
    differentials: List[Differential]
    urgency: str  # "CRITICAL", "URGENT", "ROUTINE"
    recommendations: List[str]
    confidence: int
    scan_type: str
    patient_info: PatientInfo
    created_at: Optional[datetime] = None
    id: Optional[str] = None


class AnalysisResponse(BaseModel):
    success: bool
    analysis_id: Optional[str] = None
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None


class RiskPredictionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    smoke: Literal["F", "T"]
    fvc: float = Field(gt=0)
    fec1: float = Field(gt=0)
    pefr: Literal["F", "T"]
    o2: Literal["F", "T"]
    abg_p_o2: Literal["F", "T"]
    abg_p_co2: Literal["F", "T"]
    abg_ph_level: Literal["F", "T"]
    scan: Literal["CT", "MRI", "X-ray"]
    asthma: Literal["F", "T"]
    other_diseases: Literal["F", "T"]
    age: int = Field(ge=0, le=120)


class RiskPredictionResponse(BaseModel):
    selected_model: str
    decision_threshold: float
    risk_probability: float
    predicted_label: Literal["F", "T"]
    screening_positive: bool
    recommended_action: str
    warnings: List[str]
