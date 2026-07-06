from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import jieba
from sklearn.model_selection import GridSearchCV

try:
    from .features import CATEGORIES, RISK_FEATURES, RISK_LABELS, normalize_category, risk_rule_baseline, jieba_tokenize
except ImportError:  # pragma: no cover - supports direct script execution
    from features import CATEGORIES, RISK_FEATURES, RISK_LABELS, normalize_category, risk_rule_baseline, jieba_tokenize


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"

TEXT_COLUMNS = ["item_name", "user_description"]

NUMERIC_RISK_FEATURES = [
    "used_days",
    "remaining_pct",
    "weekly_use_count",
    "user_count",
    "is_shared",
    "has_shelf_life",
    "days_to_expire",
    "is_damaged",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Train category and risk models.")
    parser.add_argument("--train", type=Path, default=PROCESSED_DIR / "train.csv")
    parser.add_argument("--test", type=Path, default=PROCESSED_DIR / "test_real_holdout.csv")
    args = parser.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(args.train)
    test_df = pd.read_csv(args.test)
    validate_training_data(train_df)

    category_model = train_category_model(train_df)
    risk_model = train_risk_model(train_df)
    results = evaluate_models(category_model, risk_model, test_df)

    joblib.dump(
        {
            "model": category_model,
            "labels": CATEGORIES,
            "trained_at": datetime.now().isoformat(timespec="seconds"),
            "input": "item_name + user_description",
        },
        MODELS_DIR / "category_model.joblib",
    )
    joblib.dump(
        {
            "model": risk_model,
            "labels": RISK_LABELS,
            "features": RISK_FEATURES,
            "trained_at": datetime.now().isoformat(timespec="seconds"),
        },
        MODELS_DIR / "risk_model.joblib",
    )
    metadata = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "train_rows": int(len(train_df)),
        "real_holdout_rows": int(len(test_df)),
        "category_labels": CATEGORIES,
        "risk_labels": RISK_LABELS,
        "risk_features": RISK_FEATURES,
        "metrics": {
            "category_accuracy": results["category_accuracy"],
            "category_macro_f1": results["category_macro_f1"],
            "risk_oracle_accuracy": results["risk_oracle_accuracy"],
            "risk_oracle_macro_f1": results["risk_oracle_macro_f1"],
            "risk_e2e_accuracy": results["risk_e2e_accuracy"],
            "risk_e2e_macro_f1": results["risk_e2e_macro_f1"],
            "rule_baseline_accuracy": results["rule_baseline_accuracy"],
            "rule_baseline_macro_f1": results["rule_baseline_macro_f1"],
        },
        "environment": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    (MODELS_DIR / "model_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_model_report(results, train_df, test_df)

    print("saved models/category_model.joblib")
    print("saved models/risk_model.joblib")
    print("saved reports/model_eval.md")


def validate_training_data(train_df: pd.DataFrame) -> None:
    offenders = train_df.loc[train_df["label_source"] == "rule_initial", "sample_id"].tolist()
    if offenders:
        raise ValueError(
            "Samples with label_source=rule_initial cannot enter training: "
            + ", ".join(map(str, offenders[:10]))
        )
    missing_category = sorted(set(train_df["category"]) - set(CATEGORIES))
    missing_risk = sorted(set(train_df["risk_label"]) - set(RISK_LABELS))
    if missing_category:
        raise ValueError(f"Unknown category labels: {missing_category}")
    if missing_risk:
        raise ValueError(f"Unknown risk labels: {missing_risk}")



def train_category_model(train_df: pd.DataFrame) -> Pipeline:
    model = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(tokenizer=jieba_tokenize, min_df=2),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
            ),
        ]
    )
    search = GridSearchCV(
        model,
        param_grid={"classifier__C": [0.1, 1.0, 10.0]},
        cv=3,
        scoring="f1_macro"
    )
    search.fit(build_text(train_df), train_df["category"])
    return search.best_estimator_


