from __future__ import annotations

from src.features import detect_damage, estimate_remaining_days, normalize_category, risk_rule_baseline


def test_detect_damage_respects_negative_phrases() -> None:
    assert detect_damage("充电线没有破损，正常使用") == 0
    assert detect_damage("感冒药未过期，包装完好") == 0
    assert detect_damage("充电线外皮破损，接触不良") == 1


def test_normalize_category_falls_back_from_text() -> None:
    assert normalize_category("", "蛋白粉", "训练后使用的补剂") == "健康与补剂用品"
    assert normalize_category("其他用品", "Type-C 数据线", "手机充电备用") == "电子配件"
    assert normalize_category("", "笔芯", "上课记笔记使用") == "学习用品"


def test_estimate_remaining_days_handles_boundaries() -> None:
    assert estimate_remaining_days(used_days=30, remaining_pct=0, weekly_use_count=7) == 0
    assert estimate_remaining_days(used_days=30, remaining_pct=50, weekly_use_count=7) == 30
    assert estimate_remaining_days(used_days=0, remaining_pct=20, weekly_use_count=14) >= 1


def test_risk_rule_baseline_prioritizes_expiry_and_damage() -> None:
    assert risk_rule_baseline({"has_shelf_life": 1, "days_to_expire": 20, "is_damaged": 0}) == "过期/损坏风险"
    assert risk_rule_baseline({"has_shelf_life": 0, "days_to_expire": 999, "is_damaged": 1}) == "过期/损坏风险"
    assert risk_rule_baseline({"remaining_pct": 20, "weekly_use_count": 14, "is_damaged": 0}) == "建议补货"
