from __future__ import annotations

import math
import re
from datetime import date
from typing import Any


def jieba_tokenize(text: str) -> list[str]:
    import jieba
    return jieba.lcut(text)


CATEGORIES = [
    "清洁日用",
    "洗漱用品",
    "健康与补剂用品",
    "学习用品",
    "电子配件",
    "其他用品",
]

RISK_LABELS = ["正常", "需要关注", "建议补货", "过期/损坏风险"]

RISK_FEATURES = [
    "category",
    "used_days",
    "remaining_pct",
    "weekly_use_count",
    "user_count",
    "is_shared",
    "has_shelf_life",
    "days_to_expire",
    "is_damaged",
]

RISK_LABEL_MAP = {
    "暂不需要": "正常",
    "近期关注": "需要关注",
    "急需补货": "建议补货",
    "保质期提醒": "过期/损坏风险",
}

DAMAGE_KEYWORDS = [
    "坏了",
    "破损",
    "磨损",
    "接触不良",
    "断裂",
    "失效",
    "过期",
    "漏液",
    "变干",
    "发霉",
    "异味",
    "不能用",
]

NEGATIVE_DAMAGE_PATTERNS = [
    "没有破损",
    "无破损",
    "未破损",
    "没破损",
    "没有损坏",
    "无损坏",
    "未损坏",
    "没有坏",
    "没坏",
    "没有接触不良",
    "无接触不良",
    "未接触不良",
    "没接触不良",
    "没有过期",
    "无过期",
    "未过期",
    "没过期",
    "还没过期",
    "没有失效",
    "无失效",
    "未失效",
    "没失效",
    "还没失效",
    "没有漏液",
    "无漏液",
]


def text_or_empty(value: Any) -> str:
    if value is None:
        return ""
    try:
        import pandas as pd
        if pd.isna(value):
            return ""
    except ImportError:
        try:
            import math
            if isinstance(value, float) and math.isnan(value):
                return ""
        except Exception:
            pass
    s = str(value).strip()
    if s.lower() in ("nan", "none", "<na>"):
        return ""
    return s


def normalize_category(raw_category: str, item_name: str = "", description: str = "") -> str:
    raw = text_or_empty(raw_category)
    text = f"{item_name} {description}".lower()

    if raw in {"药品健康", "健身补剂", "健康与补剂用品"}:
        return "健康与补剂用品"
    if raw in {"清洁日用", "洗漱用品", "学习用品", "电子配件", "其他用品"}:
        if raw == "其他用品":
            if any(k in text for k in ["笔", "纸", "文件", "便利贴", "草稿", "打印"]):
                return "学习用品"
            if any(k in text for k in ["充电", "数据线", "电池", "耳机", "插排", "转换头"]):
                return "电子配件"
        return raw

    if any(k in text for k in ["纸巾", "垃圾袋", "洗衣", "洗手液", "湿巾", "消毒", "洗洁精", "清洁"]):
        return "清洁日用"
    if any(k in text for k in ["牙膏", "牙刷", "洗发", "沐浴", "洗面奶", "毛巾", "护手霜"]):
        return "洗漱用品"
    if any(k in text for k in ["药", "创可贴", "口罩", "蛋白粉", "维生素", "补剂"]):
        return "健康与补剂用品"
    if any(k in text for k in ["笔", "草稿", "打印", "文件", "便利贴"]):
        return "学习用品"
    if any(k in text for k in ["充电", "数据线", "电池", "插排", "耳机", "转换头"]):
        return "电子配件"
    return "其他用品"


def map_risk_label(user_judgment: str) -> str:
    value = text_or_empty(user_judgment)
    return RISK_LABEL_MAP.get(value, value if value in RISK_LABELS else "需要关注")


