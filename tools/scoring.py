"""0-100 机会评分：五个子分加权，外加硬性过滤器。

设计原则：**硬性过滤器优先于总分**。
加权平均天生会稀释致命项——毛利 8% 的品，其他维度拉满仍能到 80 分。
所以凡是「一项归零就不该做」的条件，一律放进过滤器，不进评分。
"""

import math

PASS_LINE = 70          # pass 门槛（原 60 太低，红海品也能踩线过）
FLOOR_PENALTY = 0.7     # 木桶惩罚系数：任一维度低于 FLOOR_SCORE 时总分打折
FLOOR_SCORE = 30


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def sub_scores(product, profit, compliance):
    month_sales = product.get("month_sales", 0)
    # 对数曲线：月销 20 和 200 的差距要拉开，而不是线性差 6 分
    demand = clamp(15 + 50 * math.log10(max(month_sales, 1)) / math.log10(5000)) if month_sales else 0

    reviews = product.get("avg_reviews_top3", 0)
    competition = clamp(95 - (reviews / 80.0))
    if product.get("brand_concentration", 0) > 0.6:
        competition -= 15

    margin = profit["margin"]
    profitability = clamp((margin - 0.10) / 0.35 * 100)

    comp = compliance["score"]
    # 类目填错时认证清单整张不可信，这一维度的满分没有意义
    if compliance.get("category_warnings"):
        comp *= 0.5

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
    """一票否决清单。命中任意一条即 reject，不看总分。"""
    fails = []

    # --- 成本侧：算不过账 ---
    if profit["margin"] < 0.15:
        fails.append(f"毛利率 {profit['margin']:.1%} 低于 15%")
    if product.get("price_usd", 0) < 15:
        fails.append("售价低于 15 美元，广告成本吃不动")
    if product.get("weight_oz", 0) > 320:
        fails.append("单件超过 20 磅，进入大件费率")

    # --- 合规侧 ---
    if compliance["level"] == "high":
        fails.append("合规扫描高风险")
    if product.get("ip_claim"):
        fails.append("已有知识产权投诉记录")

    # --- 需求侧：市场撑不起来（原来完全没拦，这是「怎么改都 pass」的主因）---
    month_sales = product.get("month_sales", 0)
    monthly_profit = profit["unit_profit"] * month_sales
    fixed = product.get("monthly_fixed_usd", 0)
    if fixed and monthly_profit < fixed:
        fails.append(
            f"月利润 ${monthly_profit:,.0f} 低于月固定成本 ${fixed:,.0f}，卖得越多亏得越多"
        )
    if month_sales < 100:
        fails.append(f"月销 {month_sales} 件过低，撑不起广告与运营投入")

    # --- 竞争侧：红海 ---
    reviews = product.get("avg_reviews_top3", 0)
    if reviews > 20000:
        fails.append(f"头部竞品评论 {reviews:,} 条，红海市场，新品难切")

    return fails


def score(product, profit, compliance):
    subs = sub_scores(product, profit, compliance)
    total = sum(subs[k] * w for k, w in WEIGHTS.items())

    # 木桶惩罚：一项归零、其他拉满，不该还能拿高分
    if min(subs.values()) < FLOOR_SCORE:
        total *= FLOOR_PENALTY

    fails = hard_filters(product, profit, compliance)
    verdict = "reject" if fails else ("watch" if total < PASS_LINE else "pass")
    return {
        "sub_scores": subs,
        "total": round(total, 1),
        "hard_filters": fails,
        "verdict": verdict,
    }
