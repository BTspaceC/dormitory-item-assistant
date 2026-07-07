from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from src.ui.pages import batch_mode, single_mode


def test_single_prediction_reuses_injected_model_bundles(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_streamlit = SimpleNamespace(session_state={}, error=lambda _message: None)

    def fake_predict(input_data, model_bundles=None):
        captured["input"] = input_data
        captured["bundles"] = model_bundles
        return {"predicted_category": "电子配件"}

    monkeypatch.setattr(single_mode, "st", fake_streamlit)
    monkeypatch.setattr(single_mode, "predict", fake_predict)
    bundles = ({"model": "category"}, {"model": "risk"})

    single_mode.handle_prediction(
        {
            "item_name": "充电线",
            "description": "宿舍使用的充电线",
            "used_days": 30,
            "remaining_pct": 80,
            "weekly_use_count": 5.0,
            "user_count": 1,
            "is_shared": False,
            "has_shelf_life": False,
            "expiry_date": date.today(),
            "is_damaged": False,
        },
        (0, 0, 0, "test"),
        model_bundles=bundles,
    )

    assert captured["bundles"] is bundles
    assert fake_streamlit.session_state["last_result"]["predicted_category"] == "电子配件"


def test_batch_prediction_reuses_injected_model_bundles(monkeypatch) -> None:
    captured: dict[str, object] = {}
    bundles = ({"model": "category"}, {"model": "risk"})
    batch_df = pd.DataFrame([{"物品名称": "牙膏"}])

    def fake_predict_batch(df, bundles=None):
        captured["df"] = df
        captured["bundles"] = bundles
        return [{"物品名称": "牙膏", "处理状态": "已预测"}]

    monkeypatch.setattr(batch_mode, "predict_batch", fake_predict_batch)

    result = batch_mode.handle_batch_prediction(
        batch_df,
        (0, 0, 0, "test"),
        model_bundles=bundles,
    )

    assert captured["bundles"] is bundles
    assert result["skipped_blank_count"] == 0
    assert result["result_df"].loc[0, "处理状态"] == "已预测"