def parse_used_days(value: Any) -> int:
    # 优先尝试纯数值转换
    if value is not None:
        try:
            import pandas as pd
            if not pd.isna(value):
                val = float(value)
                if val == val:  # not NaN
                    return int(val)
        except (ValueError, TypeError):
            pass

    text = text_or_empty(value).strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        pass

    match = re.search(r"(\d+)\s*天", text)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s*周", text)
    if match:
        return int(match.group(1)) * 7
    match = re.search(r"(\d+)\s*个?月", text)
    if match:
        return int(match.group(1)) * 30
    if "较久" in text or "很久" in text:
        return 120
    if "半年" in text:
        return 180
    if "一年" in text:
        return 365
    return 0


def parse_remaining_pct(value: Any) -> float:
    # 优先尝试纯数值转换
    if value is not None:
        try:
            import pandas as pd
            if not pd.isna(value):
                val = float(value)
                if val == val:
                    if 0.0 < val <= 1.0:
                        return _bound_percent(val * 100.0)
                    return _bound_percent(val)
        except (ValueError, TypeError):
            pass

    text = text_or_empty(value).strip()
    if not text:
        return 50.0
    try:
        val = float(text)
        if val == val:
            if 0.0 < val <= 1.0:
                return _bound_percent(val * 100.0)
            return _bound_percent(val)
    except ValueError:
        pass

    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return _bound_percent(float(match.group(1)))
    
    # 匹配任意分数，如 1/3, 2/3, 3/4 等
    fraction_match = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if fraction_match:
        numerator = float(fraction_match.group(1))
        denominator = max(float(fraction_match.group(2)), 1.0)
        return _bound_percent((numerator / denominator) * 100.0)

    if "半" in text:
        return 50.0
    if "三分之一" in text:
        return 33.0
    if "三分之二" in text:
        return 67.0
    if "四分之三" in text:
        return 75.0
    if "四分之一" in text:
        return 25.0
    if any(k in text for k in ["可继续", "仍可", "较多", "尚可", "充足"]):
        return 70.0
    if any(k in text for k in ["较少", "不多", "快用完", "剩约1", "剩1"]):
        return 20.0
    if any(k in text for k in ["剩约2", "剩2", "剩约3", "剩3"]):
        return 25.0
    if any(k in text for k in ["剩约5", "剩5", "剩约6", "剩6", "剩约8", "剩8", "剩约10", "剩10"]):
        return 35.0
    return 50.0


def _bound_percent(value: float) -> float:
    if math.isnan(value):
        return 50.0
    return max(0.0, min(100.0, value))


def parse_weekly_use_count(value: Any) -> float:
    # 优先尝试纯数值转换
    if value is not None:
        try:
            import pandas as pd
            if not pd.isna(value):
                val = float(value)
                if val == val:
                    return val
        except (ValueError, TypeError):
            pass

    text = text_or_empty(value).strip()
    if not text:
        return 1.0
    try:
        val = float(text)
        if val == val:
            return val
    except ValueError:
        pass

    # 匹配诸如 "2次" 的后缀
    match = re.search(r"^(\d+(?:\.\d+)?)\s*次$", text)
    if match:
        return float(match.group(1))

    match = re.search(r"每周\s*(\d+(?:\.\d+)?)(?:\s*[-~到]\s*(\d+(?:\.\d+)?))?\s*次", text)
    if match:
        first = float(match.group(1))
        second = float(match.group(2)) if match.group(2) else first
        return (first + second) / 2.0
    match = re.search(r"每天\s*(\d+(?:\.\d+)?)(?:\s*[-~到]\s*(\d+(?:\.\d+)?))?\s*次", text)
    if match:
        first = float(match.group(1))
        second = float(match.group(2)) if match.group(2) else first
        return 7.0 * (first + second) / 2.0

    cn_nums = {"一": 1.0, "二": 2.0, "三": 3.0, "四": 4.0, "五": 5.0, "六": 6.0, "七": 7.0, "八": 8.0, "九": 9.0, "十": 10.0}
    for cn_char, num_val in cn_nums.items():
        if f"每周{cn_char}次" in text:
            return num_val
        if f"每天{cn_char}次" in text:
            return num_val * 7.0

    if "每天多次" in text:
        return 14.0
    if "每天或隔天" in text:
        return 5.0
    if "每天" in text:
        return 7.0
    if "隔天" in text:
        return 3.5
    if "每周多次" in text or "每周数次" in text:
        return 3.0
    if "每月" in text:
        match = re.search(r"每月\s*(\d+(?:\.\d+)?)(?:\s*[-~到]\s*(\d+(?:\.\d+)?))?\s*次", text)
        if match:
            first = float(match.group(1))
            second = float(match.group(2)) if match.group(2) else first
            return (first + second) / 2.0 / 4.0
        return 0.5
    if "偶尔" in text or "低频" in text:
        return 0.5
    return 1.0


