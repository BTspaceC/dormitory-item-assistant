import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta
import html
from typing import Any

from src.features import CATEGORIES, RISK_LABELS, RISK_CARD_CLASS, EXAMPLES
from src.predict import predict, make_prediction_input, load_models
from src.merge_feedback import append_feedback_record, ensure_feedback_schema, export_trial_records
from src.ui.utils import render_html, clean_html, format_percent, render_section_header

def render_flow_steps(steps: list[tuple[str, str]]) -> None:
    items = "".join(
        f"<div class='flow-step'><strong><span class='flow-step-num'>{i}</span>{html.escape(title)}</strong><span>{html.escape(caption)}</span></div>"
        for i, (title, caption) in enumerate(steps, 1)
    )
    render_html(f"<div class='flow-steps'>{items}</div>")

def render_example_loader() -> None:
    with st.container(border=True):
        render_section_header("演示案例", "适合交付演示时快速填入一组典型物品信息。")
        left, right = st.columns([4, 1])
        with left:
            choice = st.selectbox("演示测试案例", list(EXAMPLES.keys()))
        with right:
            st.write("")
            st.write("")
            if st.button("载入案例", width='stretch', type="primary"):
                example = EXAMPLES[choice]
                for key, value in example.items():
                    if key == "expiry_days":
                        st.session_state["expiry_date"] = date.today() + timedelta(days=int(value))
                    elif key == "is_damaged":
                        st.session_state["is_damaged_input"] = value
                    else:
                        st.session_state[key] = value
                st.rerun()

def render_prediction_form() -> dict[str, Any]:
    with st.form("prediction_form"):
        render_section_header("物品信息", "尽量填写用途、剩余量和使用频率，系统会据此判断状态风险。")
        left, right = st.columns(2)
        with left:
            item_name = st.text_input("物品名称", key="item_name")
            description = st.text_area("物品描述", key="description", height=116)
            used_days = st.number_input("已使用天数", min_value=0, max_value=1000, step=1, key="used_days")
            remaining_pct = st.number_input("剩余量百分比", min_value=0, max_value=100, step=1, key="remaining_pct")
        with right:
            weekly_use_count = st.number_input("每周使用次数", min_value=0.0, max_value=50.0, step=0.5, key="weekly_use_count")
            user_count = st.number_input("使用人数", min_value=1, max_value=10, step=1, key="user_count")
            is_shared = st.checkbox("是否共用", key="is_shared")
            has_shelf_life = st.checkbox("是否有保质期/有效期", key="has_shelf_life")
            expiry_date = None
            if has_shelf_life:
                expiry_date = st.date_input("保质期/有效期日期", key="expiry_date")
            is_damaged = st.checkbox("已破损/部分失效", value=bool(st.session_state.get("is_damaged_input", 0)))
            st.session_state["is_damaged_input"] = 1 if is_damaged else 0

        submitted = st.form_submit_button("开始预测", type="primary", width='stretch')
        return {
            "submitted": submitted,
            "item_name": item_name,
            "description": description,
            "used_days": used_days,
            "remaining_pct": remaining_pct,
            "weekly_use_count": weekly_use_count,
            "user_count": user_count,
            "is_shared": is_shared,
            "has_shelf_life": has_shelf_life,
            "expiry_date": expiry_date,
            "is_damaged": is_damaged,
        }

def validate_input(values: dict[str, Any]) -> list[str]:
    errors = []
    if not values["item_name"].strip():
        errors.append("物品名称不能为空。")
    if values["has_shelf_life"] and not values["expiry_date"]:
        errors.append("请提供有效期日期。")
    return errors

def handle_prediction(values: dict[str, Any], signature: tuple[int, int, int, str]) -> None:
    errors = validate_input(values)
    if errors:
        for error in errors:
            st.error(error)
        return

    input_data = make_prediction_input(
        item_name=values["item_name"],
        description=values["description"],
        used_days=values["used_days"],
        remaining_pct=values["remaining_pct"],
        weekly_use_count=values["weekly_use_count"],
        user_count=values["user_count"],
        is_shared=values["is_shared"],
        has_shelf_life=values["has_shelf_life"],
        expiry_date=values["expiry_date"],
        is_damaged=values["is_damaged"],
    )

    try:
        model_bundles = load_models()
    except FileNotFoundError:
        model_bundles = None

    result = predict(input_data, model_bundles=model_bundles)
    st.session_state["last_result"] = result
    st.session_state["last_input"] = input_data

def save_user_feedback(input_data: Any, result: dict[str, Any]) -> None:
    record = {
        "item_name": input_data.item_name,
        "description": input_data.description,
        "used_days": input_data.used_days,
        "remaining_pct": input_data.remaining_pct,
        "weekly_use_count": input_data.weekly_use_count,
        "user_count": input_data.user_count,
        "is_shared": input_data.is_shared,
        "has_shelf_life": input_data.has_shelf_life,
        "days_to_expire": input_data.days_to_expire,
        "is_damaged": input_data.is_damaged,
        "predicted_category": result["predicted_category"],
        "corrected_category": st.session_state.get("category_feedback", result["predicted_category"]),
        "predicted_risk": result["predicted_risk"],
        "corrected_risk": st.session_state.get("risk_feedback", result["predicted_risk"]),
        "category_accepted": "认可" if st.session_state.get("category_accepted_radio") == "准了" else "不认可",
        "risk_accepted": "认可" if st.session_state.get("risk_accepted_radio") == "准了" else "不认可",
    }
    append_feedback_record(record)
    st.success("反馈已保存！感谢您的协助。")

