import streamlit as st
import re
from pathlib import Path

from src.features import PROJECT_IMAGE_ITEMS, DOCS_OPTIONS
from src.ui.utils import render_html, render_section_header

PROJECT_ROOT = Path(__file__).resolve().parents[3]

def render_docs_page() -> None:
    render_section_header(
        "项目说明",
        "这里用于答辩展示、用户交付说明和项目材料查看，不影响预测工具页的操作。",
        "说明与材料",
    )
    render_html(
        """
        <div class="docs-intro">
            网页中仅展示脱敏交付信息，完整联系方式只用于课程正式交付回执。
        </div>
        """
    )
    render_project_image_gallery()
    render_section_header("项目文档", "文档内容直接读取项目内 Markdown 文件，便于保持本地材料和网页展示同步。")
    choice = st.selectbox("选择查看文档", list(DOCS_OPTIONS.keys()))
    text = read_markdown_file(PROJECT_ROOT / DOCS_OPTIONS[choice])
    if choice == "用户交付记录":
        text = sanitize_delivery_markdown(text)
    st.markdown(text)



def render_project_image_gallery() -> None:
    render_section_header("图文说明", "图片用于课程展示和用户交付讲解；预测操作仍集中在“单件预测”和“批量清单”两个工具页。")
    for item in PROJECT_IMAGE_ITEMS:
        with st.expander(item["title"]):
            st.write(item["description"])
            image_path = PROJECT_ROOT / item["path"]
            if image_path.exists():
                st.image(str(image_path), caption=item["title"], width='stretch')
            else:
                st.warning("图片暂未放入项目目录。")
    st.divider()



def read_markdown_file(path: Path) -> str:
    if not path.exists():
        return "该文档暂未生成。"
    try:
        return strip_yaml_frontmatter(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - keep UI readable for demo users.
        return f"文档读取失败：{exc}"



def strip_yaml_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    after = text.find("\n", end + 4)
    return text[after + 1 :].lstrip() if after != -1 else ""



def sanitize_delivery_markdown(text: str) -> str:
    sanitized = text
    sanitized = re.sub(r"(交付对象[：:]\s*)(.+)", r"\1目标用户A", sanitized)
    sanitized = re.sub(r"(联系方式[：:]\s*)(.+)", r"\1已脱敏，详见正式交付回执单", sanitized)
    sanitized = re.sub(r"(用户签字[：:]\s*)(.+)", r"\1[已脱敏]", sanitized)
    sanitized = re.sub(r"(签名[：:]\s*)(.+)", r"\1[已脱敏]", sanitized)
    sanitized = re.sub(r"(微信号?|QQ|手机号|电话)([：:\s]*)([^\n\r]*)", r"\1\2[已脱敏]", sanitized)
    sanitized = re.sub(r"1[3-9]\d{9}", "[已脱敏]", sanitized)
    return sanitized


