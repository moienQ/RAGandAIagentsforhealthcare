from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd


ARTIFACT_PATH = (
    Path(__file__).resolve().parent.parent / "artifacts" / "risk_model" / "model.joblib"
)


@lru_cache()
def load_artifact() -> dict:
    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(
            f"Risk model artifact not found at {ARTIFACT_PATH}. Run scripts/train_risk_model.py first."
        )
    return joblib.load(ARTIFACT_PATH)


def predict_risk(payload: dict) -> dict:
    artifact = load_artifact()
    feature_columns: list[str] = artifact["feature_columns"]
    feature_config: dict = artifact.get("feature_config", {})
    clip_bounds: dict = feature_config.get("clip_bounds", {})

    features = pd.DataFrame(
        [
            {
                "smoke": payload["smoke"],
                "FVC": payload["fvc"],
                "FEC1": payload["fec1"],
                "PEFR": payload["pefr"],
                "O2": payload["o2"],
                "ABG-P-O2": payload["abg_p_o2"],
                "ABG-P-CO2": payload["abg_p_co2"],
                "ABG-pH Level": payload["abg_ph_level"],
                "Scan": payload["scan"],
                "Asthama": payload["asthma"],
                "Other diseaes": payload["other_diseases"],
                "AGE": payload["age"],
            }
        ]
    )

    features["FEC1_to_FVC"] = features["FEC1"] / features["FVC"].replace(0, pd.NA)
    features["FEC1_to_FVC"] = features["FEC1_to_FVC"].replace([float("inf"), float("-inf")], pd.NA)

    for column, bounds in clip_bounds.items():
        features[column] = features[column].clip(bounds["lower"], bounds["upper"])

    features = features[feature_columns]

    pipeline = artifact["pipeline"]
    threshold = float(artifact["decision_threshold"])
    probability = float(pipeline.predict_proba(features)[0, 1])
    screening_positive = probability >= threshold

    return {
        "selected_model": artifact["selected_model"],
        "decision_threshold": threshold,
        "risk_probability": probability,
        "predicted_label": "T" if screening_positive else "F",
        "screening_positive": screening_positive,
        "recommended_action": (
            "Escalate for clinician review and confirm with a higher-quality diagnostic workflow."
            if screening_positive
            else "Do not rule out disease solely from this result; use clinician review if symptoms or history warrant it."
        ),
        "warnings": [
            "Internal-only experimental screening model.",
            "Trained on a small tabular Kaggle dataset, not on medical images.",
            "Not for standalone diagnosis or treatment decisions.",
        ],
    }
