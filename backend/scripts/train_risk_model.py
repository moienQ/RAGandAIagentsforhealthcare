import argparse
import json
from pathlib import Path

import joblib
import kagglehub
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATASET_HANDLE = "klu2000030172/lung-disease-dataset"
DATASET_FILENAME = "lung_disease.xlsx"
DROP_COLUMNS = ["Patient"]
TARGET_COLUMN = "Risk"
RANDOM_STATE = 42
THRESHOLD_GRID = np.arange(0.1, 0.91, 0.05)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a tabular baseline model for the Kaggle lung disease risk dataset."
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/risk_model",
        help="Directory where the trained model and metrics will be written.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of rows reserved for the final test split.",
    )
    parser.add_argument(
        "--target-recall",
        type=float,
        default=0.75,
        help="Minimum recall target for screening threshold calibration.",
    )
    parser.add_argument(
        "--min-precision",
        type=float,
        default=0.15,
        help="Minimum precision floor when selecting a screening threshold.",
    )
    return parser.parse_args()


def load_dataset() -> pd.DataFrame:
    dataset_dir = Path(kagglehub.dataset_download(DATASET_HANDLE))
    dataset_path = dataset_dir / DATASET_FILENAME
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    return pd.read_excel(dataset_path)


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict[str, object]]:
    features = df.drop(columns=DROP_COLUMNS + [TARGET_COLUMN]).copy()
    features["FEC1_to_FVC"] = features["FEC1"] / features["FVC"].replace(0, pd.NA)
    features["FEC1_to_FVC"] = features["FEC1_to_FVC"].replace([np.inf, -np.inf], pd.NA)
    clip_bounds: dict[str, dict[str, float]] = {}
    for column in ["FVC", "FEC1", "AGE", "FEC1_to_FVC"]:
        lower, upper = features[column].quantile([0.01, 0.99])
        features[column] = features[column].clip(lower, upper)
        clip_bounds[column] = {"lower": float(lower), "upper": float(upper)}

    target = df[TARGET_COLUMN].map({"F": 0, "T": 1})
    if target.isna().any():
        raise ValueError("Target column contains unexpected values outside {'F', 'T'}.")
    feature_config = {
        "ratio_feature": "FEC1_to_FVC",
        "clip_bounds": clip_bounds,
    }
    return features, target.astype(int), feature_config


def build_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    numeric_columns = features.select_dtypes(include=["number"]).columns.tolist()
    categorical_columns = [col for col in features.columns if col not in numeric_columns]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ]
    )


def build_candidates(preprocessor: ColumnTransformer) -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        solver="liblinear",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=400,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "extra_trees": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    ExtraTreesClassifier(
                        n_estimators=400,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


def _threshold_metrics(
    y_true: pd.Series, probabilities: np.ndarray, threshold: float
) -> dict[str, float | list[list[int]]]:
    predictions = (probabilities >= threshold).astype(int)
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, predictions).tolist(),
    }


def _pick_screening_threshold(
    threshold_metrics: list[dict[str, float | list[list[int]]]],
    target_recall: float,
    min_precision: float,
) -> dict[str, float | list[list[int]]]:
    precision_eligible = [
        metric
        for metric in threshold_metrics
        if metric["recall"] >= target_recall and metric["precision"] >= min_precision
    ]
    if precision_eligible:
        return max(
            precision_eligible,
            key=lambda metric: (
                metric["balanced_accuracy"],
                metric["precision"],
                metric["f1"],
            ),
        )

    recall_eligible = [
        metric for metric in threshold_metrics if metric["recall"] >= target_recall
    ]
    if recall_eligible:
        return max(
            recall_eligible,
            key=lambda metric: (
                metric["balanced_accuracy"],
                metric["precision"],
                metric["f1"],
            ),
        )

    return max(
        threshold_metrics,
        key=lambda metric: (
            metric["recall"],
            metric["balanced_accuracy"],
            metric["precision"],
            metric["f1"],
        ),
    )


