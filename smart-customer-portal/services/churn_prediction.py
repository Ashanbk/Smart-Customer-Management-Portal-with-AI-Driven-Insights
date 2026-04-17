from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import selectinload

from models import Customer, db

FEATURE_NAMES = [
    "nps_score",
    "monthly_usage",
    "ticket_count",
    "contract_days_left",
]

FEATURE_LABELS = {
    "nps_score": "NPS score",
    "monthly_usage": "Monthly usage",
    "ticket_count": "Ticket count",
    "contract_days_left": "Contract days left",
}

MIN_TRAINING_CUSTOMERS = 25
MODEL_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = MODEL_DIR / "churn_model.joblib"


def _customer_feature_vector(customer: Customer) -> np.ndarray:
    contract_days_left = max((customer.contract_end - date.today()).days, 0)
    return np.array(
        [
            float(customer.nps_score),
            float(customer.monthly_usage),
            float(len(customer.tickets)),
            float(contract_days_left),
        ],
        dtype=float,
    )


def _heuristic_risk_score(features: np.ndarray) -> float:
    nps_score, monthly_usage, ticket_count, contract_days_left = features

    nps_risk = max(0.0, -nps_score / 100.0)
    usage_risk = max(0.0, (8000.0 - monthly_usage) / 8000.0)
    ticket_risk = min(ticket_count, 10.0) / 10.0
    expiry_risk = 1.0 - min(contract_days_left, 365.0) / 365.0

    return (
        nps_risk * 0.35
        + usage_risk * 0.25
        + ticket_risk * 0.25
        + expiry_risk * 0.15
    )


def _build_training_dataset(customers: list[Customer]) -> tuple[np.ndarray, np.ndarray]:
    vectors = np.vstack([_customer_feature_vector(customer) for customer in customers])
    risk_scores = np.array([_heuristic_risk_score(vector) for vector in vectors], dtype=float)

    threshold = float(np.quantile(risk_scores, 0.60))
    labels = np.array([1 if score >= threshold else 0 for score in risk_scores], dtype=int)

    if len(np.unique(labels)) < 2:
        ranked_indices = np.argsort(risk_scores)
        labels = np.zeros(len(risk_scores), dtype=int)
        labels[ranked_indices[len(ranked_indices) // 2 :]] = 1

    return vectors, labels


def train_and_store_churn_model() -> dict:
    customers = (
        db.session.query(Customer)
        .options(selectinload(Customer.tickets))
        .order_by(Customer.id.asc())
        .all()
    )
    if len(customers) < MIN_TRAINING_CUSTOMERS:
        raise ValueError(
            f"At least {MIN_TRAINING_CUSTOMERS} customers are required to train the churn model."
        )

    features, labels = _build_training_dataset(customers)

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )
    pipeline.fit(features, labels)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "pipeline": pipeline,
        "feature_names": FEATURE_NAMES,
        "trained_at": datetime.utcnow().isoformat(),
        "sample_count": len(customers),
    }
    joblib.dump(payload, MODEL_PATH)
    return payload


def _load_model_payload() -> dict:
    if not MODEL_PATH.exists():
        return train_and_store_churn_model()
    return joblib.load(MODEL_PATH)


def _feature_explanation(payload: dict, feature_vector: np.ndarray) -> dict:
    pipeline = payload["pipeline"]
    scaler: StandardScaler = pipeline.named_steps["scaler"]
    model: LogisticRegression = pipeline.named_steps["model"]

    scaled_features = (feature_vector - scaler.mean_) / scaler.scale_
    contributions = model.coef_[0] * scaled_features

    factors = []
    for feature_name, raw_value, contribution in zip(
        FEATURE_NAMES, feature_vector, contributions
    ):
        impact = float(contribution)
        direction = (
            "increases churn risk"
            if impact > 0
            else "decreases churn risk"
            if impact < 0
            else "neutral impact"
        )
        factors.append(
            {
                "factor": feature_name,
                "label": FEATURE_LABELS[feature_name],
                "value": round(float(raw_value), 4),
                "impact": round(impact, 4),
                "direction": direction,
            }
        )

    ranked_factors = sorted(factors, key=lambda factor: abs(factor["impact"]), reverse=True)
    top_factors = ranked_factors[:3]
    summary_parts = [f"{factor['label']} ({factor['direction']})" for factor in top_factors]
    summary = "Top contributors: " + ", ".join(summary_parts) + "."

    return {
        "summary": summary,
        "top_factors": top_factors,
    }


def predict_customer_churn_risk(customer: Customer) -> dict:
    payload = _load_model_payload()
    pipeline: Pipeline = payload["pipeline"]

    feature_vector = _customer_feature_vector(customer)
    probability = float(pipeline.predict_proba(feature_vector.reshape(1, -1))[0][1])
    explanation = _feature_explanation(payload, feature_vector)

    return {
        "churn_probability": round(probability, 4),
        "explanation": explanation,
    }
