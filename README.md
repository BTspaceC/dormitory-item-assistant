# 宿舍生活用品智能小助手

面向宿舍用品清单管理的中文 Streamlit 应用。系统先根据物品名称和描述识别类别，再结合剩余量、使用频率、有效期和破损状态给出风险提示。

[在线演示](https://hyr-dormitory-assistant-v2.streamlit.app/) · [模型评估报告](reports/model_eval.md) · [项目技术介绍](docs/project_introduction.md)

![项目介绍](assets/project_images/产品介绍图.png)

## 功能

- 单件预测：显示物品类别、风险等级、预计剩余天数、判断依据和建议。
- 批量清单：支持在线编辑以及 CSV、Excel 上传，单次最多处理 500 行。
- 结果导出：批量结果可导出为 CSV，用户反馈单独写入候选日志。
- 输入校验：处理空值、数值越界、中文编码和单行异常。
- 反馈记录：反馈需经人工复核后才能用于离线重训，不进行在线自动学习。

## 模型与数据

| 任务 | 方法 | 训练数据 | 输出 |
|:---|:---|:---|:---|
| 类别识别 | 字符 `2-5 gram` 与中文词组 `1-2 gram` TF-IDF、特征筛选、逻辑回归和领域关键词规则 | 109 条本地人工复核样本；42,000 条公开商品类别样本 | 7 类物品 |
| 风险判断 | 随机森林与临期、低库存等决策规则 | 109 条本地人工复核样本；外部商品数据不参与风险训练 | 4 类状态 |

外部商品标题来自 [JD dataset](https://gitee.com/KunLiu_kk/jd-dataset) 固定版本 `2931aecb`。项目按 7 个目标类别进行规则映射、去重和均衡抽样，形成 42,000 条训练样本与 7,000 条评估样本。两部分来自同一个公开数据源，标签由同一套规则映射产生，不是独立人工标注。派生数据位于 `data/external/jd_category_samples.csv.gz`，来源与许可见 [第三方声明](THIRD_PARTY_NOTICES.md)。

外部数据只有商品类别信息，没有库存、有效期或破损标签，因此不进入风险模型。

## 评估口径

- 类别模型在 7,000 条同源规则映射评估样本上的 Macro F1 为 `0.979`。
- 该指标用于验证当前清洗、映射与分类流程，不代表任意宿舍输入上的实际准确率。
- 本地人工复核留出集只有 10 条，风险指标波动较大，结果只保留在 [模型评估报告](reports/model_eval.md) 中用于回归检查。
- 系统提示不能替代对药品有效期、电器破损和安全隐患的人工检查。

## 环境

当前模型使用以下固定环境重新训练并通过测试：

| 组件 | 版本 |
|:---|:---|
| Python | 3.13.0 |
| NumPy | 2.4.2 |
| Pandas | 3.0.1 |
| Scikit-learn | 1.9.0 |
| Joblib | 1.5.3 |

安装并运行：

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

开发与测试：

```bash
python -m pip install -e .[dev]
python -m pytest -q
```

## 重新训练

仓库包含脱敏后的本地数据和压缩后的外部类别样本：

```bash
python -m src.data_prepare
python -m src.train_models
```

若需从已解压的 JD dataset 文本重新构建外部样本：

```bash
python -m src.external_data path/to/sample_train.txt path/to/sample_test.txt
python -m src.train_models
```

`src.external_data` 使用固定随机种子、标题去重和每类等量抽样，并预先划分 `external_train` 与 `external_eval`，避免同一标题同时出现在两部分中。

## 数据与反馈边界

- 仓库只保留脱敏后的本地数据，姓名和联系方式不进入训练集。
- `label_source=rule_initial` 的本地样本会被训练脚本拒绝；本地训练标签需经过人工复核。
- 用户反馈写入 `data/feedback/`，运行 `python -m src.merge_feedback` 只生成待复核候选样本。
- 外部数据许可为 MulanPSL-2.0，使用派生数据和模型时需保留许可证与第三方声明。

## 目录结构

```text
app.py                         Streamlit 入口
src/data_prepare.py            本地数据脱敏、清洗与训练集生成
src/external_data.py           外部商品类别映射、去重与抽样
src/train_models.py            模型训练、基线对照与评估
src/predict.py                 类别与风险统一预测接口
src/features.py                特征解析、领域规则与混合决策
src/merge_feedback.py          用户反馈候选样本整理
data/external/                 压缩后的外部类别样本
data/processed/                本地训练集与人工复核留出集
models/                        模型文件与环境元数据
reports/                       模型评估和测试记录
tests/                         自动化回归测试
```

## 当前限制

- 公开商品标题与宿舍用品输入存在领域差异。
- 7,000 条类别评估样本与训练样本同源，不能视为独立外部验证。
- 风险训练与留出样本规模较小，当前结果不用于证明普遍泛化能力。
- 应用未接入在线学习，反馈需要人工复核后再离线重训。

## AI 辅助开发说明

项目使用 AI 辅助方案讨论、代码与文档整理；数据边界、标签策略、测试结果和公开表述由开发者检查。详见 [AI 辅助开发记录](docs/ai_usage_record.md)。