def parse_user_count(value: Any) -> int:
    if value is not None:
        try:
            import pandas as pd
            if not pd.isna(value):
                val = int(float(value))
                return max(1, val)
        except (ValueError, TypeError):
            pass

    text = text_or_empty(value).strip()
    if not text:
        return 1
    try:
        return max(1, int(float(text)))
    except ValueError:
        pass

    match = re.search(r"(\d+)\s*人", text)
    if match:
        return max(1, int(match.group(1)))
    if "全寝" in text or "寝室" in text or "宿舍" in text:
        return 4
    return 1


def parse_is_shared(value: Any) -> int:
    if value is not None:
        try:
            import pandas as pd
            if not pd.isna(value):
                if isinstance(value, bool):
                    return 1 if value else 0
                val = float(value)
                return 1 if val > 0 else 0
        except (ValueError, TypeError):
            pass

    text = text_or_empty(value).strip()
    if text.lower() in ("true", "1", "yes", "y", "t", "是"):
        return 1
    if text.lower() in ("false", "0", "no", "n", "f", "否"):
        return 0
    return 1 if any(k in text for k in ["共用", "全寝", "寝室", "宿舍"]) else 0


def parse_shelf_life(value: Any, today: date | None = None) -> tuple[int, int]:
    today = today or date.today()
    if value is None:
        return 0, 999

    import pandas as pd
    if not isinstance(value, str) and not pd.isna(value):
        try:
            val_float = float(value)
            if val_float == val_float:
                return 1, int(val_float)
        except (ValueError, TypeError):
            pass
        try:
            from datetime import datetime
            if isinstance(value, date) and not isinstance(value, datetime):
                return 1, (value - today).days
            else:
                expiry = pd.to_datetime(value).date()
                return 1, (expiry - today).days
        except Exception:
            pass

    text = text_or_empty(value).strip()
    if not text or text in {"无", "无明显保质期压力", "0", "0.0"}:
        return 0, 999

    # 优先进行具体日期格式提取，避免因中文字符如 "有效期" 提前拦截
    match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", text)
    if match:
        year, month, day = map(int, match.groups())
        try:
            expiry = date(year, month, day)
            return 1, (expiry - today).days
        except ValueError:
            return 1, 90

    try:
        val_float = float(text)
        if val_float == val_float:
            return 1, int(val_float)
    except ValueError:
        pass

    if any(k in text for k in ["需核对", "以包装", "注意", "有效期", "包装日期", "开封后", "建议", "个月内"]):
        if "12个月" in text or "12 个月" in text:
            return 1, 365
        if "3个月" in text or "3 个月" in text:
            return 1, 90
        return 1, 90

    match = re.search(r"还有\s*(\d+)\s*个?月", text)
    if match:
        return 1, int(match.group(1)) * 30
    return 1, 90


def _safe_float(v: Any, default: float) -> float:
    if v is None:
        return default
    try:
        import pandas as pd
        if pd.isna(v):
            return default
    except ImportError:
        pass
    try:
        val = float(v)
        if val != val:
            return default
        return val
    except (ValueError, TypeError):
        return default


def _safe_int(v: Any, default: int) -> int:
    return int(_safe_float(v, float(default)))


