import json
import re

from google import genai
from google.genai import errors, types

# ---------------------------------------------------------------------------
# Prompt templates — all supported scan types
# ---------------------------------------------------------------------------

SCAN_TYPE_PROMPTS = {
    "chest_xray": """You are a board-certified radiologist with 20 years of experience specializing in chest radiology.

Scan Type: PA Chest X-ray
Patient: {age_str}{gender_str}
Clinical History: {clinical_history}

Analyze the chest X-ray systematically, evaluating:
- Lung fields (left and right separately) — consolidation, opacities, nodules, hyperinflation
- Cardiac silhouette — size, shape, borders
- Mediastinum — width, contours, tracheal deviation
- Pleural spaces — effusion, pneumothorax
- Bony structures — ribs, clavicles, scapulae, vertebrae
- Diaphragm — elevation, flattening, costophrenic angles
- Soft tissues and airways

Return ONLY valid JSON (no markdown, no extra text) in this exact structure:
{
  "findings": [
    {"description": "...", "severity": "CRITICAL|URGENT|MONITOR|NORMAL", "location": "..."}
  ],
  "impression": "One paragraph overall diagnostic summary",
  "differentials": [
    {"diagnosis": "...", "likelihood": "XX%"}
  ],
  "urgency": "CRITICAL|URGENT|ROUTINE",
  "recommendations": ["...", "..."],
  "confidence": 85
}""",

    "mri_brain": """You are a board-certified neuroradiologist with 20 years of experience.

Scan Type: Brain MRI
Patient: {age_str}{gender_str}
Clinical History: {clinical_history}

Analyze the brain MRI systematically:
- Cerebral cortex and subcortical white matter — signal abnormalities, atrophy
- Basal ganglia and thalami
- Brainstem and cerebellum
- Ventricles — size, shape, hydrocephalus
- Extra-axial spaces — subdural/epidural collections
- Vascular structures — flow voids, thrombosis
- Posterior fossa

Return ONLY valid JSON:
{
  "findings": [
    {"description": "...", "severity": "CRITICAL|URGENT|MONITOR|NORMAL", "location": "..."}
  ],
  "impression": "Comprehensive neuroradiological summary",
  "differentials": [
    {"diagnosis": "...", "likelihood": "XX%"}
  ],
  "urgency": "CRITICAL|URGENT|ROUTINE",
  "recommendations": ["...", "..."],
  "confidence": 85
}""",

    "ct_scan": """You are a board-certified radiologist with 20 years of experience in CT interpretation.

Scan Type: CT Scan
Patient: {age_str}{gender_str}
Clinical History: {clinical_history}

Analyze systematically based on visible anatomy:
- Parenchymal organs (liver, spleen, kidneys, pancreas if abdominal)
- Vascular structures
- Lymph nodes
- Bones and soft tissues
- Any masses, collections, or abnormal densities

Return ONLY valid JSON:
{
  "findings": [
    {"description": "...", "severity": "CRITICAL|URGENT|MONITOR|NORMAL", "location": "..."}
  ],
  "impression": "Comprehensive CT interpretation",
  "differentials": [
    {"diagnosis": "...", "likelihood": "XX%"}
  ],
  "urgency": "CRITICAL|URGENT|ROUTINE",
  "recommendations": ["...", "..."],
  "confidence": 85
}""",

    "lab_report": """You are a board-certified clinical pathologist and internal medicine specialist with 20 years of experience.

Document Type: Laboratory Report
Patient: {age_str}{gender_str}
Clinical History: {clinical_history}

Analyze all laboratory values:
- Identify abnormal values with clinical significance
- Flag critical values requiring immediate attention
- Correlate values for patterns

Return ONLY valid JSON:
{
  "findings": [
    {"description": "...", "severity": "CRITICAL|URGENT|MONITOR|NORMAL", "location": "..."}
  ],
  "impression": "Clinical interpretation of laboratory findings",
  "differentials": [
    {"diagnosis": "...", "likelihood": "XX%"}
  ],
  "urgency": "CRITICAL|URGENT|ROUTINE",
  "recommendations": ["...", "..."],
  "confidence": 90
}""",

    "ecg": """You are a board-certified cardiologist with 20 years of ECG interpretation experience.

Document Type: ECG / EKG
Patient: {age_str}{gender_str}
Clinical History: {clinical_history}

Analyze the ECG systematically:
- Rate and rhythm
- P waves, PR interval
- QRS complex and ST segment changes
- T wave changes, QT/QTc interval
- Bundle branch blocks, axis deviation

Return ONLY valid JSON:
{
  "findings": [
    {"description": "...", "severity": "CRITICAL|URGENT|MONITOR|NORMAL", "location": "..."}
  ],
  "impression": "Complete ECG interpretation",
  "differentials": [
    {"diagnosis": "...", "likelihood": "XX%"}
  ],
  "urgency": "CRITICAL|URGENT|ROUTINE",
  "recommendations": ["...", "..."],
  "confidence": 88
}""",
}

# Map aliases / common frontend values to canonical prompt keys
SCAN_TYPE_ALIASES = {
    "lung":        "chest_xray",
    "xray":        "chest_xray",
    "x-ray":       "chest_xray",
    "chest":       "chest_xray",
    "brain":       "mri_brain",
    "mri":         "mri_brain",
    "ct":          "ct_scan",
    "abdomen":     "ct_scan",
    "abdominal":   "ct_scan",
    "lab":         "lab_report",
    "labs":        "lab_report",
    "blood":       "lab_report",
    "ekg":         "ecg",
    "cardiac":     "ecg",
}

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

