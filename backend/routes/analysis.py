from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import json

from services import gemini_service, supabase_service, cnn_service, dicom_service
from services.dicom_service import build_dicom_context_string
from models.schemas import AnalysisResponse
from config import get_settings

router = APIRouter()
settings = get_settings()

# Warm up CNN model on startup (non-blocking — returns None if not available)
cnn_service._load_model()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | {"application/pdf", "application/dicom"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _detect_dicom(filename: str, content_type: str) -> bool:
    """Return True if the upload is a DICOM file."""
    fname = (filename or "").lower()
    return fname.endswith(".dcm") or content_type == "application/dicom"


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(...),
    scan_type: str = Form(...),
    patient_name: Optional[str] = Form(None),
    patient_age: Optional[int] = Form(None),
    patient_gender: Optional[str] = Form(None),
    clinical_history: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
):
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or ""
    is_dicom = _detect_dicom(filename, content_type)

    # Validate file type
    if not is_dicom and content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {content_type}. "
                "Please upload JPG, PNG, WebP, PDF, or DICOM (.dcm)."
            ),
        )

    # Read file
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 20 MB.")

    # Build base patient info
    patient_info = {
        "name": patient_name or "Anonymous",
        "age": patient_age,
        "gender": patient_gender,
        "clinical_history": clinical_history,
    }

    # --- DICOM handling ---
    dicom_context: Optional[str] = None
    image_bytes_for_cnn = file_content      # bytes sent to CNN
    gemini_bytes = file_content             # bytes sent to Gemini
    gemini_media_type = content_type

    if is_dicom:
        try:
            png_bytes, dicom_meta = dicom_service.process_dicom(file_content)
        except RuntimeError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"DICOM processing failed: {e}")

        # Merge DICOM metadata into patient_info (fill any blanks)
        if not patient_info["name"] or patient_info["name"] == "Anonymous":
            patient_info["name"] = dicom_meta.get("patient_name", "Anonymous")
        if not patient_info["age"] and dicom_meta.get("patient_age"):
            # DICOM age is a string like "025Y"
            raw_age = dicom_meta["patient_age"]
            try:
                patient_info["age"] = int("".join(filter(str.isdigit, raw_age)))
            except ValueError:
                pass
        if not patient_info["gender"] and dicom_meta.get("patient_sex"):
            sex_map = {"M": "Male", "F": "Female", "O": "Other"}
            patient_info["gender"] = sex_map.get(dicom_meta["patient_sex"], dicom_meta["patient_sex"])

        # Override scan type if DICOM modality is more specific
        if not scan_type or scan_type == "auto":
            modality_map = {
                "CR": "chest_xray", "DX": "chest_xray",
                "MR": "mri_brain",
                "CT": "ct_scan",
                "ECG": "ecg", "EKG": "ecg",
            }
            dicom_modality = dicom_meta.get("modality", "").upper()
            if dicom_modality in modality_map:
                scan_type = modality_map[dicom_modality]

        dicom_context = build_dicom_context_string(dicom_meta)
        image_bytes_for_cnn = png_bytes
        gemini_bytes = png_bytes
        gemini_media_type = "image/png"

    # --- CNN inference (optional, non-blocking) ---
    cnn_result: Optional[dict] = None
    if gemini_media_type in ALLOWED_IMAGE_TYPES or is_dicom:
        cnn_result = cnn_service.run_inference_from_bytes(
            image_bytes_for_cnn, media_type="image/png"
        )

    # --- Gemini analysis ---
    try:
        result = await gemini_service.analyze_scan(
            file_content=gemini_bytes,
            media_type=gemini_media_type,
            scan_type=scan_type,
            patient_info=patient_info,
            api_key=settings.GOOGLE_API_KEY,
            model=settings.GEMINI_MODEL,
            cnn_hint=cnn_result,
            dicom_context=dicom_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

    # --- Save to Supabase (non-fatal) ---
    analysis_id = None
    if user_id and settings.SUPABASE_URL and settings.SUPABASE_KEY:
        try:
            supabase = supabase_service.get_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            analysis_id = await supabase_service.save_analysis(
                supabase=supabase,
                user_id=user_id,
                scan_type=scan_type,
                patient_info=patient_info,
                result=result,
                filename=filename or "upload",
            )
        except Exception as e:
            print(f"Warning: Failed to save analysis to Supabase: {e}")

    result["patient_info"] = patient_info
    return AnalysisResponse(success=True, analysis_id=analysis_id, result=result)


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, user_id: str):
    if not settings.SUPABASE_URL:
        raise HTTPException(status_code=501, detail="Database not configured")
    supabase = supabase_service.get_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    record = await supabase_service.get_analysis(supabase, analysis_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record