def calibrate_candidates(
    candidates: dict[str, Pipeline],
    x_train: pd.DataFrame,
    y_train: pd.Series,
    target_recall: float,
    min_precision: float,
) -> tuple[str, dict[str, dict[str, object]]]:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    summary: dict[str, dict[str, object]] = {}
    best_name = ""
    best_score: tuple[float, float, float, float] | None = None

    for name, pipeline in candidates.items():
        out_of_fold_probabilities = cross_val_predict(
            pipeline,
            x_train,
            y_train,
            cv=cv,
            method="predict_proba",
            n_jobs=-1,
        )[:, 1]

        threshold_metrics = [
            _threshold_metrics(y_train, out_of_fold_probabilities, threshold)
            for threshold in THRESHOLD_GRID
        ]
        selected_threshold = _pick_screening_threshold(
            threshold_metrics, target_recall, min_precision
        )
        oof_roc_auc = float(roc_auc_score(y_train, out_of_fold_probabilities))

        summary[name] = {
            "oof_roc_auc": oof_roc_auc,
            "selected_threshold": selected_threshold,
            "threshold_sweep": threshold_metrics,
        }

        score = (
            float(selected_threshold["balanced_accuracy"]),
            float(selected_threshold["precision"]),
            float(selected_threshold["recall"]),
            oof_roc_auc,
        )
        if best_score is None or score > best_score:
            best_name = name
            best_score = score

    if not best_name:
        raise RuntimeError("No candidate model was selected.")

    return best_name, summary


def evaluate_test_set(
    pipeline: Pipeline,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float,
) -> dict[str, object]:
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= threshold).astype(int)

    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "classification_report": classification_report(
            y_test, predictions, output_dict=True, zero_division=0
        ),
    }


def save_artifacts(
    output_dir: Path,
    pipeline: Pipeline,
    features: pd.DataFrame,
    feature_config: dict[str, object],
    train_rows: int,
    test_rows: int,
    positive_rate: float,
    selected_model: str,
    selected_threshold: float,
    calibration_summary: dict[str, dict[str, object]],
    test_metrics: dict[str, object],
    target_recall: float,
    min_precision: float,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    model_payload = {
        "pipeline": pipeline,
        "feature_columns": features.columns.tolist(),
        "feature_config": feature_config,
        "target_mapping": {"F": 0, "T": 1},
        "selected_model": selected_model,
        "decision_threshold": float(selected_threshold),
    }
    joblib.dump(model_payload, output_dir / "model.joblib")

    metrics_payload = {
        "dataset_handle": DATASET_HANDLE,
        "dataset_filename": DATASET_FILENAME,
        "rows_total": int(train_rows + test_rows),
        "rows_train": int(train_rows),
        "rows_test": int(test_rows),
        "positive_rate": positive_rate,
        "selected_model": selected_model,
        "decision_threshold": float(selected_threshold),
        "feature_config": feature_config,
        "screening_targets": {
            "target_recall": target_recall,
            "min_precision": min_precision,
        },
        "calibration_summary": calibration_summary,
        "test_metrics": test_metrics,
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics_payload, indent=2), encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    df = load_dataset()
    features, target, feature_config = build_features(df)

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=args.test_size,
        stratify=target,
        random_state=RANDOM_STATE,
    )

    preprocessor = build_preprocessor(features)
    candidates = build_candidates(preprocessor)
    selected_model, calibration_summary = calibrate_candidates(
        candidates, x_train, y_train, args.target_recall, args.min_precision
    )
    pipeline = candidates[selected_model]
    pipeline.fit(x_train, y_train)

    selected_threshold = float(
        calibration_summary[selected_model]["selected_threshold"]["threshold"]
    )
    test_metrics = evaluate_test_set(pipeline, x_test, y_test, selected_threshold)
    output_dir = Path(args.output_dir)
    save_artifacts(
        output_dir=output_dir,
        pipeline=pipeline,
        features=features,
        feature_config=feature_config,
        train_rows=len(x_train),
        test_rows=len(x_test),
        positive_rate=float(target.mean()),
        selected_model=selected_model,
        selected_threshold=selected_threshold,
        calibration_summary=calibration_summary,
        test_metrics=test_metrics,
        target_recall=args.target_recall,
        min_precision=args.min_precision,
    )

    print(f"Selected model: {selected_model}")
    print(f"Decision threshold: {selected_threshold:.2f}")
    print("Calibration summary:")
    print(json.dumps(calibration_summary, indent=2))
    print("Test metrics:")
    print(json.dumps(test_metrics, indent=2))
    print(f"Saved artifacts to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
