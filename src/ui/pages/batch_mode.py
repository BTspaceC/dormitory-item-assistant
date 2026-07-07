import streamlit as st
import pandas as pd
import html
from typing import Any

from src.features import BATCH_HAS_SHELF_LIFE_COLUMN, BATCH_EXPIRE_DAYS_COLUMN, MAX_BATCH_UPLOAD_ROWS
from src.predict import predict, make_prediction_input
from src.ui.utils import render_html, clean_html, render_section_header
from src.ui.pages.single_mode import render_flow_steps

CSV_UPLOAD_ENCODINGS = ["utf-8-sig", "gb18030", "gbk"]
REQUIRED_BATCH_UPLOAD_COLUMNS = ["物品名称", "剩余量(%)", "周频次"]

def read_batch_upload(uploaded_file: Any) -> pd.DataFrame | None:
    try:
        if uploaded_file.name.lower().endswith(".xlsx"):
            uploaded_file.seek(0)
            return prepare_batch_upload_df(pd.read_excel(uploaded_file))
        last_error: Exception | None = None
        for encoding in CSV_UPLOAD_ENCODINGS:
            uploaded_file.seek(0)
            try:
                return prepare_batch_upload_df(pd.read_csv(uploaded_file, encoding=encoding))
            except UnicodeDecodeError as exc:
                last_error = exc
        if last_error:
            raise last_error
    except Exception as exc:  # noqa: BLE001 - keep upload errors friendly in the UI.
        st.warning(f"清单读取失败：{exc}")
        return None

def prepare_batch_upload_df(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_batch_columns(df)
    missing_columns = [column for column in REQUIRED_BATCH_UPLOAD_COLUMNS if column not in df.columns]
    if missing_columns:
        st.warning(f"上传清单缺少关键列：{'、'.join(missing_columns)}。已载入表格，请在预测前补齐。")
    if len(df) > MAX_BATCH_UPLOAD_ROWS:
        st.warning(f"为保证页面流畅，单次最多载入 {MAX_BATCH_UPLOAD_ROWS} 行，已自动保留前 {MAX_BATCH_UPLOAD_ROWS} 行。")
        df = df.head(MAX_BATCH_UPLOAD_ROWS).copy()
    return df

def normalize_batch_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [str(c).strip() for c in normalized.columns]
    rename_map = {}
    if "物品描述" in normalized.columns and "用户描述" not in normalized.columns:
        rename_map["物品描述"] = "用户描述"
    if "是否有保质期" in normalized.columns and BATCH_HAS_SHELF_LIFE_COLUMN not in normalized.columns:
        rename_map["是否有保质期"] = BATCH_HAS_SHELF_LIFE_COLUMN
    if "距离过期天数" in normalized.columns and BATCH_EXPIRE_DAYS_COLUMN not in normalized.columns:
        rename_map["距离过期天数"] = BATCH_EXPIRE_DAYS_COLUMN
    if "剩余量百分比" in normalized.columns and "剩余量(%)" not in normalized.columns:
        rename_map["剩余量百分比"] = "剩余量(%)"
    if "每周使用次数" in normalized.columns and "周频次" not in normalized.columns:
        rename_map["每周使用次数"] = "周频次"
    if rename_map:
        normalized = normalized.rename(columns=rename_map)

    # Cast columns to pandas nullable dtypes to prevent literal 'None' values and ensure checkboxes/inputs render properly
    type_map = {
        "物品名称": "string",
        "用户描述": "string",
        "使用天数": "Int64",
        "剩余量(%)": "Int64",
        "周频次": "Float64",
        "使用人数": "Int64",
        "是否共用": "boolean",
        BATCH_HAS_SHELF_LIFE_COLUMN: "boolean",
        BATCH_EXPIRE_DAYS_COLUMN: "Int64",
        "是否破损": "boolean"
    }
    for col, dtype in type_map.items():
        if col in normalized.columns:
            try:
                s = normalized[col].copy()
                if s.dtype == object or s.dtype == 'string':
                    s = s.map(lambda val: pd.NA if (pd.isna(val) or str(val).strip().lower() in ("nan", "none", "null", "<na>", "")) else val)
                normalized[col] = s.astype(dtype)
            except Exception:
                pass
    return normalized

def safe_str(val, default="") -> str:
    if pd.isna(val) or val is None:
        return default
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null", ""):
        return default
    return s

def safe_int(val, default=0) -> int:
    if pd.isna(val) or val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0) -> float:
    if pd.isna(val) or val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_bool(val, default=False) -> bool:
    if pd.isna(val) or val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("true", "1", "yes", "y", "t", "checked", "是"):
        return True
    if s in ("false", "0", "no", "n", "f", "unchecked", "否"):
        return False
    try:
        return bool(float(val))
    except (ValueError, TypeError):
        return default

