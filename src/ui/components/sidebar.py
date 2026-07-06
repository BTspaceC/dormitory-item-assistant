import streamlit as st
from typing import Any
from src.ui.utils import render_html

def render_sidebar(metadata: dict[str, Any]) -> None:
    metrics = metadata.get("metrics", {})
    with st.sidebar:
        st.header("小助手状态")
        if not metadata:
            st.warning("未找到模型元数据，请先训练模型。")
        else:
            st.write(f"训练时间：{metadata.get('trained_at', '未知')}")
            st.metric("训练样本数", metadata.get("train_rows", "未知"), help="用于模型训练的总样本量")
            st.metric("真实留出样本数", metadata.get("real_holdout_rows", "未知"), help="未参与训练、用于评估的真实样本")

            
def render_app_header() -> None:
    render_html(
        """
        <section class="app-hero">
            <div class="app-hero-main">
                <div class="app-hero-copy">
                    <div class="app-hero-kicker">宿舍生活用品管理</div>
                    <h1>宿舍生活用品智能小助手</h1>
                    <p>
                        帮你记住纸巾、牙膏、感冒药和充电线这些容易被忘掉的小东西，
                        提前发现补货、过期和损坏风险。不知道哪些东西该补？先填一个试试看。
                    </p>
                    <div class="app-badges">
                        <span class="app-badge">宿舍清单</span>
                        <span class="app-badge">补货提醒</span>
                        <span class="app-badge">有效期关注</span>
                        <span class="app-badge">用户反馈记录</span>
                    </div>
                </div>
                <div class="app-hero-stats">
                    <div><strong>🧠 2 个模型</strong><span>类别 + 风险</span></div>
                    <div><strong>📋 批量清单</strong><span>CSV / Excel</span></div>
                    <div><strong>💬 反馈记录</strong><span>便于交付</span></div>
                </div>
            </div>
        </section>
        """
    )


