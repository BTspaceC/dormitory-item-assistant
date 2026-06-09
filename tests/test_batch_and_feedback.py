from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from src.features import (
    BATCH_EXPIRE_DAYS_COLUMN,
    BATCH_HAS_SHELF_LIFE_COLUMN,
    MAX_BATCH_UPLOAD_ROWS,
)
from src.ui.pages.batch_mode import (
    normalize_batch_columns,
    prepare_batch_upload_df,
    read_batch_upload,
)
from src.ui.utils import clean_html
from src.ui.pages.docs_page import strip_yaml_frontmatter
from src.merge_feedback import build_feedback_candidates
from src.merge_feedback import (
    FEEDBACK_COLUMNS,
    append_feedback_record,
    ensure_feedback_schema,
    export_trial_records,
)


def test_normalize_batch_columns_accepts_legacy_column_names() -> None:
    raw = pd.DataFrame(
        [
            {
                "物品名称": "感冒药",
                "剩余量百分比": 50,
                "每周使用次数": 0.5,
                "是否有保质期": True,
                "距离过期天数": 20,
            }
        ]
    )

    normalized = normalize_batch_columns(raw)

    assert BATCH_HAS_SHELF_LIFE_COLUMN in normalized.columns
    assert BATCH_EXPIRE_DAYS_COLUMN in normalized.columns
    assert bool(normalized.loc[0, BATCH_HAS_SHELF_LIFE_COLUMN]) is True
    assert normalized.loc[0, BATCH_EXPIRE_DAYS_COLUMN] == 20


def test_read_batch_upload_accepts_gbk_csv() -> None:
    uploaded = make_csv_upload(
        "物品名称,剩余量(%),周频次\n感冒药,50,0.5\n",
        encoding="gbk",
    )

    df = read_batch_upload(uploaded)

    assert df is not None
    assert df.loc[0, "物品名称"] == "感冒药"
    assert df.loc[0, "剩余量(%)"] == 50


def test_read_batch_upload_accepts_gb18030_csv() -> None:
    uploaded = make_csv_upload(
        "物品名称,剩余量百分比,每周使用次数\n𠀀测试物品,30,1\n",
        encoding="gb18030",
    )

    df = read_batch_upload(uploaded)

    assert df is not None
    assert df.loc[0, "物品名称"] == "𠀀测试物品"


def test_prepare_batch_upload_df_limits_large_files() -> None:
    raw = pd.DataFrame(
        {
            "物品名称": [f"物品{i}" for i in range(MAX_BATCH_UPLOAD_ROWS + 1)],
            "剩余量百分比": [50] * (MAX_BATCH_UPLOAD_ROWS + 1),
            "每周使用次数": [1] * (MAX_BATCH_UPLOAD_ROWS + 1),
        }
    )

    limited = prepare_batch_upload_df(raw)

    assert len(limited) == MAX_BATCH_UPLOAD_ROWS
    assert limited.iloc[-1]["物品名称"] == f"物品{MAX_BATCH_UPLOAD_ROWS - 1}"


def test_clean_html_removes_markdown_code_block_indentation() -> None:
    markup = """
        <div class="result-card">
            <h3>预测结果</h3>
        </div>
    """

    cleaned = clean_html(markup)

    assert cleaned.startswith("<div")
    assert "\n        <h3>" not in cleaned


def test_strip_yaml_frontmatter_for_docs_page() -> None:
    text = """---
title: "测试文档"
date: 2026-06-09
---

# 正文标题

正文内容。
"""

    stripped = strip_yaml_frontmatter(text)

    assert stripped.startswith("# 正文标题")
    assert "title:" not in stripped


def test_dark_theme_css_is_scoped_to_theme_bridge() -> None:
    source = (Path(__file__).resolve().parent.parent / "src" / "ui" / "styles.py").read_text(encoding="utf-8")

    assert "@media (prefers-color-scheme: dark)" not in source
    assert "[data-theme=\"dark\"]" not in source
    assert "[data-baseweb-theme=\"dark\"]" not in source
    assert "html.dorm-theme-dark" in source
    assert "dorm-theme-light" in source
    assert "stActiveTheme-" in source


