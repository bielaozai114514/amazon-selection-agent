"""0-100 机会评分：五个子分加权，外加硬性过滤器。"""


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def sub_scores(product, profit, compliance):
    month_sales = product.get("month_sales", 0)
    demand = clamp(30 + (month_sales / 30.0)) if month_sales else 45

    reviews = product.get("avg_reviews_top3", 0)
    competition = clamp(95 - (reviews / 80.0))
    if product.get("brand_concentration", 0) > 0.6:
        competition -= 15

    margin = profit["margin"]
    profitability = clamp((margin - 0.10) / 0.35 * 100)
    comp = compliance["score"]

    weight_oz = product.get("weight_oz", 0)
    logistics = 95 if weight_oz <= 8 else 80 if weight_oz <= 32 else 55 if weight_oz <= 160 else 30

    return {
        "demand": round(clamp(demand), 1),
        "competition": round(clamp(competition), 1),
        "profit": round(profitability, 1),
        "compliance": round(comp, 1),
        "logistics": round(logistics, 1),
    }


WEIGHTS = {"demand": 0.30, "competition": 0.25, "profit": 0.25, "compliance": 0.10, "logistics": 0.10}


def hard_filters(product, profit, compliance):
    fails = []
    if profit["margin"] < 0.15:
        fails.append(f"毛利率 {profit['margin']:.1%} 低于 15%")
    if product.get("price_usd", 0) < 15:
        fails.append("售价低于 15 美元，广告成本吃不动")
    if product.get("weight_oz", 0) > 320:
        fails.append("单件超过 20 磅，进入大件费率")
    if compliance["level"] == "high":
        fails.append("合规扫描高风险")
    if product.get("ip_claim"):
        fails.append("已有知识产权投诉记录")
    return fails


def score(product, profit, compliance):
    subs = sub_scores(product, profit, compliance)
    total = sum(subs[k] * w for k, w in WEIGHTS.items())
    fails = hard_filters(product, profit, compliance)
    verdict = "reject" if fails else ("watch" if total < 60 else "pass")
    return {"sub_scores": subs, "total": round(total, 1), "hard_filters": fails, "verdict": verdict}
