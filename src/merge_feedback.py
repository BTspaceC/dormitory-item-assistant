from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from filelock import FileLock

try:
    from .features import CATEGORIES, RISK_LABELS, normalize_category, risk_rule_baseline
except ImportError:  # pragma: no cover - supports direct script execution
    from features import CATEGORIES, RISK_LABELS, normalize_category, risk_rule_baseline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = PROJECT_ROOT / "data" / "feedback" / "user_feedback_log.csv"
CANDIDATE_PATH = PROJECT_ROOT / "data" / "feedback" / "feedback_retrain_candidates.csv"
TRIAL_EXPORT_CSV_PATH = PROJECT_ROOT / "reports" / "user_trial_export.csv"
TRIAL_EXPORT_MD_PATH = PROJECT_ROOT / "reports" / "user_trial_export.md"

FEEDBACK_COLUMNS = [
    "timestamp",
    "item_name",
    "description",
    "used_days",
    "remaining_pct",
    "weekly_use_count",
    "user_count",
    "is_shared",
    "has_shelf_life",
    "days_to_expire",
    "is_damaged",
    "predicted_category",
    "corrected_category",
    "predicted_risk",
    "corrected_risk",
    "category_accepted",
    "risk_accepted",
]

OUTPUT_COLUMNS = [
    "sample_id",
    "item_name",
    "user_description",
    "category",
    "risk_label",
    "used_days",
    "remaining_pct",
    "weekly_use_count",
    "user_count",
    "is_shared",
    "has_shelf_life",
    "days_to_expire",
    "is_damaged",
    "source",
    "label_source",
    "original_category",
    "original_user_judgment",
    "remaining_text",
    "frequency_text",
    "shelf_life_text",
    "notes",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert user feedback logs into retraining candidates.")
    parser.add_argument("--feedback", type=Path, default=FEEDBACK_PATH)
    parser.add_argument("--output", type=Path, default=CANDIDATE_PATH)
    args = parser.parse_args()

    candidates = build_feedback_candidates(args.feedback)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    lock_file = args.output.with_suffix('.csv.lock')
    with FileLock(lock_file):
        candidates.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"saved {len(candidates)} feedback retraining candidates to {args.output}")
    if len(candidates):
        print("人工复核后，可将合格样本合并进 data/processed/expanded_samples.csv，再重新训练模型。")


