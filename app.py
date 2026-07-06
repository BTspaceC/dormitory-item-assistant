import streamlit as st
import json
from pathlib import Path

# Important: set page config must be first
st.set_page_config(
    page_title="宿舍生活用品智能小助手",
    page_icon="🎒",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.predict import load_models
from src.features import EXAMPLES, BATCH_TEMPLATE
from datetime import date, timedelta

from src.ui.styles import add_page_style
from src.ui.styles import render_theme_bridge
from src.ui.components.sidebar import render_sidebar, render_app_header
from src.ui.pages.single_mode import render_single_mode
from src.ui.pages.batch_mode import render_batch_mode
from src.ui.pages.docs_page import render_docs_page

PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_ROOT / "models"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

def initialize_state() -> None:
    defaults = EXAMPLES["抽纸：高频消耗，剩余 20%"].copy()
    defaults["expiry_date"] = date.today() + timedelta(days=defaults.pop("expiry_days"))
    for key, value in defaults.items():
        if key == "is_damaged":
            if "is_damaged_input" not in st.session_state:
                st.session_state["is_damaged_input"] = value
        else:
            if key not in st.session_state:
                st.session_state[key] = value
    if "batch_input_df" not in st.session_state:
        import pandas as pd
        st.session_state["batch_input_df"] = pd.DataFrame(BATCH_TEMPLATE)

def read_model_metadata() -> dict:
    if not METADATA_PATH.exists():
        return {}
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

def model_cache_signature() -> tuple[int, int, int, str]:
    metadata_mtime = METADATA_PATH.stat().st_mtime_ns if METADATA_PATH.exists() else 0
    category_path = MODELS_DIR / "category_model.joblib"
    risk_path = MODELS_DIR / "risk_model.joblib"
    category_mtime = category_path.stat().st_mtime_ns if category_path.exists() else 0
    risk_mtime = risk_path.stat().st_mtime_ns if risk_path.exists() else 0
    trained_at = read_model_metadata().get("trained_at", "")
    return metadata_mtime, category_mtime, risk_mtime, trained_at

@st.cache_resource(show_spinner="正在加载模型，请稍候...")
def load_cached_models(signature: tuple[int, int, int, str]):
    _ = signature
    return load_models()

def main() -> None:
    add_page_style()
    render_theme_bridge()
    initialize_state()

    metadata = read_model_metadata()
    render_sidebar(metadata)

    render_app_header()

    signature = model_cache_signature()
    # Ensure models are loaded
    try:
        load_cached_models(signature)
    except Exception as e:
        # Predict functions have fallback now
        st.error(f"模型加载异常，将使用降级规则模式: {e}")

    single_tab, batch_tab, docs_tab = st.tabs(["单件预测", "批量清单", "项目说明"])
    with single_tab:
        render_single_mode(signature)
    with batch_tab:
        render_batch_mode(signature)
    with docs_tab:
        render_docs_page()

if __name__ == "__main__":
    main()