def test_build_feedback_candidates_keeps_only_rejected_feedback(tmp_path: Path) -> None:
    feedback_path = tmp_path / "feedback.csv"
    pd.DataFrame(
        [
            {
                "item_name": "蛋白粉",
                "description": "训练后使用的补剂",
                "predicted_category": "其他用品",
                "corrected_category": "健康与补剂用品",
                "predicted_risk": "正常",
                "corrected_risk": "需要关注",
                "category_accepted": "不认可",
                "risk_accepted": "不认可",
            },
            {
                "item_name": "牙膏",
                "description": "每天早晚使用",
                "predicted_category": "洗漱用品",
                "corrected_category": "洗漱用品",
                "predicted_risk": "正常",
                "corrected_risk": "正常",
                "category_accepted": "认可",
                "risk_accepted": "认可",
            },
        ]
    ).to_csv(feedback_path, index=False, encoding="utf-8-sig")

    candidates = build_feedback_candidates(feedback_path)

    assert len(candidates) == 1
    assert candidates.loc[0, "item_name"] == "蛋白粉"
    assert candidates.loc[0, "category"] == "健康与补剂用品"
    assert candidates.loc[0, "risk_label"] == "需要关注"
    assert candidates.loc[0, "source"] == "user_feedback"
    assert candidates.loc[0, "label_source"] == "user_corrected"


def test_ensure_feedback_schema_migrates_legacy_headers(tmp_path: Path) -> None:
    feedback_path = tmp_path / "feedback.csv"
    pd.DataFrame(
        [
            {
                "trial_id": "trial-1",
                "timestamp": "2026-06-09T12:00:00",
                "item_name": "纸巾",
                "description": "快用完了",
                "predicted_category": "清洁日用",
                "corrected_category": "清洁日用",
                "predicted_risk": "建议补货",
                "corrected_risk": "建议补货",
            }
        ]
    ).to_csv(feedback_path, index=False, encoding="utf-8-sig")

    ensure_feedback_schema(feedback_path)
    migrated = pd.read_csv(feedback_path, encoding="utf-8-sig")

    assert migrated.columns.tolist() == FEEDBACK_COLUMNS
    assert migrated.loc[0, "item_name"] == "纸巾"
    assert "trial_id" not in migrated.columns


def test_append_feedback_record_uses_canonical_columns(tmp_path: Path) -> None:
    feedback_path = tmp_path / "feedback.csv"

    append_feedback_record(
        {
            "item_name": "数据线",
            "description": "外皮破损",
            "predicted_category": "电子配件",
            "corrected_category": "电子配件",
            "predicted_risk": "过期/损坏风险",
            "corrected_risk": "过期/损坏风险",
            "category_accepted": "认可",
            "risk_accepted": "认可",
        },
        feedback_path=feedback_path,
    )
    stored = pd.read_csv(feedback_path, encoding="utf-8-sig")

    assert stored.columns.tolist() == FEEDBACK_COLUMNS
    assert stored.loc[0, "item_name"] == "数据线"
    assert stored.loc[0, "predicted_risk"] == "过期/损坏风险"
    assert stored.loc[0, "timestamp"]


def test_export_trial_records_writes_docs_page_paths(tmp_path: Path) -> None:
    feedback_path = tmp_path / "feedback.csv"
    csv_path = tmp_path / "reports" / "user_trial_export.csv"
    md_path = tmp_path / "reports" / "user_trial_export.md"
    append_feedback_record(
        {
            "item_name": "牙膏",
            "description": "每天使用",
            "predicted_category": "洗漱用品",
            "corrected_category": "洗漱用品",
            "predicted_risk": "需要关注",
            "corrected_risk": "需要关注",
            "category_accepted": "认可",
            "risk_accepted": "认可",
        },
        feedback_path=feedback_path,
    )

    exported_csv, exported_md, row_count = export_trial_records(feedback_path, csv_path, md_path)

    assert Path(exported_csv).name == "user_trial_export.csv"
    assert Path(exported_md).name == "user_trial_export.md"
    assert row_count == 1
    assert pd.read_csv(csv_path, encoding="utf-8-sig").loc[0, "item_name"] == "牙膏"
    assert "牙膏" in md_path.read_text(encoding="utf-8")


def make_csv_upload(text: str, encoding: str) -> BytesIO:
    uploaded = BytesIO(text.encode(encoding))
    uploaded.name = "清单.csv"
    return uploaded
