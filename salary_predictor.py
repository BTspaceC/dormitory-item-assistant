import streamlit as st
import pandas as pd

# 设置网页基本配置
st.set_page_config(
    page_title="数据分析岗起薪计算器",
    page_icon="💼",
    layout="centered"
)

# 页面大标题与说明
st.title("💼 数据分析岗起薪计算器")
st.write("根据您的学历、意向城市、工作经验和专业技能，快速估算您的起薪范围。")

# 创建表单收集用户信息
with st.form("predictor_form"):
    st.write("### 📋 填写个人信息")
    
    # 1. 姓名输入
    name = st.text_input("您的姓名：", placeholder="请输入您的姓名")
    
    # 2. 学历单选
    education = st.radio(
        "您的学历：",
        options=["本科", "硕士", "博士"],
        horizontal=True
    )
    
    # 3. 工作城市下拉选择框
    city = st.selectbox(
        "意向工作城市：",
        options=["北京", "上海", "广州", "深圳", "杭州", "成都"]
    )
    
    # 4. 工作经验滑动条（0-5年）
    experience = st.slider(
        "相关工作经验（年）：",
        min_value=0,
        max_value=5,
        value=0,
        step=1
    )
    
    # 5. 技能掌握程度多选框
    skills = st.multiselect(
        "技能掌握程度（可多选）：",
        options=["Python", "SQL", "Excel", "Tableau", "PowerBI", "机器学习"],
        default=[]
    )
    
    # 提交表单计算按钮
    submit_button = st.form_submit_button("计算预期薪酬 🚀")

# 薪酬计算逻辑
if submit_button:
    if not name.strip():
        st.error("⚠️ 请先输入您的姓名！")
    else:
        # 基础薪酬：本科12万，硕士15万，博士18万
        base_salary = {"本科": 12.0, "硕士": 15.0, "博士": 18.0}[education]
        
        # 城市系数：北京/上海(1.3)，深圳/杭州(1.2)，广州(1.1)，成都(1.0)
        city_coeff = {
            "北京": 1.3, "上海": 1.3,
            "深圳": 1.2, "杭州": 1.2,
            "广州": 1.1,
            "成都": 1.0
        }[city]
        
        # 经验加成：每年经验 +2万
        exp_bonus = experience * 2.0
        
        # 技能加成：每项技能 +1万
        skill_bonus = len(skills) * 1.0
        
        # 最终年薪基准计算：(基础薪酬 + 经验加成 + 技能加成) * 城市系数
        predicted_base = (base_salary + exp_bonus + skill_bonus) * city_coeff
        
        # 预期年薪范围（设定上下 5% 的范围作为合理区间）
        lower_bound = predicted_base * 0.95
        upper_bound = predicted_base * 1.05
        
        # 气球庆祝特效
        st.balloons()
        
        # 展示计算结果
        st.write("---")
        st.write("### 🎉 计算结果")
        st.success(f"**{name}**，根据您选择的背景，我们为您计算出的起薪预测如下：")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="预期年薪范围",
                value=f"{lower_bound:.1f}万 - {upper_bound:.1f}万 / 年",
                delta=f"年薪基准: {predicted_base:.1f}万"
            )
        with col2:
            st.metric(
                label="平均月薪估算",
                value=f"{(lower_bound/12.0):.1f}万 - {(upper_bound/12.0):.1f}万 / 月",
                delta="含福利与年终奖"
            )
            
        # 详细拆解表格
        st.write("#### 📊 薪酬计算细节拆解：")
        breakdown_df = pd.DataFrame({
            "计算项目": [
                "学历基础年薪", 
                "工作经验加成", 
                "专业技能加成", 
                "城市折算系数", 
                "年薪预测基准值"
            ],
            "数值 / 加成": [
                f"{base_salary:.1f} 万 / 年 ({education})",
                f"+ {exp_bonus:.1f} 万 / 年 (+2万/年，当前 {experience} 年)",
                f"+ {skill_bonus:.1f} 万 / 年 (+1万/项，已选 {len(skills)} 项)",
                f"x {city_coeff:.1f} ({city})",
                f"**{predicted_base:.2f} 万 / 年**"
            ]
        })
        st.table(breakdown_df)
