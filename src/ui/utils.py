import streamlit as st
from typing import Any
from textwrap import dedent

def render_html(markup: str) -> None:
    st.markdown(clean_html(markup), unsafe_allow_html=True)

def clean_html(markup: str) -> str:
    return dedent(markup).strip()

def format_percent(value: Any) -> str:
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "未知"

def render_section_header(title: str, caption: str = "", eyebrow: str = "") -> None:
    if eyebrow:
        st.caption(f"**{eyebrow}**")
    st.markdown(f"### {title}")
    if caption:
        st.caption(caption)