def render_result_cards(result: dict[str, Any]) -> None:
    remaining_display = (
        "需人工检查 / 不适用"
        if result["predicted_risk"] == "过期/损坏风险"
        else f"{result['estimated_remaining_days']} 天"
    )
    cards = [
        ("预测类别", result["predicted_category"], "模型 1 输出", ""),
        ("风险使用类别", result["risk_category"], "模型 2 实际输入", ""),
        ("状态风险", result["predicted_risk"], "当前优先处理等级", RISK_CARD_CLASS.get(result["predicted_risk"], "")),
        ("类别把握", format_percent(result.get("category_confidence", 0.0)), "建议结合实际确认", ""),
        ("风险把握", format_percent(result.get("risk_confidence", 0.0)), "状态判断置信参考", ""),
        ("预计剩余可用", remaining_display, "过期/损坏风险时不估算天数", ""),
    ]
    card_html = "".join(
        clean_html(
            f"""
            <div class="result-card {html.escape(extra_class)}">
                <div class="label">{html.escape(label)}</div>
                <div class="value">{html.escape(str(value))}</div>
                <div class="hint">{html.escape(hint)}</div>
            </div>
            """
        )
        for label, value, hint, extra_class in cards
    )
    render_html(f"<div class='result-card-grid'>{card_html}</div>")

def render_probability_chart(probabilities: dict[str, float], title: str, color_scheme: str) -> None:
    if not probabilities:
        return
    df = pd.DataFrame(list(probabilities.items()), columns=["Category", "Probability"])
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Probability:Q", axis=alt.Axis(format="%"), title="置信度"),
            y=alt.Y("Category:N", sort="-x", title=""),
            color=alt.Color("Category:N", scale=alt.Scale(scheme=color_scheme), legend=None),
            tooltip=["Category", alt.Tooltip("Probability:Q", format=".1%")],
        )
        .properties(title=title, height=max(150, len(df) * 30))
    )
    st.altair_chart(chart, width='stretch')

def render_result_and_feedback(signature: tuple[int, int, int, str]) -> None:
    result = st.session_state["last_result"]
    last_input = st.session_state["last_input"]

    render_result_cards(result)

    if result.get("needs_category_review") or result.get("needs_risk_review"):
        render_html(
            """
            <div class="risk-alert risk-watch">
                <strong>💡 模型把握度较低，需要人工核对</strong>
                部分判断的置信度低于 50%，建议您在下方“结果核对与反馈”中提供正确的分类或状态。
            </div>
            """
        )
    else:
        render_html(
            f"""
            <div class="risk-alert {html.escape(RISK_CARD_CLASS.get(result['predicted_risk'], ''))}">
                <strong>{html.escape(result['predicted_risk'])}</strong>
                {html.escape(result['advice'])}
            </div>
            """
        )

    if result.get("risk_reasons"):
        reasons_html = "".join(f"<div class='reason-item'>• {html.escape(r)}</div>" for r in result["risk_reasons"])
        render_html(f"<div class='reason-list'>{reasons_html}</div>")

    st.divider()
    left, right = st.columns(2)
    with left:
        render_probability_chart(result.get("category_probabilities", {}), "类别预测分布", "tealblues")
    with right:
        render_probability_chart(result.get("risk_probabilities", {}), "风险评估分布", "oranges")

    st.divider()
    st.subheader("结果核对与反馈")
    st.caption("帮助我们改进模型。如果不准，请提供正确的分类或状态。")
    if not st.session_state.get("_feedback_schema_checked"):
        ensure_feedback_schema()
        st.session_state["_feedback_schema_checked"] = True

    with st.form("feedback_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.radio("类别判断准吗？", ["准了", "不准"], horizontal=True, key="category_accepted_radio")
            st.selectbox("实际类别应该是", CATEGORIES, index=CATEGORIES.index(result["predicted_category"]) if result["predicted_category"] in CATEGORIES else 0, key="category_feedback")
        with col2:
            st.radio("状态评估准吗？", ["准了", "不准"], horizontal=True, key="risk_accepted_radio")
            st.selectbox("实际状态应该是", RISK_LABELS, index=RISK_LABELS.index(result["predicted_risk"]) if result["predicted_risk"] in RISK_LABELS else 0, key="risk_feedback")
        if st.form_submit_button("提交反馈", width='stretch'):
            save_user_feedback(last_input, result)

    st.divider()
    st.subheader("试用数据导出")
    if st.button("导出试用记录", width='stretch'):
        csv_path, md_path, row_count = export_trial_records()
        st.success(f"已导出 {row_count} 条记录。")
        st.caption(f"CSV：{csv_path}")
        st.caption(f"Markdown：{md_path}")

def render_empty_result_panel() -> None:
    with st.container(border=True):
        st.markdown("### 等待预测结果")
        st.caption(
            "先选择一个演示案例，或者填写自己的宿舍物品信息。点击“开始预测”后，这里会展示类别、风险等级、判断依据和用户反馈入口。"
        )

def render_single_mode(signature: tuple[int, int, int, str]) -> None:
    render_section_header(
        "单件预测",
        "可以先载入演示案例，也可以直接填写用户自己的宿舍物品信息。",
        "工具入口",
    )
    render_flow_steps(
        [
            ("选择案例", "快速填入一组典型物品"),
            ("填写信息", "补充剩余量、频率和状态"),
            ("查看结果", "确认风险并保存反馈"),
        ]
    )
    render_example_loader()
    form_values = render_prediction_form()

    if form_values["submitted"]:
        handle_prediction(form_values, signature)

    st.divider()
    render_section_header("预测结果", "集中展示风险等级判定、预测明细、图表统计和反馈入口。")
    if "last_result" in st.session_state and st.session_state.get("last_input"):
        render_result_and_feedback(signature)
    else:
        render_empty_result_panel()
