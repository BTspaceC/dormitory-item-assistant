from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

try:
    from .features import (
        CATEGORIES,
        RISK_FEATURES,
        RISK_LABELS,
        advice_for,
        detect_damage,
        estimate_remaining_days,
        explain_risk_factors,
        normalize_category,
        parse_shelf_life,
        risk_rule_baseline,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from features import (
        CATEGORIES,
        RISK_FEATURES,
        RISK_LABELS,
        advice_for,
        detect_damage,
        estimate_remaining_days,
        explain_risk_factors,
        normalize_category,
        parse_shelf_life,
        risk_rule_baseline,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"


@dataclass
class PredictionInput:
    item_name: str
    description: str
    used_days: int
    remaining_pct: float
    weekly_use_count: float
    user_count: int
    is_shared: int
    has_shelf_life: int
    days_to_expire: int
    is_damaged: int
    category_override: str | None = None


def load_models(model_dir: Path = MODELS_DIR) -> tuple[dict[str, Any], dict[str, Any]]:
    category_path = model_dir / "category_model.joblib"
    risk_path = model_dir / "risk_model.joblib"
    if not category_path.exists() or not risk_path.exists():
        raise FileNotFoundError("模型文件不存在，请先运行 python -m src.data_prepare 和 python -m src.train_models。")
    return joblib.load(category_path), joblib.load(risk_path)


def predict(
    input_data: PredictionInput,
    model_dir: Path = MODELS_DIR,
    model_bundles: tuple[dict[str, Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        bundles = model_bundles or load_models(model_dir)
        category_bundle, risk_bundle = bundles
        risk_model = risk_bundle["model"]
        predicted_category, category_probs = predict_category(input_data.item_name, input_data.description, bundles)
    except FileNotFoundError:
        bundles = None
        predicted_category = normalize_category("", input_data.item_name, input_data.description)
        category_probs = {}
        risk_model = None

    risk_category = input_data.category_override or predicted_category
    row = {
        "category": risk_category,
        "used_days": input_data.used_days,
        "remaining_pct": input_data.remaining_pct,
        "weekly_use_count": input_data.weekly_use_count,
        "user_count": input_data.user_count,
        "is_shared": input_data.is_shared,
        "has_shelf_life": input_data.has_shelf_life,
        "days_to_expire": input_data.days_to_expire,
        "is_damaged": input_data.is_damaged,
    }
    
    if risk_model is not None:
        risk_df = pd.DataFrame([row], columns=RISK_FEATURES)
        predicted_risk = risk_model.predict(risk_df)[0]
        risk_probs = get_probabilities(risk_model, risk_df, RISK_LABELS)
    else:
        predicted_risk = risk_rule_baseline(row)
        risk_probs = {}
        
    category_confidence = max(category_probs.values()) if category_probs else 0.0
    risk_confidence = max(risk_probs.values()) if risk_probs else 0.0
    remaining_days = estimate_remaining_days(
        input_data.used_days,
        input_data.remaining_pct,
        input_data.weekly_use_count,
    )

    return {
        "predicted_category": predicted_category,
        "risk_category": risk_category,
        "predicted_risk": predicted_risk,
        "estimated_remaining_days": remaining_days,
        "advice": advice_for(risk_category, predicted_risk, remaining_days),
        "risk_reasons": explain_risk_factors(row, predicted_risk),
        "category_confidence": category_confidence,
        "risk_confidence": risk_confidence,
        "needs_category_review": category_confidence < 0.45,
        "needs_risk_review": risk_confidence < 0.50,
        "category_probabilities": category_probs,
        "risk_probabilities": risk_probs,
    }


def predict_category(
    item_name: str,
    description: str,
    model_bundles: tuple[dict[str, Any], dict[str, Any]] | None = None,
    model_dir: Path = MODELS_DIR,
) -> tuple[str, dict[str, float]]:
    try:
        category_bundle, _ = model_bundles or load_models(model_dir)
        category_model = category_bundle["model"]
        text = f"{item_name} {description}"
        predicted_category = category_model.predict([text])[0]
        category_probs = get_probabilities(category_model, [text], CATEGORIES)
        confidence = max(category_probs.values()) if category_probs else 0.0
    except FileNotFoundError:
        confidence = 0.0
        category_probs = {}
        predicted_category = ""

    fallback_category = normalize_category("", item_name, description)
    if confidence < 0.40 and fallback_category != "其他用品":
        predicted_category = fallback_category
        # Redistribute probability: assign fallback category the max confidence,
        # and scale down other categories proportionally.
        fallback_prob = max(category_probs.get(predicted_category, 0.0), confidence + 0.01)
        other_total = sum(v for k, v in category_probs.items() if k != predicted_category)
        scale = (1.0 - fallback_prob) / other_total if other_total > 0 else 0.0
        category_probs = {
            k: (fallback_prob if k == predicted_category else v * scale)
            for k, v in category_probs.items()
        }
    elif not predicted_category:
        predicted_category = fallback_category
        category_probs = {}
    return predicted_category, category_probs


def get_probabilities(model: Any, values: Any, label_order: list[str]) -> dict[str, float]:
    if not hasattr(model, "predict_proba"):
        return {label: 0.0 for label in label_order}
    probabilities = model.predict_proba(values)[0]
    classes = list(model.classes_) if hasattr(model, "classes_") else list(model[-1].classes_)
    return {
        label: round(float(probabilities[classes.index(label)]), 4) if label in classes else 0.0
        for label in label_order
    }


def make_prediction_input(
    item_name: str,
    description: str,
    used_days: int,
    remaining_pct: float,
    weekly_use_count: float,
    user_count: int,
    is_shared: bool,
    has_shelf_life: bool,
    expiry_date: date | None,
    is_damaged: bool,
    category_override: str | None = None,
) -> PredictionInput:
    if has_shelf_life and expiry_date is not None:
        days_to_expire = (expiry_date - date.today()).days
    elif has_shelf_life:
        _, days_to_expire = parse_shelf_life("需核对包装有效期")
    else:
        days_to_expire = 999
    return PredictionInput(
        item_name=item_name,
        description=description,
        used_days=int(used_days),
        remaining_pct=float(remaining_pct),
        weekly_use_count=float(weekly_use_count),
        user_count=int(user_count),
        is_shared=1 if is_shared else 0,
        has_shelf_life=1 if has_shelf_life else 0,
        days_to_expire=int(days_to_expire),
        is_damaged=1 if is_damaged else 0,
        category_override=category_override if category_override in CATEGORIES else None,
    )