DEFAULT_MODEL_CANDIDATES = (
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_scan_type(scan_type: str) -> str:
    """Normalise raw scan_type string to a known prompt key."""
    key = scan_type.lower().strip()
    return SCAN_TYPE_ALIASES.get(key, key if key in SCAN_TYPE_PROMPTS else "chest_xray")


def _normalise_model_name(model: str) -> str:
    return model.split("/", 1)[1] if model.startswith("models/") else model


def _candidate_models(preferred_model: str) -> list[str]:
    candidates = [_normalise_model_name(preferred_model)] if preferred_model else []
    for model in DEFAULT_MODEL_CANDIDATES:
        if model not in candidates:
            candidates.append(model)
    return candidates


def _resolve_fallback_model(client: genai.Client, preferred_model: str) -> str:
    """Pick the first currently supported generateContent model from our fallback list."""
    available = set()
    for model in client.models.list():
        methods = getattr(model, "supported_actions", None) or getattr(
            model, "supported_generation_methods", None
        ) or []
        if "generateContent" in methods:
            available.add(_normalise_model_name(model.name))

    for candidate in _candidate_models(preferred_model):
        if candidate in available:
            return candidate

    return _normalise_model_name(preferred_model)


def _build_prompt(
    scan_type: str,
    patient_info: dict,
    cnn_hint: dict | None = None,
    dicom_context: str | None = None,
) -> str:
    age_str = f"{patient_info.get('age')} year old " if patient_info.get("age") else ""
    gender_str = f"{patient_info.get('gender')} " if patient_info.get("gender") else ""
    clinical_history = patient_info.get("clinical_history") or "Not provided"

    canonical = _resolve_scan_type(scan_type)
    template = SCAN_TYPE_PROMPTS[canonical]
    prompt = (
        template.replace("{age_str}", age_str)
        .replace("{gender_str}", gender_str)
        .replace("{clinical_history}", clinical_history)
    )

    # Inject DICOM equipment/study metadata when available
    if dicom_context:
        prompt = f"DICOM Metadata: {dicom_context}\n\n" + prompt

    # Inject CNN classification hint — helps Gemini focus its analysis
    if cnn_hint and cnn_hint.get("predicted_class"):
        cls = cnn_hint["predicted_class"].replace("_", " ").title()
        conf = round(cnn_hint.get("confidence", 0) * 100, 1)
        hint_text = (
            f"\n\n[AI Pre-Screening Hint]: A convolutional neural network classifier "
            f"predicted '{cls}' with {conf}% confidence. "
            f"Use this as supplementary context — do NOT anchor solely on it. "
            f"Your independent image analysis takes priority."
        )
        prompt = prompt + hint_text

    return prompt


def _parse_response(response_text: str) -> dict:
    """Extract JSON from Gemini's response robustly."""
    print(f"[gemini] raw response (first 300 chars): {response_text[:300]!r}")

    # Strip markdown fences: ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?\s*", "", response_text)
    cleaned = re.sub(r"```", "", cleaned).strip()

    # Direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the outermost JSON object
    json_match = re.search(r'\{[\s\S]+\}', cleaned)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    print(f"[gemini] WARNING: could not parse JSON — returning fallback. Raw: {response_text[:500]!r}")
    return {
        "findings": [{
            "description": "Unable to parse AI response. Please retry.",
            "severity": "MONITOR",
            "location": "N/A"
        }],
        "impression": response_text[:500],
        "differentials": [],
        "urgency": "ROUTINE",
        "recommendations": ["Please retry the analysis"],
        "confidence": 0
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def analyze_scan(
    file_content: bytes,
    media_type: str,
    scan_type: str,
    patient_info: dict,
    api_key: str,
    model: str,
    cnn_hint: dict | None = None,
    dicom_context: str | None = None,
) -> dict:
    """Call Google Gemini API to analyze a medical scan."""
    client = genai.Client(api_key=api_key)
    prompt = _build_prompt(scan_type, patient_info, cnn_hint=cnn_hint, dicom_context=dicom_context)
    selected_model = _normalise_model_name(model)

    # Always pass file as typed bytes Part — works for both images and PDFs
    file_part = types.Part.from_bytes(
        data=file_content,
        mime_type=media_type if media_type in IMAGE_TYPES else "application/pdf"
    )

    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=[prompt, file_part],
            config=types.GenerateContentConfig(
                max_output_tokens=2048,
                temperature=0.1,
            )
        )
    except errors.ClientError as exc:
        if exc.status != 404:
            raise

        fallback_model = _resolve_fallback_model(client, selected_model)
        if fallback_model == selected_model:
            raise

        print(
            f"[gemini] model {selected_model!r} unavailable; retrying with {fallback_model!r}"
        )
        selected_model = fallback_model
        response = client.models.generate_content(
            model=selected_model,
            contents=[prompt, file_part],
            config=types.GenerateContentConfig(
                max_output_tokens=2048,
                temperature=0.1,
            )
        )

    print(f"[gemini] finish_reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}")

    result = _parse_response(response.text)
    result["scan_type"] = _resolve_scan_type(scan_type)
    # Attach CNN prediction to result if available
    if cnn_hint:
        result["cnn_prediction"] = cnn_hint
    return result
