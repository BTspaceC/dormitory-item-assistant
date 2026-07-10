from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectPercentile, chi2
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import OneHotEncoder

try:
    from .external_data import JD_DATASET_COMMIT, JD_DATASET_LICENSE, JD_DATASET_URL
    from .features import (
        CATEGORIES,
        RISK_FEATURES,
        RISK_LABELS,
        category_rule_override,
        hybrid_risk_decision,
        jieba_tokenize,
        normalize_category,
        risk_rule_baseline,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from external_data import JD_DATASET_COMMIT, JD_DATASET_LICENSE, JD_DATASET_URL
    from features import (
        CATEGORIES,
        RISK_FEATURES,
        RISK_LABELS,
        category_rule_override,
        hybrid_risk_decision,
        jieba_tokenize,
        normalize_category,
        risk_rule_baseline,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXTERNAL_DATA_PATH = PROJECT_ROOT / "data" / "external" / "jd_category_samples.csv.gz"
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train category and risk models.")
    parser.add_argument("--train", type=Path, default=PROCESSED_DIR / "train.csv")
    parser.add_argument("--test", type=Path, default=PROCESSED_DIR / "test_real_holdout.csv")
    parser.add_argument("--external", type=Path, default=EXTERNAL_DATA_PATH)
    parser.add_argument("--without-external", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(args.train)
    test_df = pd.read_csv(args.test)
    validate_training_data(train_df)
    external_df = load_external_data(None if args.without_external else args.external)

    baseline_category_model = train_baseline_category_model(train_df)
    category_model = train_category_model(train_df, external_df)
    risk_model = train_risk_model(train_df)
    results = evaluate_models(
        category_model,
        baseline_category_model,
        risk_model,
        test_df,
        external_df,
    )
    trained_at = datetime.now().isoformat(timespec="seconds")
    external_train_rows = int((external_df["dataset_split"] == "external_train").sum())
    external_eval_rows = int((external_df["dataset_split"] == "external_eval").sum())

    joblib.dump(
        {
            "model": category_model,
            "labels": CATEGORIES,
            "trained_at": trained_at,
            "input": "item_name + user_description",
            "training_design": "local reviewed samples (50x domain resampling) + balanced JD category metadata",
            "external_train_rows": external_train_rows,
        },
        MODELS_DIR / "category_model.joblib",
    )
    joblib.dump(
        {
            "model": risk_model,
            "labels": RISK_LABELS,
            "features": RISK_FEATURES,
            "trained_at": trained_at,
            "decision_policy": "safety/replenishment gates + random forest",
        },
        MODELS_DIR / "risk_model.joblib",
    )

    metrics = {
        key: value
        for key, value in results.items()
        if key.endswith(("accuracy", "macro_f1"))
    }
    metadata = {
        "trained_at": trained_at,
        "train_rows": int(len(train_df)),
        "category_train_rows": int(len(train_df) + external_train_rows),
        "external_category_train_rows": external_train_rows,
        "external_category_eval_rows": external_eval_rows,
        "local_reviewed_holdout_rows": int(len(test_df)),
        "real_holdout_rows": int(len(test_df)),
        "category_labels": CATEGORIES,
        "risk_labels": RISK_LABELS,
        "risk_features": RISK_FEATURES,
        "external_data": {
            "name": "JD dataset",
            "url": JD_DATASET_URL,
            "commit": JD_DATASET_COMMIT,
            "license": JD_DATASET_LICENSE,
            "usage": "category classification only; never used as risk labels",
        },
        "metrics": metrics,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    (MODELS_DIR / "model_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_model_report(results, train_df, test_df, external_train_rows, external_eval_rows)

    print("saved models/category_model.joblib")
    print("saved models/risk_model.joblib")
    print("saved reports/model_eval.md")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


def load_external_data(path: Path | None) -> pd.DataFrame:
    columns = [
        "source_id",
        "item_name",
        "user_description",
        "category",
        "source_category_2",
        "source_category_3",
        "source",
        "dataset_split",
    ]
    if path is None:
        return pd.DataFrame(columns=columns)
    if not path.exists():
        raise FileNotFoundError(
            f"External category data not found: {path}. "
            "Run python -m src.external_data first, or use --without-external."
        )
    external_df = pd.read_csv(path)
    missing = sorted(set(columns) - set(external_df.columns))
    if missing:
        raise ValueError(f"External data is missing columns: {missing}")
    unknown = sorted(set(external_df["category"]) - set(CATEGORIES))
    if unknown:
        raise ValueError(f"External data has unknown categories: {unknown}")
    allowed_splits = {"external_train", "external_eval"}
    invalid_splits = sorted(set(external_df["dataset_split"]) - allowed_splits)
    if invalid_splits:
        raise ValueError(f"External data has invalid splits: {invalid_splits}")
    return external_df


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


def make_baseline_category_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(tokenizer=jieba_tokenize, token_pattern=None, min_df=2),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
            ),
        ]
    )


def train_baseline_category_model(train_df: pd.DataFrame) -> Pipeline:
    search = GridSearchCV(
        make_baseline_category_pipeline(),
        param_grid={"classifier__C": [0.1, 1.0, 10.0]},
        cv=3,
        scoring="f1_macro",
    )
    search.fit(build_text(train_df), train_df["category"])
    return search.best_estimator_


def make_enhanced_category_pipeline() -> Pipeline:
    text_features = FeatureUnion(
        [
            (
                "char",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(2, 5),
                    min_df=2,
                    max_features=100_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "word",
                TfidfVectorizer(
                    tokenizer=jieba_tokenize,
                    token_pattern=None,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=60_000,
                    sublinear_tf=True,
                ),
            ),
        ]
    )
    return Pipeline(
        steps=[
            ("tfidf", text_features),
            ("select", SelectPercentile(chi2, percentile=80)),
            (
                "classifier",
                LogisticRegression(
                    C=4.0,
                    max_iter=700,
                    solver="saga",
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def train_category_model(train_df: pd.DataFrame, external_df: pd.DataFrame) -> Pipeline:
    external_train = external_df.loc[external_df["dataset_split"] == "external_train"]
    local_domain_rows = pd.concat(
        [train_df[TEXT_COLUMNS + ["category"]]] * 50,
        ignore_index=True,
    )
    combined = pd.concat(
        [local_domain_rows, external_train[TEXT_COLUMNS + ["category"]]],
        ignore_index=True,
    )
    model = make_enhanced_category_pipeline()
    model.fit(build_text(combined), combined["category"])
    return model


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
        scoring="f1_macro",
    )
    search.fit(train_df[RISK_FEATURES], train_df["risk_label"])
    return search.best_estimator_


def evaluate_models(
    category_model: Pipeline,
    baseline_category_model: Pipeline,
    risk_model: Pipeline,
    test_df: pd.DataFrame,
    external_df: pd.DataFrame,
) -> dict:
    category_pred = hybrid_category_predictions(category_model, test_df)
    baseline_category_pred = hybrid_category_predictions(baseline_category_model, test_df)

    external_eval = external_df.loc[external_df["dataset_split"] == "external_eval"]
    if len(external_eval):
        external_pred = category_model.predict(build_text(external_eval))
        external_baseline_pred = baseline_category_model.predict(build_text(external_eval))
        external_accuracy = float(accuracy_score(external_eval["category"], external_pred))
        external_macro_f1 = float(
            f1_score(external_eval["category"], external_pred, labels=CATEGORIES, average="macro", zero_division=0)
        )
        external_baseline_accuracy = float(accuracy_score(external_eval["category"], external_baseline_pred))
        external_baseline_macro_f1 = float(
            f1_score(
                external_eval["category"],
                external_baseline_pred,
                labels=CATEGORIES,
                average="macro",
                zero_division=0,
            )
        )
    else:
        external_accuracy = external_macro_f1 = 0.0
        external_baseline_accuracy = external_baseline_macro_f1 = 0.0

    risk_oracle_pred = risk_model.predict(test_df[RISK_FEATURES])
    e2e_df = test_df.copy()
    e2e_df["category"] = category_pred
    risk_model_pred = risk_model.predict(e2e_df[RISK_FEATURES])
    hybrid_pairs = [
        hybrid_risk_decision(row, model_prediction)
        for row, model_prediction in zip(e2e_df.to_dict(orient="records"), risk_model_pred)
    ]
    risk_hybrid_pred = [prediction for prediction, _ in hybrid_pairs]
    risk_decision_sources = [source for _, source in hybrid_pairs]
    rule_pred = [risk_rule_baseline(row) for row in test_df.to_dict(orient="records")]

    return {
        "category_pred": category_pred,
        "baseline_category_pred": baseline_category_pred,
        "risk_oracle_pred": risk_oracle_pred,
        "risk_model_pred": risk_model_pred,
        "risk_hybrid_pred": risk_hybrid_pred,
        "risk_decision_sources": risk_decision_sources,
        "rule_pred": rule_pred,
        "baseline_category_accuracy": float(accuracy_score(test_df["category"], baseline_category_pred)),
        "baseline_category_macro_f1": macro_f1(test_df["category"], baseline_category_pred, CATEGORIES),
        "category_accuracy": float(accuracy_score(test_df["category"], category_pred)),
        "category_macro_f1": macro_f1(test_df["category"], category_pred, CATEGORIES),
        "external_baseline_category_accuracy": external_baseline_accuracy,
        "external_baseline_category_macro_f1": external_baseline_macro_f1,
        "external_category_accuracy": external_accuracy,
        "external_category_macro_f1": external_macro_f1,
        "risk_oracle_accuracy": float(accuracy_score(test_df["risk_label"], risk_oracle_pred)),
        "risk_oracle_macro_f1": macro_f1(test_df["risk_label"], risk_oracle_pred, RISK_LABELS),
        "risk_model_accuracy": float(accuracy_score(test_df["risk_label"], risk_model_pred)),
        "risk_model_macro_f1": macro_f1(test_df["risk_label"], risk_model_pred, RISK_LABELS),
        "risk_hybrid_accuracy": float(accuracy_score(test_df["risk_label"], risk_hybrid_pred)),
        "risk_hybrid_macro_f1": macro_f1(test_df["risk_label"], risk_hybrid_pred, RISK_LABELS),
        "rule_baseline_accuracy": float(accuracy_score(test_df["risk_label"], rule_pred)),
        "rule_baseline_macro_f1": macro_f1(test_df["risk_label"], rule_pred, RISK_LABELS),
        "category_report": classification_report(
            test_df["category"], category_pred, labels=CATEGORIES, zero_division=0
        ),
        "risk_report": classification_report(
            test_df["risk_label"], risk_hybrid_pred, labels=RISK_LABELS, zero_division=0
        ),
        "risk_confusion_matrix": confusion_matrix(
            test_df["risk_label"], risk_hybrid_pred, labels=RISK_LABELS
        ).tolist(),
    }


def macro_f1(actual: pd.Series, predicted: list[str], labels: list[str]) -> float:
    return float(f1_score(actual, predicted, labels=labels, average="macro", zero_division=0))


def build_text(df: pd.DataFrame) -> pd.Series:
    return df[TEXT_COLUMNS].fillna("").agg(" ".join, axis=1)


def hybrid_category_predictions(category_model: Pipeline, df: pd.DataFrame) -> list[str]:
    texts = build_text(df)
    raw_pred = category_model.predict(texts)
    proba = category_model.predict_proba(texts)
    predictions: list[str] = []
    for row, predicted, probabilities in zip(df.to_dict(orient="records"), raw_pred, proba):
        confidence = float(max(probabilities))
        fallback = normalize_category("", row["item_name"], row.get("user_description", ""))
        rule_override = category_rule_override(row["item_name"], row.get("user_description", ""))
        if rule_override is not None:
            predictions.append(rule_override)
        elif confidence < 0.40 and fallback != "其他用品":
            predictions.append(fallback)
        else:
            predictions.append(predicted)
    return predictions


def write_model_report(
    results: dict,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    external_train_rows: int,
    external_eval_rows: int,
) -> None:
    comparison_rows = []
    for row, category_pred, model_risk, hybrid_risk, source, rule_risk in zip(
        test_df.to_dict(orient="records"),
        results["category_pred"],
        results["risk_model_pred"],
        results["risk_hybrid_pred"],
        results["risk_decision_sources"],
        results["rule_pred"],
    ):
        comparison_rows.append(
            f"| {row['item_name']} | {row['category']} | {category_pred} | {row['risk_label']} | "
            f"{model_risk} | {hybrid_risk} | {source} | {rule_risk} |"
        )

    matrix_rows = [
        "| " + label + " | " + " | ".join(str(value) for value in values) + " |"
        for label, values in zip(RISK_LABELS, results["risk_confusion_matrix"])
    ]

    report = f"""# 模型评估报告

## 评估边界

- 本地训练样本：{len(train_df)} 条；本地人工复核留出样本：{len(test_df)} 条。
- 外部类别训练样本：{external_train_rows} 条；同源规则映射留出样本：{external_eval_rows} 条。
- 外部数据仅提供商品类别，不含库存、有效期或破损状态，因此**未用于风险模型训练**。
- 外部来源：[JD dataset]({JD_DATASET_URL})，固定版本 `{JD_DATASET_COMMIT[:8]}`，许可证 `{JD_DATASET_LICENSE}`。
- 7,000 条外部评估样本与训练样本来自同一公开数据源，标签由同一套规则映射产生，不是独立人工标注。
- 本地人工复核留出集只有 {len(test_df)} 条，以下风险指标波动较大，仅用于检查当前流程在这组样本上的表现。

## 类别模型：优化前后

| 评估集 | 模型 | Accuracy | Macro F1 |
|:---|:---|---:|---:|
| 本地人工复核留出集 | 原始中文分词 TF-IDF | {results['baseline_category_accuracy']:.3f} | {results['baseline_category_macro_f1']:.3f} |
| 本地人工复核留出集 | 字符 + 中文词组 TF-IDF（优化后） | {results['category_accuracy']:.3f} | {results['category_macro_f1']:.3f} |
| 同源规则映射留出集 | 原始中文分词 TF-IDF | {results['external_baseline_category_accuracy']:.3f} | {results['external_baseline_category_macro_f1']:.3f} |
| 同源规则映射留出集 | 字符 + 中文词组 TF-IDF（优化后） | {results['external_category_accuracy']:.3f} | {results['external_category_macro_f1']:.3f} |

## 风险决策：优化前后

| 方法 | Accuracy | Macro F1 |
|:---|---:|---:|
| 随机森林（原端到端策略） | {results['risk_model_accuracy']:.3f} | {results['risk_model_macro_f1']:.3f} |
| 规则基线 | {results['rule_baseline_accuracy']:.3f} | {results['rule_baseline_macro_f1']:.3f} |
| **混合风险决策（优化后）** | **{results['risk_hybrid_accuracy']:.3f}** | **{results['risk_hybrid_macro_f1']:.3f}** |
| 随机森林（人工复核类别，仅诊断） | {results['risk_oracle_accuracy']:.3f} | {results['risk_oracle_macro_f1']:.3f} |

混合策略把确定性条件交给规则：30 天内到期直接进入高风险，低库存且高频使用直接建议补货；随机森林负责其余模糊边界。无有效期物品只有通用破损标记时先校准为“需要关注”，避免把轻微磨损与明确失效混为一类。

## 本地人工复核留出样本明细

| 物品 | 复核类别 | 预测类别 | 复核风险 | 原模型风险 | 混合风险 | 决策来源 | 规则基线 |
|:---|:---|:---|:---|:---|:---|:---|:---|
{chr(10).join(comparison_rows)}

## 混合风险决策混淆矩阵

| 复核标签 \\ 预测标签 | {' | '.join(RISK_LABELS)} |
|:---|---:|---:|---:|---:|
{chr(10).join(matrix_rows)}

## 类别模型详细报告（本地人工复核留出集）

```text
{results['category_report']}
```

## 混合风险决策详细报告（本地人工复核留出集）

```text
{results['risk_report']}
```

## 仍然存在的限制

1. 京东数据与宿舍物品存在领域差异，训练时对本地复核样本做 50 倍领域重采样，并保留关键词兜底。
2. 外部商品元数据只能改善类别识别，不能证明风险模型具有大规模泛化能力。
3. 风险结果仍应结合包装有效期和物品实际状态人工核验；系统不替代医疗或安全判断。
"""
    (REPORTS_DIR / "model_eval.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
