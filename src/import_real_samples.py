from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from .features import CATEGORIES, RISK_LABELS
except ImportError:  # pragma: no cover
    from features import CATEGORIES, RISK_LABELS


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "data" / "collection" / "real_sample_collection.xlsx"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "collection" / "validated"

SLOTS = ["库存充足", "库存偏低", "临期/损坏或其他"]
YES_NO = {"是": 1, "否": 0, "1": 1, "0": 0, 1: 1, 0: 0, True: 1, False: 0}
REQUIRED_COLUMNS = [
    "participant_id",
    "dataset_split",
    "sampling_slot",
    "item_name",
    "description",
    "category",
    "used_days",
    "remaining_pct",
    "weekly_use_count",
    "user_count",
    "is_shared",
    "has_shelf_life",
    "days_to_expire",
    "is_damaged",
    "risk_label",
    "label_reason",
    "consent",
    "review_status",
    "reviewer_category",
    "reviewer_risk",
    "review_notes",
]

OUTPUT_COLUMNS = [
    "sample_id",
    "participant_id",
    "dataset_split",
    "sampling_slot",
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
    "label_reason",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and split independently collected real samples.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def read_collection(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path, sheet_name="样本采集", dtype=object)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig", dtype=object)
    raise ValueError("采集文件只支持 .xlsx 或 .csv。")


def expected_split(participant_id: str) -> str | None:
    if not participant_id.startswith("P") or not participant_id[1:].isdigit():
        return None
    number = int(participant_id[1:])
    if 1 <= number <= 14:
        return "train"
    if 15 <= number <= 20:
        return "holdout"
    return None


def validate_collection(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"采集表缺少字段：{', '.join(missing)}")

    valid_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for row_index, raw in df.iterrows():
        row = {column: raw.get(column, "") for column in REQUIRED_COLUMNS}
        reasons: list[str] = []
        participant_id = text(row["participant_id"]).upper()
        item_name = text(row["item_name"])
        split = text(row["dataset_split"]).lower()
        slot = text(row["sampling_slot"])

        if not item_name:
            continue
        expected = expected_split(participant_id)
        if expected is None:
            reasons.append("participant_id 必须为 P001-P020")
        elif split != expected:
            reasons.append(f"dataset_split 应为 {expected}")
        if slot not in SLOTS:
            reasons.append("sampling_slot 不在允许范围")
        if text(row["consent"]) != "是":
            reasons.append("未确认匿名研究使用")
        if text(row["review_status"]) != "通过":
            reasons.append("尚未通过人工复核")

        category = text(row["reviewer_category"]) or text(row["category"])
        risk_label = text(row["reviewer_risk"]) or text(row["risk_label"])
        if category not in CATEGORIES:
            reasons.append("类别标签无效")
        if risk_label not in RISK_LABELS:
            reasons.append("风险标签无效")

        used_days = number(row["used_days"], 0, 3650, "used_days", reasons, integer=True)
        remaining_pct = number(row["remaining_pct"], 0, 100, "remaining_pct", reasons)
        weekly_use_count = number(row["weekly_use_count"], 0, 100, "weekly_use_count", reasons)
        user_count = number(row["user_count"], 1, 8, "user_count", reasons, integer=True)
        days_to_expire = number(row["days_to_expire"], -365, 3650, "days_to_expire", reasons, integer=True)

        is_shared = yes_no(row["is_shared"], "is_shared", reasons)
        has_shelf_life = yes_no(row["has_shelf_life"], "has_shelf_life", reasons)
        is_damaged = yes_no(row["is_damaged"], "is_damaged", reasons)
        if has_shelf_life == 0:
            days_to_expire = 999

        duplicate_key = (participant_id, item_name.casefold())
        if duplicate_key in seen:
            reasons.append("同一参与者重复填写同一物品")
        seen.add(duplicate_key)

        if reasons:
            rejected = dict(row)
            rejected["row_number"] = int(row_index) + 2
            rejected["rejection_reason"] = "；".join(reasons)
            rejected_rows.append(rejected)
            continue

        slot_index = SLOTS.index(slot) + 1
        valid_rows.append(
            {
                "sample_id": f"survey_{participant_id.lower()}_{slot_index}",
                "participant_id": participant_id,
                "dataset_split": split,
                "sampling_slot": slot,
                "item_name": item_name,
                "user_description": text(row["description"]),
                "category": category,
                "risk_label": risk_label,
                "used_days": used_days,
                "remaining_pct": remaining_pct,
                "weekly_use_count": weekly_use_count,
                "user_count": user_count,
                "is_shared": is_shared,
                "has_shelf_life": has_shelf_life,
                "days_to_expire": days_to_expire,
                "is_damaged": is_damaged,
                "source": "real_user_v2",
                "label_source": "user_independent_reviewed",
                "original_category": text(row["category"]),
                "original_user_judgment": text(row["risk_label"]),
                "remaining_text": f"剩约{remaining_pct}%",
                "frequency_text": f"每周约{weekly_use_count}次",
                "shelf_life_text": "有保质期" if has_shelf_life else "无",
                "label_reason": text(row["label_reason"]),
                "notes": text(row["review_notes"]) or "独立填写并经人工复核的真实用户样本。",
            }
        )

    valid_df = pd.DataFrame(valid_rows, columns=OUTPUT_COLUMNS)
    rejected_df = pd.DataFrame(rejected_rows)
    return valid_df, rejected_df


def text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def yes_no(value: Any, field: str, reasons: list[str]) -> int | None:
    normalized = text(value)
    key: Any = normalized if normalized else value
    if key in YES_NO:
        return YES_NO[key]
    reasons.append(f"{field} 必须为是/否")
    return None


def number(
    value: Any,
    minimum: float,
    maximum: float,
    field: str,
    reasons: list[str],
    *,
    integer: bool = False,
) -> int | float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        reasons.append(f"{field} 不是数字")
        return None
    if not minimum <= parsed <= maximum:
        reasons.append(f"{field} 应在 {minimum}-{maximum} 之间")
    if integer and not parsed.is_integer():
        reasons.append(f"{field} 必须为整数")
    return int(parsed) if integer else parsed


def write_outputs(valid_df: pd.DataFrame, rejected_df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    valid_df.to_csv(output_dir / "validated_real_samples.csv", index=False, encoding="utf-8-sig")
    valid_df.loc[valid_df["dataset_split"] == "train"].to_csv(
        output_dir / "new_real_train.csv", index=False, encoding="utf-8-sig"
    )
    valid_df.loc[valid_df["dataset_split"] == "holdout"].to_csv(
        output_dir / "new_real_holdout.csv", index=False, encoding="utf-8-sig"
    )
    rejected_df.to_csv(output_dir / "rejected_samples.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    args = parse_args()
    valid_df, rejected_df = validate_collection(read_collection(args.input))
    write_outputs(valid_df, rejected_df, args.output_dir)
    participants = valid_df["participant_id"].nunique() if len(valid_df) else 0
    print(f"valid_samples={len(valid_df)}")
    print(f"participants={participants}")
    print(f"train_samples={(valid_df['dataset_split'] == 'train').sum() if len(valid_df) else 0}")
    print(f"holdout_samples={(valid_df['dataset_split'] == 'holdout').sum() if len(valid_df) else 0}")
    print(f"rejected_samples={len(rejected_df)}")
    if len(valid_df) < 60 or participants < 20:
        print("collection_status=incomplete")
    else:
        print("collection_status=complete")


if __name__ == "__main__":
    main()
