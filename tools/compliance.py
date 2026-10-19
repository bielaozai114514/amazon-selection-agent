"""合规风险扫描。只做关键词命中与检索入口生成，不给出侵权结论。"""

import json
from pathlib import Path
from urllib.parse import quote_plus

DATA = Path(__file__).resolve().parent.parent / "data"

# 类目信号词：用于校验 category 字段与标题/关键词是否自洽。
# category 是唯一决定认证清单的字段，填错就整张清单错，
# 而「漏掉强制认证」比「多要一个认证」危险得多，所以必须交叉校验。
CATEGORY_SIGNALS = {
    "food_contact": [
        "水杯", "杯子", "餐具", "餐盒", "保鲜", "饭盒", "碗", "瓶", "壶",
        "cup", "bottle", "plate", "bowl", "tumbler", "food container", "lunch box", "mug",
    ],
    "beauty": [
        "化妆品", "护肤", "精华", "面霜", "口红", "洗发", "面膜", "香水",
        "serum", "cream", "lotion", "makeup", "shampoo", "lipstick", "perfume", "cosmetic",
    ],
    "electronics": [
        "led", "充电", "usb", "蓝牙", "无线", "电池", "加湿器", "灯", "音箱", "耳机",
        "bluetooth", "wireless", "charger", "battery", "humidifier", "lamp", "speaker",
        "earbud", "headphone", "adapter",
    ],
    "toys": ["玩具", "儿童", "宝宝", "积木", "toy", "kids", "children", "baby", "puzzle"],
    "apparel": [
        "服装", "衣服", "裤", "裙", "鞋", "帽", "袜", "外套",
        "shirt", "pants", "dress", "shoe", "hat", "sock", "jacket",
    ],
}

# 排除短语：命中这些说明信号词是修饰语而非品类本身。
# 例：「化妆镜」含 makeup，但它是镜子不是化妆品；「水杯」含杯但不是玻璃杯类目。
EXCLUSIONS = {
    "beauty": ["化妆镜", "化妆刷", "makeup mirror", "makeup brush", "mirror", "镜"],
    "food_contact": ["杯垫", "杯架", "cup holder", "coaster"],
}


def load_terms():
    return json.loads((DATA / "risk_terms.json").read_text(encoding="utf-8"))


def validate_category(product):
    """校验 category 与标题/关键词是否自洽，返回告警列表。

    两类问题：
    1. category 不在认证映射表里 → 认证清单会静默为空，用户以为「不需要认证」
    2. 标题命中了另一个类目的强信号词 → 大概率填错类目，认证清单全错
    """
    cat = product.get("category", "")
    terms = load_terms()
    warnings = []

    if cat not in terms["certifications"]:
        warnings.append(
            f"category「{cat}」不在认证映射表中，本次不会输出任何认证要求。"
            f"这通常意味着类目填错了，而不是「不需要认证」。"
        )

    text = " ".join([
        product.get("title", ""),
        product.get("keyword", ""),
        " ".join(product.get("bullets", [])),
    ]).lower()

    for target, kws in CATEGORY_SIGNALS.items():
        if target == cat:
            continue
        # 排除短语优先：说明信号词只是修饰语（如「化妆镜」不是化妆品）
        if any(e in text for e in EXCLUSIONS.get(target, [])):
            continue
        hits = [k for k in kws if k in text]
        if hits:
            shown = "、".join(hits[:3])
            warnings.append(
                f"标题/关键词含「{shown}」，疑似 {target} 类目，但 category 填的是「{cat}」。"
                f"若确属 {target}，认证清单会完全不同，请核对。"
            )

    return warnings


def scan_text(text, terms):
    low = text.lower()
    brand = [t for t in terms["brand_terms"] if t in low]
    feature = [t for t in terms["feature_terms"] if t in low]
    return brand, feature


def search_links(keyword):
    q = quote_plus(keyword)
    return {
        "uspto_patent": "https://ppubs.uspto.gov/pubwebapp/static/pages/ppubsbasic.html",
        "google_patents": f"https://patents.google.com/?q={q}",
        "uspto_trademark": "https://tmsearch.uspto.gov/search/search-information",
        "wipo_brand": "https://branddb.wipo.int/",
        "cnipa": "https://pss-system.cponline.cnipa.gov.cn/",
        "euipo": "https://euipo.europa.eu/eSearch/",
        "amazon_transparency": "https://transparency.amazon.com/",
    }


def certifications(category, flags):
    terms = load_terms()
    out = []
    if category in terms["certifications"]:
        out += terms["certifications"][category]
    if flags.get("battery"):
        out += terms["certifications"]["battery"]
    if flags.get("laser"):
        out += terms["certifications"]["laser"]
    if flags.get("children"):
        out += terms["certifications"]["children"]
    return sorted(set(out))


def check(product):
    terms = load_terms()
    text = " ".join([product.get("title", ""), " ".join(product.get("bullets", []))])
    brand, feature = scan_text(text, terms)
    flags = {
        "battery": any(k in text.lower() for k in ("battery", "锂电", "充电")),
        "laser": "laser" in text.lower() or "激光" in text,
        "children": product.get("category") in ("toys", "children"),
    }
    score = 100
    score -= 55 if brand else 0
    score -= 12 * len(feature)
    score = max(0, score)
    level = "high" if score < 50 else ("medium" if score < 80 else "low")
    return {
        "score": score,
        "level": level,
        "category": product.get("category", ""),
        "category_warnings": validate_category(product),
        "brand_hits": brand,
        "feature_hits": feature,
        "certs": certifications(product.get("category", ""), flags),
        "links": search_links(product.get("title", "") or product.get("keyword", "")),
        "note": "命中项是人工核查清单，不是侵权判定",
    }