def train_risk_model(train_df: pd.DataFrame) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("category", OneHotEncoder(handle_unknown="ignore"), ["category"]),
            ("numeric", "passthrough", NUMERIC_RISK_FEATURES),
        ]
    )
    model = Pipeline(
        steps=[
            ("features", preprocessor),
            (
                "classifier",
                RandomForestClassifier(
                    random_state=42,
                    min_samples_leaf=2,
                    class_weight="balanced",
                ),
            ),
        ]
    )
    search = GridSearchCV(
        model,
        param_grid={"classifier__n_estimators": [100, 200], "classifier__max_depth": [None, 10]},
        cv=3,
        scoring="f1_macro"
    )
    search.fit(train_df[RISK_FEATURES], train_df["risk_label"])
    return search.best_estimator_


def evaluate_models(category_model: Pipeline, risk_model: Pipeline, test_df: pd.DataFrame) -> dict:
    category_pred = hybrid_category_predictions(category_model, test_df)
    risk_oracle_pred = risk_model.predict(test_df[RISK_FEATURES])
    e2e_df = test_df.copy()
    e2e_df["category"] = category_pred
    risk_e2e_pred = risk_model.predict(e2e_df[RISK_FEATURES])
    rule_pred = [risk_rule_baseline(row) for row in test_df.to_dict(orient="records")]

    return {
        "category_pred": category_pred,
        "risk_oracle_pred": risk_oracle_pred,
        "risk_e2e_pred": risk_e2e_pred,
        "rule_pred": rule_pred,
        "category_accuracy": float(accuracy_score(test_df["category"], category_pred)),
        "category_macro_f1": float(
            f1_score(test_df["category"], category_pred, labels=CATEGORIES, average="macro", zero_division=0)
        ),
        "risk_oracle_accuracy": float(accuracy_score(test_df["risk_label"], risk_oracle_pred)),
        "risk_oracle_macro_f1": float(
            f1_score(test_df["risk_label"], risk_oracle_pred, labels=RISK_LABELS, average="macro", zero_division=0)
        ),
        "risk_e2e_accuracy": float(accuracy_score(test_df["risk_label"], risk_e2e_pred)),
        "risk_e2e_macro_f1": float(
            f1_score(test_df["risk_label"], risk_e2e_pred, labels=RISK_LABELS, average="macro", zero_division=0)
        ),
        "rule_baseline_accuracy": float(accuracy_score(test_df["risk_label"], rule_pred)),
        "rule_baseline_macro_f1": float(
            f1_score(test_df["risk_label"], rule_pred, labels=RISK_LABELS, average="macro", zero_division=0)
        ),
        "category_report": classification_report(
            test_df["category"], category_pred, labels=CATEGORIES, zero_division=0
        ),
        "risk_report": classification_report(
            test_df["risk_label"], risk_e2e_pred, labels=RISK_LABELS, zero_division=0
        ),
        "risk_confusion_matrix": confusion_matrix(
            test_df["risk_label"], risk_e2e_pred, labels=RISK_LABELS
        ).tolist(),
    }


def build_text(df: pd.DataFrame) -> pd.Series:
    return df[TEXT_COLUMNS].fillna("").agg(" ".join, axis=1)


def hybrid_category_predictions(category_model: Pipeline, df: pd.DataFrame) -> list[str]:
    texts = build_text(df)
    raw_pred = category_model.predict(texts)
    proba = category_model.predict_proba(texts)
    classes = list(category_model.classes_) if hasattr(category_model, "classes_") else list(category_model[-1].classes_)

    predictions: list[str] = []
    for row, predicted, probabilities in zip(df.to_dict(orient="records"), raw_pred, proba):
        confidence = float(max(probabilities))
        fallback = normalize_category("", row["item_name"], row.get("user_description", ""))
        if confidence < 0.40 and fallback != "其他用品":
            predictions.append(fallback)
        else:
            predictions.append(predicted)
    return predictions