def detect_damage(*texts: Any) -> int:
    joined = " ".join(text_or_empty(t) for t in texts)
    compact = re.sub(r"\s+", "", joined)
    
    # 每个损坏关键字都对应其专属否定短语，防止全局无条件匹配覆盖
    damage_negations = {
        "坏了": ["没有坏", "没坏", "没有坏了", "没坏了"],
        "破损": ["没有破损", "无破损", "未破损", "没破损"],
        "磨损": ["没有磨损", "无磨损", "未磨损", "没磨损"],
        "接触不良": ["没有接触不良", "无接触不良", "未接触不良"],
        "断裂": ["没有断裂", "无断裂", "未断裂"],
        "失效": ["没有失效", "无失效", "未失效"],
        "过期": ["没有过期", "未过期", "没过期"],
        "漏液": ["没有漏液", "无漏液", "未漏液"],
        "变干": ["没有变干", "无变干", "未变干"],
        "发霉": ["没有发霉", "无发霉", "未发霉"],
        "异味": ["没有异味", "无异味", "未异味"],
        "不能用": ["没有不能用", "未不能用"],
    }
    
    for keyword, negations in damage_negations.items():
        if keyword in compact:
            is_negated = any(neg in compact for neg in negations)
            if not is_negated:
                return 1
                
    for keyword in DAMAGE_KEYWORDS:
        if keyword in compact and keyword not in damage_negations:
            return 1
            
    return 0


def estimate_remaining_days(used_days: float, remaining_pct: float, weekly_use_count: float) -> int:
    used_days = _safe_float(used_days, 0.0)
    remaining_pct = _safe_float(remaining_pct, 50.0)
    weekly_use_count = _safe_float(weekly_use_count, 1.0)

    remaining_pct = _bound_percent(remaining_pct)
    if remaining_pct <= 0:
        return 0
    if used_days > 0 and remaining_pct < 100:
        consumed = max(1.0, 100.0 - remaining_pct)
        total_life_days = used_days * 100.0 / consumed
        return max(0, int(round(total_life_days - used_days)))
    if weekly_use_count > 0:
        return max(1, int(round(remaining_pct / max(weekly_use_count, 0.5))))
    return 30


def risk_rule_baseline(row: dict[str, Any]) -> str:
    remaining = _safe_float(row.get("remaining_pct"), 50.0)
    weekly = _safe_float(row.get("weekly_use_count"), 1.0)
    days_to_expire = _safe_int(row.get("days_to_expire"), 999)
    has_shelf_life = _safe_int(row.get("has_shelf_life"), 0)
    damaged = _safe_int(row.get("is_damaged"), 0)

    if damaged or (has_shelf_life and days_to_expire <= 30):
        return "过期/损坏风险"
    if remaining <= 15 or (weekly >= 7 and remaining <= 25):
        return "建议补货"
    if remaining <= 40 or (has_shelf_life and days_to_expire <= 90):
        return "需要关注"
    return "正常"


def _feature_value(input_data: Any, key: str, default: Any) -> Any:
    if isinstance(input_data, dict):
        return input_data.get(key, default)
    return getattr(input_data, key, default)