def build_feedback_candidates(feedback_path: Path = FEEDBACK_PATH) -> pd.DataFrame:
    if not feedback_path.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    try:
        feedback_df = pd.read_csv(feedback_path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    rows: list[dict[str, object]] = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for index, row in feedback_df.iterrows():
        item_name = clean_text(row.get("item_name"))
        description = clean_text(row.get("description"))
        predicted_category = clean_text(row.get("predicted_category"))
        corrected_category = clean_text(row.get("corrected_category"))
        predicted_risk = clean_text(row.get("predicted_risk"))
        corrected_risk = clean_text(row.get("corrected_risk"))

        category_rejected = clean_text(row.get("category_accepted")) == "不认可"
        risk_rejected = clean_text(row.get("risk_accepted")) == "不认可"
        if not item_name or not (category_rejected or risk_rejected):
            continue

        final_category = normalize_category(corrected_category or predicted_category, item_name, description)
        if final_category not in CATEGORIES:
            continue
        final_risk = corrected_risk if corrected_risk in RISK_LABELS else predicted_risk
        if final_risk not in RISK_LABELS:
            final_risk = risk_rule_baseline(default_feature_row(final_category))

        rows.append(
            {
                "sample_id": f"feedback_{timestamp}_{index + 1:03d}",
                "item_name": item_name,
                "user_description": description,
                "category": final_category,
                "risk_label": final_risk,
                "used_days": 30,
                "remaining_pct": 50.0,
                "weekly_use_count": 1.0,
                "user_count": 1,
                "is_shared": 0,
                "has_shelf_life": 0,
                "days_to_expire": 999,
                "is_damaged": 0,
                "source": "user_feedback",
                "label_source": "user_corrected",
                "original_category": predicted_category,
                "original_user_judgment": predicted_risk,
                "remaining_text": "用户反馈日志未记录剩余量，需人工复核补充",
                "frequency_text": "用户反馈日志未记录使用频率，需人工复核补充",
                "shelf_life_text": "用户反馈日志未记录保质期，需人工复核补充",
                "notes": "由用户反馈整理出的候选再训练样本，进入训练集前必须人工复核特征字段。",
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def default_feature_row(category: str) -> dict[str, object]:
    return {
        "category": category,
        "remaining_pct": 50,
        "weekly_use_count": 1,
        "has_shelf_life": 0,
        "days_to_expire": 999,
        "is_damaged": 0,
    }


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def ensure_feedback_schema(feedback_path: Path = FEEDBACK_PATH) -> None:
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    if not feedback_path.exists():
        pd.DataFrame(columns=FEEDBACK_COLUMNS).to_csv(feedback_path, index=False, encoding="utf-8-sig")
        return
    try:
        existing = pd.read_csv(feedback_path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        pd.DataFrame(columns=FEEDBACK_COLUMNS).to_csv(feedback_path, index=False, encoding="utf-8-sig")
        return
    if list(existing.columns) == FEEDBACK_COLUMNS:
        return
    migrated = pd.DataFrame(columns=FEEDBACK_COLUMNS)
    for column in FEEDBACK_COLUMNS:
        if column in existing.columns:
            migrated[column] = existing[column]
    migrated.to_csv(feedback_path, index=False, encoding="utf-8-sig")


def append_feedback_record(record: dict[str, Any], feedback_path: Path = FEEDBACK_PATH) -> None:
    ensure_feedback_schema(feedback_path)
    row = {column: record.get(column, "") for column in FEEDBACK_COLUMNS}
    row["timestamp"] = record.get("timestamp") or datetime.now().isoformat()
    
    lock_file = feedback_path.with_suffix(feedback_path.suffix + ".lock")
    with FileLock(str(lock_file), timeout=5):
        df = pd.DataFrame([row], columns=FEEDBACK_COLUMNS)
        df.to_csv(feedback_path, mode="a", header=False, index=False, encoding="utf-8-sig")


def export_trial_records(
    feedback_path: Path = FEEDBACK_PATH,
    csv_path: Path = TRIAL_EXPORT_CSV_PATH,
    md_path: Path = TRIAL_EXPORT_MD_PATH,
) -> tuple[str, str, int]:
    ensure_feedback_schema(feedback_path)
    df = pd.read_csv(feedback_path, encoding="utf-8-sig")
    exported_at = datetime.now().isoformat(timespec="seconds")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write('title: "用户试用数据导出"\n')
        f.write("author:\n")
        f.write("  - 机器学习课程项目小组\n")
        f.write(f"date: {datetime.now().date().isoformat()}\n")
        f.write("---\n\n")
        f.write("# 用户试用数据导出\n\n")
        f.write("本文件记录系统后台捕获并导出的真实用户现场试用及纠偏历史日志。\n\n")
        f.write("## 一、导出概要信息\n\n")
        f.write("| 统计指标 | 详情 |\n")
        f.write("|:---|:---|\n")
        f.write(f"| **数据导出时间** | {exported_at} |\n")
        f.write(f"| **已载入日志条数** | {len(df)} |\n\n")
        f.write("## 二、日志详细记录\n\n")
        if df.empty:
            f.write("*当前暂无活跃用户试用记录日志。*\n")
        else:
            f.write(dataframe_to_markdown(df))
            f.write("\n")
    return str(csv_path), str(md_path), len(df)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    columns = [str(column) for column in df.columns]
    rows = ["| " + " | ".join(escape_markdown_cell(column) for column in columns) + " |"]
    rows.append("| " + " | ".join("---" for _ in columns) + " |")
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(escape_markdown_cell(row.get(column, "")) for column in columns) + " |")
    return "\n".join(rows)


def escape_markdown_cell(value: object) -> str:
    text = clean_text(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


if __name__ == "__main__":
    main()