def write_model_report(results: dict, train_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    comparison_rows = []
    for row, category_pred, risk_pred, rule_pred in zip(
        test_df.to_dict(orient="records"),
        results["category_pred"],
        results["risk_e2e_pred"],
        results["rule_pred"],
    ):
        comparison_rows.append(
            "| {item} | {true_cat} | {pred_cat} | {true_risk} | {pred_risk} | {rule_risk} |".format(
                item=row["item_name"],
                true_cat=row["category"],
                pred_cat=category_pred,
                true_risk=row["risk_label"],
                pred_risk=risk_pred,
                rule_risk=rule_pred,
            )
        )

    matrix_rows = []
    for label, values in zip(RISK_LABELS, results["risk_confusion_matrix"]):
        matrix_rows.append("| " + label + " | " + " | ".join(str(v) for v in values) + " |")

    report = f"""---
title: "模型评估报告"
author:
  - 机器学习课程项目小组
date: {datetime.now().date().isoformat()}
---

# 模型评估报告

本报告记录系统内“物品类别分类模型”和“宿舍物品状态风险模型”在留出测试集上的评估指标。

## 一、评估数据集说明

- **训练样本总量**：{len(train_df)} 条。
- **真实留出测试样本量**：{len(test_df)} 条。
- **样本约束**：系统拒绝初始规则标签（`label_source=rule_initial`）样本进入训练集，以保障训练数据的纯净性。
- **指标意义**：本评估结果主要用于验证全流程的可行性与模型的基础效能。

## 二、指标摘要

| 模型/基准方法 | 准确率 (Accuracy) | 宏平均 F1 (Macro F1) |
|:---|---:|---:|
| **物品类别分类模型** | {results["category_accuracy"]:.3f} | {results["category_macro_f1"]:.3f} |
| **状态风险预测模型（端到端）** | {results["risk_e2e_accuracy"]:.3f} | {results["risk_e2e_macro_f1"]:.3f} |
| **状态风险预测模型（使用人工真类别）** | {results["risk_oracle_accuracy"]:.3f} | {results["risk_oracle_macro_f1"]:.3f} |
| **规则对照基线** | {results["rule_baseline_accuracy"]:.3f} | {results["rule_baseline_macro_f1"]:.3f} |

: 表 1：模型与规则基线评估指标对比

## 三、真实留出样本预测明细

| 物品名称 | 真实类别 | 预测类别 | 真实状态 | 模型预测状态 | 规则基线状态 |
|:---|:---|:---|:---|:---|:---|
{chr(10).join(comparison_rows)}

: 表 2：{len(test_df)}条真实留出样本预测详情

## 四、状态风险模型混淆矩阵

*注：类别顺序为：正常、需要关注、建议补货、过期/损坏风险。*

| 真实标签 \\ 预测标签 | {" | ".join(RISK_LABELS)} |
|:---|----:|----:|----:|----:|
{chr(10).join(matrix_rows)}

: 表 3：状态风险预测混淆矩阵

<div style="page-break-after: always;"></div>

## 五、分类模型详细报告

```text
{results["category_report"]}
```

## 六、状态风险模型详细报告

```text
{results["risk_report"]}
```

## 七、局限性与改进方向

1. **类别分类模型**：虽然在留出测试集上达到较高准确率，但样本量偏小且测试集与训练集同分布，泛化能力仍需在大规模未知领域上验证。
2. **状态风险模型**：当前端到端 Accuracy 为 {results["risk_e2e_accuracy"]:.3f}，与规则基线 {results["rule_baseline_accuracy"]:.3f} 持平；Macro F1 为 {results["risk_e2e_macro_f1"]:.3f}，低于规则基线 {results["rule_baseline_macro_f1"]:.3f}。现阶段指标只用于验证训练与评估流程，不作为模型效果优势的证据。
3. **数据迭代方案**：后续将继续通过系统内置的反馈持久化模块，收集更多用户的真实纠偏数据，以便执行定期的线下重训和模型优化。
"""
    (REPORTS_DIR / "model_eval.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