def explain_risk_factors(input_data: Any, predicted_risk: str) -> list[str]:
    remaining = _safe_float(_feature_value(input_data, "remaining_pct", 50.0), 50.0)
    weekly = _safe_float(_feature_value(input_data, "weekly_use_count", 1.0), 1.0)
    has_shelf_life = _safe_int(_feature_value(input_data, "has_shelf_life", 0), 0)
    days_to_expire = _safe_int(_feature_value(input_data, "days_to_expire", 999), 999)
    damaged = _safe_int(_feature_value(input_data, "is_damaged", 0), 0)
    used_days = _safe_float(_feature_value(input_data, "used_days", 0.0), 0.0)
    remaining_days = estimate_remaining_days(used_days, remaining, weekly)

    if predicted_risk == "正常":
        reasons: list[str] = []
        if remaining >= 50:
            reasons.append(f"剩余量约 {remaining:.0f}%，库存相对充足。")
        if weekly <= 2:
            reasons.append(f"每周使用约 {weekly:g} 次，消耗频率较低。")
        if has_shelf_life and days_to_expire > 90:
            reasons.append(f"距离有效期约 {days_to_expire} 天，暂未接近过期。")
        if not damaged:
            reasons.append("未标记破损或失效。")
        return reasons[:3] or ["当前填写的信息未显示明显补货或失效风险。"]

    if predicted_risk == "需要关注":
        reasons = []
        if remaining <= 40:
            reasons.append(f"剩余量约 {remaining:.0f}%，库存已经偏低。")
        if weekly >= 4:
            reasons.append(f"每周使用约 {weekly:g} 次，消耗频率较高。")
        if has_shelf_life and 30 < days_to_expire <= 90:
            reasons.append(f"距离有效期约 {days_to_expire} 天，建议近期核对。")
        if remaining_days <= 14:
            reasons.append(f"按当前使用情况估计，还能使用约 {remaining_days} 天。")
        return reasons[:3] or ["该物品暂未达到立即补货程度，但建议近期留意库存或状态。"]

    if predicted_risk == "建议补货":
        reasons = []
        if remaining <= 20:
            reasons.append(f"剩余量约 {remaining:.0f}%，库存很低。")
        if weekly >= 5:
            reasons.append(f"每周使用约 {weekly:g} 次，属于高频消耗物品。")
        if remaining_days <= 7:
            reasons.append(f"预计剩余可用约 {remaining_days} 天，补货优先级较高。")
        return reasons[:3] or ["该物品已接近用完，建议尽快补充。"]

    reasons = []
    if damaged:
        reasons.append("用户已标记存在破损或失效。")
    if has_shelf_life and days_to_expire < 0:
        reasons.append("该物品已超过有效期。")
    elif has_shelf_life and days_to_expire <= 30:
        reasons.append(f"距离有效期约 {days_to_expire} 天，过期风险较高。")
    if remaining <= 20:
        reasons.append(f"剩余量约 {remaining:.0f}%，同时存在状态风险。")
    return reasons[:3] or ["该物品存在过期、损坏或失效风险，建议人工核对。"]


def advice_for(category: str, risk_label: str, remaining_days: int) -> str:
    if risk_label == "建议补货":
        return f"建议尽快补充该物品，预计剩余可用约 {remaining_days} 天。"
    if risk_label == "需要关注":
        return f"建议近期关注库存或状态，预计剩余可用约 {remaining_days} 天。"
    if risk_label == "过期/损坏风险":
        if category == "电子配件":
            return "该物品可能存在损坏或失效风险，建议检查并准备备用。"
        return "该物品可能存在过期、变质或失效风险，建议核对有效期或更换。"
    return f"当前状态正常，预计剩余可用约 {remaining_days} 天，可暂不补货。"


EXAMPLES = {
    "抽纸：高频消耗，剩余 20%": {
        "item_name": "抽纸",
        "description": "宿舍公用，消耗快。",
        "used_days": 14,
        "remaining_pct": 20,
        "weekly_use_count": 10.0,
        "user_count": 4,
        "is_shared": True,
        "has_shelf_life": False,
        "expiry_days": 999,
        "is_damaged": False
    },
    "牙膏：单人使用，剩余 1/3": {
        "item_name": "牙膏",
        "description": "个人洗漱用品。",
        "used_days": 60,
        "remaining_pct": 33,
        "weekly_use_count": 14.0,
        "user_count": 1,
        "is_shared": False,
        "has_shelf_life": True,
        "expiry_days": 700,
        "is_damaged": False
    },
    "感冒药：备用药，还有4个月过期": {
        "item_name": "感冒药",
        "description": "备用药箱里的感冒药。",
        "used_days": 180,
        "remaining_pct": 80,
        "weekly_use_count": 0.5,
        "user_count": 1,
        "is_shared": False,
        "has_shelf_life": True,
        "expiry_days": 120,
        "is_damaged": False
    },
    "中性笔芯：学习用品，剩 2 支": {
        "item_name": "中性笔芯",
        "description": "上课和写作业经常用，还剩2支。",
        "used_days": 30,
        "remaining_pct": 25,
        "weekly_use_count": 5.0,
        "user_count": 1,
        "is_shared": False,
        "has_shelf_life": False,
        "expiry_days": 999,
        "is_damaged": False
    },
    "数据线：破损，接触不良": {
        "item_name": "数据线",
        "description": "每天使用，表皮已经破损，有时候接触不良。",
        "used_days": 180,
        "remaining_pct": 45,
        "weekly_use_count": 7.0,
        "user_count": 1,
        "is_shared": False,
        "has_shelf_life": False,
        "expiry_days": 999,
        "is_damaged": True
    },
    "异常输入：剩余量 5%": {
        "item_name": "纸巾",
        "description": "快用完了。",
        "used_days": 20,
        "remaining_pct": 5,
        "weekly_use_count": 14.0,
        "user_count": 1,
        "is_shared": False,
        "has_shelf_life": False,
        "expiry_days": 999,
        "is_damaged": False
    }
}

