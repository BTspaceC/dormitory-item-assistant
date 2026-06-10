from __future__ import annotations

import pandas as pd
import pytest
from src.predict import predict, make_prediction_input, load_models
from src.features import BATCH_HAS_SHELF_LIFE_COLUMN, BATCH_EXPIRE_DAYS_COLUMN

def test_make_prediction_input_defaults() -> None:
    inp = make_prediction_input(
        item_name="洗面奶",
        description="洗脸用的",
        used_days=None,
        remaining_pct=None,
        weekly_use_count=None,
        user_count=None,
        is_shared=None,
        has_shelf_life=None,
        expiry_date=None,
        is_damaged=None
    )
    assert inp.item_name == "洗面奶"
    assert inp.description == "洗脸用的"
    assert inp.used_days == 30
    assert inp.remaining_pct == 50.0
    assert inp.weekly_use_count == 1.0
    assert inp.user_count == 1
    assert inp.is_shared == 0
    assert inp.has_shelf_life == 0
    assert inp.is_damaged == 0

def test_predict_single_item_fallback() -> None:
    # Test predict with None models to ensure baseline fallback logic executes
    inp = make_prediction_input(
        item_name="感冒冲剂",
        description="感冒药",
        used_days=10,
        remaining_pct=90,
        weekly_use_count=1,
        user_count=1,
        is_shared=False,
        has_shelf_life=True,
        expiry_date=None,
        is_damaged=False
    )
    inp.days_to_expire = 15  # Near expiry
    res = predict(inp, model_bundles=None)
    assert res["predicted_category"] == "健康与补剂用品"
    assert res["predicted_risk"] == "过期/损坏风险"

def test_predict_batch_standard_and_none_values() -> None:
    df = pd.DataFrame([
        {
            "物品名称": "抽纸",
            "用户描述": "放桌上用",
            "使用天数": None,
            "剩余量(%)": 20,
            "周频次": 14,
            "使用人数": 2,
            "是否共用": True,
            BATCH_HAS_SHELF_LIFE_COLUMN: False,
            BATCH_EXPIRE_DAYS_COLUMN: None,
            "是否破损": False
        },
        {
            "物品名称": "",  # Empty name row should be skipped
            "用户描述": "无用行",
            "使用天数": 10,
            "剩余量(%)": 50,
            "周频次": 1,
            "使用人数": 1,
            "是否共用": False,
            BATCH_HAS_SHELF_LIFE_COLUMN: False,
            BATCH_EXPIRE_DAYS_COLUMN: None,
            "是否破损": False
        }
    ])
    
    # Try loading actual model bundle if available
    try:
        models = load_models()
    except FileNotFoundError:
        models = None
        
    from src.ui.pages.batch_mode import predict_batch
    results = predict_batch(df, bundles=models)
    
    assert len(results) == 1
    assert results[0]["物品名称"] == "抽纸"
    assert results[0]["处理状态"] == "已预测"
    assert "预测类别" in results[0]
    assert "状态风险" in results[0]
