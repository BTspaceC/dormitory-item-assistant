from __future__ import annotations

from datetime import date
from pathlib import Path
import pandas as pd
from src.features import (
    category_rule_override,
    detect_damage,
    DOCS_OPTIONS,
    estimate_remaining_days,
    hybrid_risk_decision,
    normalize_category,
    risk_rule_baseline,
    parse_weekly_use_count,
    parse_user_count,
    parse_is_shared,
    parse_shelf_life,
)


def test_detect_damage_respects_negative_phrases() -> None:
    assert detect_damage("充电线没有破损，正常使用") == 0
    assert detect_damage("感冒药未过期，包装完好") == 0
    assert detect_damage("充电线外皮破损，接触不良") == 1
    assert detect_damage("没有接触不良且无破损") == 0


def test_normalize_category_falls_back_from_text() -> None:
    assert normalize_category("", "蛋白粉", "训练后使用的补剂") == "健康与补剂用品"
    assert normalize_category("其他用品", "Type-C 数据线", "手机充电备用") == "电子配件"
    assert normalize_category("", "笔芯", "上课记笔记使用") == "学习用品"
    assert normalize_category("其他用品", "抽纸", "") == "清洁日用"
    assert normalize_category("其他用品", "湿纸巾", "") == "清洁日用"
    assert normalize_category("其他用品", "卷筒纸", "") == "清洁日用"
    assert normalize_category("其他用品", "草稿纸", "") == "学习用品"
    assert normalize_category("其他用品", "篮球", "平时拿来体育运动") == "文体娱乐"
    assert normalize_category("", "哑铃", "健身器材") == "文体娱乐"


def test_category_rule_override_uses_only_high_precision_terms() -> None:
    assert category_rule_override("备用药盒", "宿舍收纳常用药") == "健康与补剂用品"
    assert category_rule_override("Type-C 充电线", "") == "电子配件"
    assert category_rule_override("电子书阅读器", "") is None
    assert category_rule_override("完全陌生的神秘东西", "无法识别") == "其他用品"


def test_docs_menu_only_references_existing_files() -> None:
    project_root = Path(__file__).resolve().parents[1]
    assert all((project_root / relative_path).is_file() for relative_path in DOCS_OPTIONS.values())


def test_estimate_remaining_days_handles_boundaries() -> None:
    assert estimate_remaining_days(used_days=30, remaining_pct=0, weekly_use_count=7) == 0
    assert estimate_remaining_days(used_days=30, remaining_pct=50, weekly_use_count=7) == 30
    assert estimate_remaining_days(used_days=0, remaining_pct=20, weekly_use_count=14) >= 1


def test_risk_rule_baseline_prioritizes_expiry_and_damage() -> None:
    assert risk_rule_baseline({"has_shelf_life": 1, "days_to_expire": 20, "is_damaged": 0}) == "过期/损坏风险"
    assert risk_rule_baseline({"has_shelf_life": 0, "days_to_expire": 999, "is_damaged": 1}) == "过期/损坏风险"
    assert risk_rule_baseline({"remaining_pct": 20, "weekly_use_count": 14, "is_damaged": 0}) == "建议补货"


def test_hybrid_risk_decision_uses_hard_safety_signals() -> None:
    row = {"has_shelf_life": 1, "days_to_expire": 20, "is_damaged": 0, "remaining_pct": 80}
    assert hybrid_risk_decision(row, "正常") == ("过期/损坏风险", "安全硬规则")

    expired = {"has_shelf_life": 1, "days_to_expire": 0, "is_damaged": 0, "remaining_pct": 80}
    assert hybrid_risk_decision(expired, "正常") == ("过期/损坏风险", "安全硬规则")


def test_hybrid_risk_decision_prioritizes_replenishment() -> None:
    row = {
        "has_shelf_life": 0,
        "days_to_expire": 999,
        "is_damaged": 0,
        "remaining_pct": 15,
        "weekly_use_count": 14,
    }
    assert hybrid_risk_decision(row, "需要关注") == ("建议补货", "补货阈值规则")


def test_hybrid_risk_decision_blocks_unsubstantiated_danger() -> None:
    row = {
        "has_shelf_life": 0,
        "days_to_expire": 999,
        "is_damaged": 0,
        "remaining_pct": 60,
        "weekly_use_count": 7,
    }
    assert hybrid_risk_decision(row, "过期/损坏风险") == ("需要关注", "安全阈值校准")

    far_from_expiry = {**row, "has_shelf_life": 1, "days_to_expire": 365}
    assert hybrid_risk_decision(far_from_expiry, "过期/损坏风险") == ("需要关注", "安全阈值校准")


def test_hybrid_risk_decision_calibrates_non_expiring_damage() -> None:
    row = {
        "has_shelf_life": 0,
        "days_to_expire": 999,
        "is_damaged": 1,
        "remaining_pct": 60,
        "weekly_use_count": 7,
    }
    assert hybrid_risk_decision(row, "过期/损坏风险") == ("需要关注", "损坏等级校准")


def test_parse_weekly_use_count() -> None:
    # Numeric values
    assert parse_weekly_use_count(3.5) == 3.5
    assert parse_weekly_use_count("2.5") == 2.5
    # Chinese phrase mappings
    assert parse_weekly_use_count("每周2次") == 2.0
    assert parse_weekly_use_count("每天2次") == 14.0
    assert parse_weekly_use_count("每天1-2次") == 10.5
    assert parse_weekly_use_count("每天") == 7.0
    assert parse_weekly_use_count("隔天") == 3.5
    assert parse_weekly_use_count("偶尔") == 0.5
    assert parse_weekly_use_count(None) == 1.0
    assert parse_weekly_use_count("每月4次") == 1.0


def test_parse_user_count() -> None:
    assert parse_user_count(4) == 4
    assert parse_user_count("3") == 3
    assert parse_user_count("2人") == 2
    assert parse_user_count("寝室合用") == 4
    assert parse_user_count(None) == 1
    assert parse_user_count("abc") == 1


def test_parse_is_shared() -> None:
    assert parse_is_shared(True) == 1
    assert parse_is_shared(False) == 0
    assert parse_is_shared("是") == 1
    assert parse_is_shared("否") == 0
    assert parse_is_shared("全寝共用") == 1
    assert parse_is_shared("个人使用") == 0


def test_parse_shelf_life() -> None:
    today = date(2026, 6, 9)
    # Expiry date object
    assert parse_shelf_life(date(2026, 6, 19), today=today) == (1, 10)
    # Expiry string
    assert parse_shelf_life("2026-06-14", today=today) == (1, 5)
    # Numeric days to expire
    assert parse_shelf_life(30, today=today) == (1, 30)
    # Months text
    assert parse_shelf_life("还有3个月", today=today) == (1, 90)
    # No shelf life
    assert parse_shelf_life("无", today=today) == (0, 999)
    assert parse_shelf_life(None, today=today) == (0, 999)