BATCH_TEMPLATE = [
    {
        "物品名称": "洗衣液",
        "用户描述": "宿舍合买的，还剩不到一半",
        "使用天数": 45,
        "剩余量(%)": 40,
        "周频次": 3.5,
        "使用人数": 4,
        "是否共用": True,
        "是否有保质期": True,
        "保质期(天)": 500,
        "是否破损": False
    },
    {
        "物品名称": "电池",
        "用户描述": "买了一板南孚电池，遥控器用",
        "使用天数": 100,
        "剩余量(%)": 60,
        "周频次": 0.1,
        "使用人数": 4,
        "是否共用": True,
        "是否有保质期": True,
        "保质期(天)": 1500,
        "是否破损": False
    },
    {
        "物品名称": "维生素C",
        "用户描述": "每天吃，快吃完了，下个月就过期",
        "使用天数": 150,
        "剩余量(%)": 10,
        "周频次": 7.0,
        "使用人数": 1,
        "是否共用": False,
        "是否有保质期": True,
        "保质期(天)": 20,
        "是否破损": False
    },
    {
        "物品名称": "",
        "用户描述": "",
        "使用天数": 0,
        "剩余量(%)": 100,
        "周频次": 1.0,
        "使用人数": 1,
        "是否共用": False,
        "是否有保质期": False,
        "保质期(天)": 0,
        "是否破损": False
    }
]

DOCS_OPTIONS = {
    "AI辅助使用记录": "docs/ai_usage_record.md",
    "用户交付记录": "reports/user_delivery_record.md",
    "测试用例与分析": "reports/test_cases.md",
    "模型训练与评估": "reports/model_eval.md",
    "试用数据记录": "reports/user_trial_export.md"
}

PROJECT_IMAGE_ITEMS = [
    {
        "title": "项目功能说明与产品介绍",
        "description": "产品功能定位与核心痛点解决。",
        "path": "assets/project_images/产品介绍图.png"
    },
    {
        "title": "三步快捷使用指南",
        "description": "宿舍生活用品智能小助手的三步快捷使用方法。",
        "path": "assets/project_images/三步使用指南图.png"
    },
    {
        "title": "日常真实使用场景演示",
        "description": "日常生活中的实际使用场景演示。",
        "path": "assets/project_images/使用场景图.png"
    },
    {
        "title": "项目算法可信度验证",
        "description": "算法可靠性验证与模型准确度说明。",
        "path": "assets/project_images/项目可信度图.png"
    }
]

RISK_CARD_CLASS = {
    "正常": "risk-normal",
    "需要关注": "risk-watch",
    "建议补货": "risk-restock",
    "过期/损坏风险": "risk-danger"
}

NUMERIC_RISK_FEATURES = [
    "used_days",
    "remaining_pct",
    "weekly_use_count",
    "user_count",
    "is_shared",
    "has_shelf_life",
    "days_to_expire",
    "is_damaged"
]

BATCH_HAS_SHELF_LIFE_COLUMN = "是否有保质期"
BATCH_EXPIRE_DAYS_COLUMN = "保质期(天)"
MAX_BATCH_UPLOAD_ROWS = 500
