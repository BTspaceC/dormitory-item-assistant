from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.external_data import map_jd_category, parse_jd_line


def test_map_jd_category_covers_each_project_label() -> None:
    cases = {
        ("生活电器", "生活电器@吸尘器"): "清洁日用",
        ("个护健康", "个护健康@电动牙刷"): "洗漱用品",
        ("个护健康", "个护健康@按摩器"): "健康与补剂用品",
        ("电子教育", "电子教育@电子词典"): "学习用品",
        ("数码配件", "数码配件@电池_充电器"): "电子配件",
        ("小说", "小说@侦探_推理"): "文体娱乐",
        ("大家电", "大家电@冰箱"): "其他用品",
    }
    for source_categories, expected in cases.items():
        assert map_jd_category(*source_categories) == expected


def test_map_jd_category_rejects_ambiguous_food() -> None:
    assert map_jd_category("水果", "水果@苹果") is None


def test_parse_jd_line_preserves_commas_inside_title() -> None:
    parsed = parse_jd_line("数码配件,数码配件@机身附件,USB 数据线, 1 米\n")
    assert parsed == ("数码配件", "数码配件@机身附件", "USB 数据线, 1 米")


def test_committed_external_sample_is_balanced_and_leak_free() -> None:
    project_root = Path(__file__).resolve().parents[1]
    data = pd.read_csv(project_root / "data" / "external" / "jd_category_samples.csv.gz")
    counts = data.groupby(["dataset_split", "category"]).size()

    assert len(data) == 49_000
    assert data["source_id"].is_unique
    assert set(counts.loc["external_train"]) == {6_000}
    assert set(counts.loc["external_eval"]) == {1_000}
