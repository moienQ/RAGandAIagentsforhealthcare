import anthropic
import base64
import json
import re
from typing import Optional

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
- Enhancement patterns if contrast sequences available

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
- Any masses, collections, or abnormal densities (Hounsfield units if relevant)
- Lung windows / bone windows / soft tissue windows as appropriate

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

Analyze all laboratory values in the report:
- Identify abnormal values (high/low) with clinical significance
- Flag critical values requiring immediate attention
- Correlate values for patterns (e.g., anemia workup, metabolic panel, lipid profile)
- Provide clinical interpretation in context of patient demographics

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
- QRS complex duration and morphology
- ST segment changes (elevation/depression)
- T wave changes
- QT/QTc interval
- Bundle branch blocks, axis deviation
- Any ischemic or arrhythmic patterns

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
}"""
}

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
PDF_TYPE = "application/pdf"


def _build_prompt(scan_type: str, patient_info: dict) -> str:
    age_str = f"{patient_info.get('age')} year old " if patient_info.get("age") else ""
    gender_str = f"{patient_info.get('gender')} " if patient_info.get("gender") else ""
    clinical_history = patient_info.get("clinical_history") or "Not provided"

    template = SCAN_TYPE_PROMPTS.get(scan_type, SCAN_TYPE_PROMPTS["chest_xray"])
    return template.format(
        age_str=age_str,
        gender_str=gender_str,
        clinical_history=clinical_history
    )


def _parse_response(response_text: str) -> dict:
    """Extract JSON from Claude's response robustly."""
    # Try direct parse
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON block
    json_match = re.search(r'\{[\s\S]+\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: return structured error
    return {
        "findings": [{"description": "Unable to parse AI response. Please retry.", "severity": "MONITOR", "location": "N/A"}],
        "impression": response_text[:500],
        "differentials": [],
        "urgency": "ROUTINE",
        "recommendations": ["Please retry the analysis"],
        "confidence": 0
    }


async def analyze_scan(
    file_content: bytes,
    media_type: str,
    scan_type: str,
    patient_info: dict,
    api_key: str
) -> dict:
    """Call Claude API to analyze a medical scan."""
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(scan_type, patient_info)

    # Build content array
    if media_type in IMAGE_TYPES:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(file_content).decode("utf-8")
                }
            },
            {"type": "text", "text": prompt}
        ]
    else:
        # For PDFs and other docs, encode as base64 document
        content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.b64encode(file_content).decode("utf-8")
                }
            },
            {"type": "text", "text": prompt}
        ]

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}]
    )

    result = _parse_response(response.content[0].text)
    result["scan_type"] = scan_type
    return result
