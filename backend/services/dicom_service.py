"""
DICOM ingestion service for MediVision AI.

Handles .dcm file uploads:
  1. Reads pixel array via pydicom
  2. Applies windowing (if present) for proper contrast
  3. Converts to PNG bytes via PIL
  4. Extracts key DICOM metadata as clinical context

Returns (png_bytes: bytes, dicom_metadata: dict) to the analysis pipeline.
"""

import io
import logging
from typing import Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def is_dicom(filename: str, content_type: str) -> bool:
    """Detect if an uploaded file is a DICOM file."""
    name_lower = (filename or "").lower()
    return (
        name_lower.endswith(".dcm")
        or content_type in ("application/dicom", "application/octet-stream")
        and name_lower.endswith(".dcm")
    )


def _apply_windowing(pixel_array: np.ndarray, ds) -> np.ndarray:
    """
    Apply DICOM window center/width if present, otherwise auto-scale.
    Returns a uint8 array ready for PIL.
    """
    try:
        wc = float(ds.WindowCenter if not isinstance(ds.WindowCenter, list) else ds.WindowCenter[0])
        ww = float(ds.WindowWidth if not isinstance(ds.WindowWidth, list) else ds.WindowWidth[0])
        img_min = wc - ww / 2
        img_max = wc + ww / 2
        clipped = np.clip(pixel_array.astype(np.float32), img_min, img_max)
        scaled = (clipped - img_min) / (img_max - img_min) * 255.0
    except (AttributeError, ZeroDivisionError):
        # No window info — auto min-max scaling
        arr = pixel_array.astype(np.float32)
        arr_min, arr_max = arr.min(), arr.max()
        if arr_max == arr_min:
            scaled = np.zeros_like(arr)
        else:
            scaled = (arr - arr_min) / (arr_max - arr_min) * 255.0

    return scaled.astype(np.uint8)


def _safe_get(ds, tag: str, default: str = "") -> str:
    """Safely extract a DICOM tag value as string."""
    try:
        val = getattr(ds, tag, None)
        if val is None:
            return default
        return str(val).strip()
    except Exception:
        return default


def process_dicom(file_bytes: bytes) -> Tuple[bytes, dict]:
    """
    Process a raw DICOM file.

    Args:
        file_bytes: Raw bytes of the .dcm file

    Returns:
        (png_bytes, metadata_dict)
        - png_bytes: PNG image bytes of the scan
        - metadata_dict: Extracted DICOM metadata for clinical context
    """
    try:
        import pydicom
        from pydicom.uid import UID
    except ImportError:
        raise RuntimeError(
            "pydicom is not installed. Run: pip install pydicom"
        )

    # Parse DICOM
    ds = pydicom.dcmread(io.BytesIO(file_bytes))

    # Extract metadata
    metadata = {
        "patient_name":       _safe_get(ds, "PatientName", "Unknown"),
        "patient_id":         _safe_get(ds, "PatientID"),
        "patient_sex":        _safe_get(ds, "PatientSex"),
        "patient_age":        _safe_get(ds, "PatientAge"),
        "study_date":         _safe_get(ds, "StudyDate"),
        "study_description":  _safe_get(ds, "StudyDescription"),
        "modality":           _safe_get(ds, "Modality"),
        "institution_name":   _safe_get(ds, "InstitutionName"),
        "body_part":          _safe_get(ds, "BodyPartExamined"),
        "series_description": _safe_get(ds, "SeriesDescription"),
        "manufacturer":       _safe_get(ds, "Manufacturer"),
    }

    logger.info(
        f"[DICOM] Loaded: modality={metadata['modality']}, "
        f"patient={metadata['patient_name']}, date={metadata['study_date']}"
    )

    # Get pixel data
    pixel_array = ds.pixel_array

    # Handle multi-frame (take first frame)
    if pixel_array.ndim == 3 and pixel_array.shape[0] > 3:
        pixel_array = pixel_array[0]

    # Apply windowing → uint8
    pixel_u8 = _apply_windowing(pixel_array, ds)

    # Build PIL image
    if pixel_u8.ndim == 2:
        # Grayscale
        pil_img = Image.fromarray(pixel_u8, mode="L").convert("RGB")
    elif pixel_u8.ndim == 3 and pixel_u8.shape[2] == 3:
        pil_img = Image.fromarray(pixel_u8, mode="RGB")
    else:
        # Fallback: convert however PIL can manage
        pil_img = Image.fromarray(pixel_u8).convert("RGB")

    # Encode to PNG bytes
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    logger.info(f"[DICOM] Converted to PNG: {pil_img.size[0]}x{pil_img.size[1]} px")

    return png_bytes, metadata


def build_dicom_context_string(metadata: dict) -> str:
    """
    Build a human-readable clinical context string from DICOM metadata,
    suitable for injection into a Gemini prompt.
    """
    parts = []
    if metadata.get("modality"):
        parts.append(f"Modality: {metadata['modality']}")
    if metadata.get("body_part"):
        parts.append(f"Body Part: {metadata['body_part']}")
    if metadata.get("study_description"):
        parts.append(f"Study: {metadata['study_description']}")
    if metadata.get("series_description"):
        parts.append(f"Series: {metadata['series_description']}")
    if metadata.get("institution_name"):
        parts.append(f"Institution: {metadata['institution_name']}")
    if metadata.get("study_date"):
        parts.append(f"Study Date: {metadata['study_date']}")
    if metadata.get("manufacturer"):
        parts.append(f"Equipment: {metadata['manufacturer']}")
    return " | ".join(parts) if parts else "No DICOM metadata available"