def predict_batch(df: pd.DataFrame, bundles=None) -> list[dict]:
    results = []
    for idx, row in df.iterrows():
        name = safe_str(row.get('物品名称'))
        if not name:
            continue
        
        input_data = make_prediction_input(
            item_name=name,
            description=safe_str(row.get('用户描述', '')),
            used_days=safe_int(row.get('使用天数'), 30),
            remaining_pct=safe_float(row.get('剩余量(%)'), 50.0),
            weekly_use_count=safe_float(row.get('周频次'), 1.0),
            user_count=safe_int(row.get('使用人数'), 1),
            is_shared=safe_bool(row.get('是否共用'), False),
            has_shelf_life=safe_bool(row.get(BATCH_HAS_SHELF_LIFE_COLUMN), False),
            expiry_date=None,
            is_damaged=safe_bool(row.get('是否破损'), False)
        )
        if input_data.has_shelf_life:
            input_data.days_to_expire = safe_int(row.get(BATCH_EXPIRE_DAYS_COLUMN), 999)
        
        res = predict(input_data, model_bundles=bundles)
        
        results.append({
            "物品名称": name,
            "处理状态": "已预测",
            "预测类别": res["predicted_category"],
            "状态风险": res["predicted_risk"],
            "决策来源": res.get("risk_decision_source", "风险模型"),
            "把握程度": f"类别 {res['category_confidence']:.0%} | 风险 {res['risk_confidence']:.0%}",
            "原因摘要": res["risk_reasons"][0] if res["risk_reasons"] else "",
            "建议摘要": res["advice"],
            "完整原因": "\n".join(res["risk_reasons"]),
            "完整建议": res["advice"],
            "有效期显示": str(input_data.days_to_expire) if input_data.has_shelf_life else "无",
        })
    return results

