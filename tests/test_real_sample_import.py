from __future__ import annotations

import pandas as pd

from src.import_real_samples import REQUIRED_COLUMNS, validate_collection


def make_row(**overrides):
    row = {
        "participant_id": "P001",
        "dataset_split": "train",
        "sampling_slot": "库存充足",
        "item_name": "洗衣液",
        "description": "宿舍日常使用",
        "category": "清洁日用",
        "used_days": 30,
        "remaining_pct": 70,
        "weekly_use_count": 3,
        "user_count": 2,
        "is_shared": "是",
        "has_shelf_life": "否",
        "days_to_expire": 0,
        "is_damaged": "否",
        "risk_label": "正常",
        "label_reason": "库存充足",
        "consent": "是",
        "review_status": "通过",
        "reviewer_category": "",
        "reviewer_risk": "",
        "review_notes": "",
    }
    row.update(overrides)
    return row


def test_valid_collection_uses_preassigned_split_and_reviewed_labels() -> None:
    valid, rejected = validate_collection(
        pd.DataFrame(
            [
                make_row(reviewer_category="洗漱用品", reviewer_risk="需要关注"),
                make_row(
                    participant_id="P015",
                    dataset_split="holdout",
                    sampling_slot="库存偏低",
                    item_name="牙膏",
                    category="洗漱用品",
                    risk_label="建议补货",
                ),
            ],
            columns=REQUIRED_COLUMNS,
        )
    )

    assert rejected.empty
    assert valid["dataset_split"].tolist() == ["train", "holdout"]
    assert valid.loc[0, "category"] == "洗漱用品"
    assert valid.loc[0, "risk_label"] == "需要关注"
    assert valid.loc[0, "days_to_expire"] == 999


def test_collection_rejects_unreviewed_wrong_split_and_duplicate() -> None:
    valid, rejected = validate_collection(
        pd.DataFrame(
            [
                make_row(review_status="待复核"),
                make_row(participant_id="P016", dataset_split="train", item_name="牙膏"),
                make_row(item_name="洗衣液"),
            ],
            columns=REQUIRED_COLUMNS,
        )
    )

    assert valid.empty
    reasons = " ".join(rejected["rejection_reason"].tolist())
    assert "尚未通过人工复核" in reasons
    assert "dataset_split 应为 holdout" in reasons
    assert "重复填写同一物品" in reasons


def test_collection_skips_prefilled_blank_rows() -> None:
    blank = {column: "" for column in REQUIRED_COLUMNS}
    valid, rejected = validate_collection(pd.DataFrame([blank], columns=REQUIRED_COLUMNS))
    assert valid.empty
    assert rejected.empty
