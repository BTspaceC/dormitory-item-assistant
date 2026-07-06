from __future__ import annotations

import argparse
import hashlib
import random
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

try:
    from .features import CATEGORIES
except ImportError:  # pragma: no cover - supports direct script execution
    from features import CATEGORIES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "external" / "jd_category_samples.csv.gz"
JD_DATASET_URL = "https://gitee.com/KunLiu_kk/jd-dataset"
JD_DATASET_COMMIT = "2931aecb22e9decfe7cea85f292690eebd3adcb0"
JD_DATASET_LICENSE = "MulanPSL-2.0"

WASH_CATEGORIES = {
    "个护健康@剃须刀",
    "个护健康@卷_直发器",
    "个护健康@冲牙器",
    "个护健康@理发器",
    "个护健康@美容器",
    "个护健康@潮流护理电器",
    "个护健康@洁面仪",
    "个护健康@剃_脱毛器",
    "个护健康@补水_蒸脸仪",
    "个护健康@电吹风",
    "个护健康@离子_直发梳",
    "个护健康@电动牙刷",
    "个护健康@黑头仪",
    "个护健康@电动牙刷头",
    "个护健康@电动鼻毛修剪器",
}

HEALTH_CATEGORIES = {
    "个护健康@按摩器",
    "个护健康@电子秤",
    "个护健康@按摩椅",
    "个护健康@其它健康电器",
    "个护健康@足浴盆",
    "个护健康@足疗机",
    "个护健康@眼部按摩仪",
}

CLEANING_CATEGORIES = {
    "生活电器@除螨仪",
    "生活电器@干衣机",
    "生活电器@毛球修剪器",
    "生活电器@除湿机",
    "生活电器@蒸汽_电动拖把",
    "生活电器@扫地机器人",
    "生活电器@空气净化器",
    "生活电器@吸尘器",
    "生活电器@擦地_擦窗机器人",
    "生活电器@家用洗地机",
    "生活电器@衣物消毒机",
}

OTHER_PRODUCT_CATEGORIES = {
    "摄影摄像",
    "智能设备",
    "家庭影音",
    "家电配件",
    "厨房小电",
    "厨卫大电",
    "大家电",
    "商用电器",
}

STUDY_BOOK_CATEGORIES = {
    "科技",
    "计算机与互联网",
    "管理",
    "经济管理",
    "投资理财",
}


def map_jd_category(category_2: str, category_3: str) -> str | None:
    """Map only semantically defensible JD groups into this project's labels."""
    if category_3 in CLEANING_CATEGORIES:
        return "清洁日用"
    if category_3 in WASH_CATEGORIES:
        return "洗漱用品"
    if category_3 in HEALTH_CATEGORIES:
        return "健康与补剂用品"
    if category_2 == "电子教育" or category_2 in STUDY_BOOK_CATEGORIES:
        return "学习用品"
    if category_2 in {"数码配件", "影音娱乐"}:
        return "电子配件"
    if category_2 == "小说":
        return "文体娱乐"
    if category_2 in OTHER_PRODUCT_CATEGORIES:
        return "其他用品"
    return None


def parse_jd_line(line: str) -> tuple[str, str, str] | None:
    parts = line.rstrip("\r\n").split(",", 2)
    if len(parts) != 3:
        return None
    category_2, category_3, title = (part.strip() for part in parts)
    title = re.sub(r"\s+", " ", title).strip()[:180]
    if not category_2 or not category_3 or len(title) < 2:
        return None
    return category_2, category_3, title


def build_external_dataset(
    input_files: list[Path],
    *,
    samples_per_class: int = 7000,
    eval_per_class: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """Create a balanced, deduplicated sample with reservoir sampling."""
    if not 0 < eval_per_class < samples_per_class:
        raise ValueError("eval_per_class must be between 1 and samples_per_class - 1")

    rng = random.Random(seed)
    reservoirs: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_counts: dict[str, int] = defaultdict(int)
    seen_titles: set[str] = set()

    for path in input_files:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                parsed = parse_jd_line(line)
                if parsed is None:
                    continue
                category_2, category_3, title = parsed
                category = map_jd_category(category_2, category_3)
                if category is None:
                    continue
                title_key = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", title.casefold())
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                source_id = hashlib.sha256(title_key.encode("utf-8")).hexdigest()[:16]
                record = {
                    "source_id": source_id,
                    "item_name": title,
                    "user_description": "",
                    "category": category,
                    "source_category_2": category_2,
                    "source_category_3": category_3,
                    "source": "jd-dataset",
                }
                seen_counts[category] += 1
                reservoir = reservoirs[category]
                if len(reservoir) < samples_per_class:
                    reservoir.append(record)
                else:
                    replacement = rng.randrange(seen_counts[category])
                    if replacement < samples_per_class:
                        reservoir[replacement] = record

    missing = {
        category: len(reservoirs[category])
        for category in CATEGORIES
        if len(reservoirs[category]) < samples_per_class
    }
    if missing:
        raise ValueError(f"Insufficient mapped rows for balanced sample: {missing}")

    rows: list[dict[str, str]] = []
    for category in CATEGORIES:
        reservoir = reservoirs[category]
        rng.shuffle(reservoir)
        for index, record in enumerate(reservoir):
            rows.append(
                {
                    **record,
                    "dataset_split": "external_eval" if index < eval_per_class else "external_train",
                }
            )
    result = pd.DataFrame(rows)
    return result.sort_values(["dataset_split", "category", "source_id"]).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a balanced category sample from extracted JD dataset text files.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Extracted JD sample_*.txt files")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--samples-per-class", type=int, default=7000)
    parser.add_argument("--eval-per-class", type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = build_external_dataset(
        args.inputs,
        samples_per_class=args.samples_per_class,
        eval_per_class=args.eval_per_class,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False, encoding="utf-8", compression="gzip")
    print(f"saved={args.output}")
    print(dataset.groupby(["dataset_split", "category"]).size().to_string())


if __name__ == "__main__":
    main()