def handle_batch_prediction(
    batch_df: pd.DataFrame,
    signature: tuple[int, int, int, str],
    model_bundles: tuple[dict[str, Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    results = predict_batch(batch_df, bundles=model_bundles)
    result_df = pd.DataFrame(results)
    skipped_blank_count = len(batch_df) - len(result_df)
    return {"result_df": result_df, "skipped_blank_count": skipped_blank_count}

def render_batch_summary_cards(result_df: pd.DataFrame) -> None:
    predicted_df = result_df[result_df["处理状态"] == "已预测"] if "处理状态" in result_df.columns else pd.DataFrame()
    exception_count = int(len(result_df) - len(predicted_df))
    risk_counts = predicted_df["状态风险"].value_counts().to_dict() if not predicted_df.empty else {}
    cards = [
        ("成功预测", len(predicted_df), "已进入图表统计"),
        ("需优先处理", risk_counts.get("过期/损坏风险", 0) + risk_counts.get("建议补货", 0), "过期/损坏或建议补货"),
        ("需要关注", risk_counts.get("需要关注", 0), "建议近期查看"),
        ("异常/待补充", exception_count, "未进入有效预测统计"),
    ]
    card_html = "".join(
        clean_html(
            f"""
            <div class="batch-summary-card">
                <div class="label">{html.escape(label)}</div>
                <div class="value">{html.escape(str(value))}</div>
                <div class="hint">{html.escape(hint)}</div>
            </div>
            """
        )
        for label, value, hint in cards
    )
    render_html(f"<div class='batch-summary-grid'>{card_html}</div>")

def render_batch_results(batch_result: Any) -> None:
    if isinstance(batch_result, dict):
        result_df = batch_result.get("result_df", pd.DataFrame())
        skipped_blank_count = int(batch_result.get("skipped_blank_count", 0) or 0)
    else:
        result_df = batch_result
        skipped_blank_count = 0
    if result_df.empty:
        if skipped_blank_count:
            st.info(f"已自动跳过 {skipped_blank_count} 条空白行。")
        return
    display_columns = ["物品名称", "处理状态", "预测类别", "状态风险", "把握程度", "原因摘要", "建议摘要"]
    render_section_header("批量预测结果", "先看风险摘要，再查看图表和明细表格。")
    if skipped_blank_count:
        st.info(f"已自动跳过 {skipped_blank_count} 条空白行。")
    render_batch_summary_cards(result_df)
    st.dataframe(result_df[display_columns], hide_index=True, width='stretch')

def render_batch_mode(
    signature: tuple[int, int, int, str],
    model_bundles: tuple[dict[str, Any], dict[str, Any]] | None = None,
) -> None:
    render_section_header(
        "批量清单",
        "适合交付试用时一次录入 5-8 个物品，也可以上传 CSV / Excel 宿舍清单。",
        "批量预测",
    )
    render_flow_steps(
        [
            ("上传清单", "支持 CSV、Excel，最多载入 500 行"),
            ("检查表格", "补齐物品名称、剩余量和使用频率"),
            ("批量预测", "按风险排序并导出结果"),
        ]
    )
    with st.container(border=True):
        render_section_header("导入清单", "CSV 支持 utf-8-sig、gb18030、gbk；Excel 使用 .xlsx。")
        uploaded_file = st.file_uploader(
            "上传宿舍用品清单（CSV 或 Excel）",
            type=["csv", "xlsx"],
            help="文件至少包含物品名称、剩余量百分比、每周使用次数；其他字段可选。",
        )
    if uploaded_file is not None:
        upload_signature = (uploaded_file.name, getattr(uploaded_file, "size", None))
        if st.session_state.get("batch_uploaded_signature") != upload_signature:
            uploaded_df = read_batch_upload(uploaded_file)
            if uploaded_df is not None:
                st.session_state["batch_input_df"] = normalize_batch_columns(uploaded_df)
                st.session_state["batch_uploaded_signature"] = upload_signature
                st.session_state.pop("batch_result_df", None)
                st.success(f"已载入 {len(st.session_state['batch_input_df'])} 行清单，可检查后点击批量预测。")
    else:
        st.session_state.pop("batch_uploaded_signature", None)

    st.session_state["batch_input_df"] = normalize_batch_columns(st.session_state["batch_input_df"])

    render_section_header(
        "编辑清单",
        "已使用天数默认 30 天，使用人数默认 1 人，不按共用处理；异常行会单独提示，不影响其他行。",
    )
    def clear_batch_results() -> None:
        if "batch_result_df" in st.session_state:
            st.session_state["batch_result_df"] = None
        if "batch_result" in st.session_state:
            st.session_state["batch_result"] = None

    batch_df = st.data_editor(
        st.session_state["batch_input_df"],
        num_rows="dynamic",
        width='stretch',
        hide_index=True,
        column_config={
            "物品名称": st.column_config.TextColumn("物品名称", required=False),
            "用户描述": st.column_config.TextColumn("物品描述"),
            "剩余量(%)": st.column_config.NumberColumn("剩余量(%)", min_value=0, max_value=100, step=1),
            "周频次": st.column_config.NumberColumn("周频次", min_value=0, max_value=50, step=0.5),
            BATCH_HAS_SHELF_LIFE_COLUMN: st.column_config.CheckboxColumn(BATCH_HAS_SHELF_LIFE_COLUMN),
            BATCH_EXPIRE_DAYS_COLUMN: st.column_config.NumberColumn(BATCH_EXPIRE_DAYS_COLUMN, min_value=-365, max_value=3650, step=1),
            "是否破损": st.column_config.CheckboxColumn("是否破损"),
        },
        key="batch_editor",
        on_change=clear_batch_results,
    )

    if st.button("开始批量预测", type="primary", width='stretch'):
        if batch_df.empty:
            st.warning("请先填入有效数据")
        else:
            with st.spinner("正在进行批量预测，请稍候..."):
                batch_result = handle_batch_prediction(
                    batch_df,
                    signature,
                    model_bundles=model_bundles,
                )
                st.session_state["batch_result_df"] = batch_result["result_df"]
                st.session_state["batch_result"] = batch_result

    if st.session_state.get("batch_result_df") is not None:
        render_batch_results(st.session_state["batch_result"])
