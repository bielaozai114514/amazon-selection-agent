"""把结果渲染成 Markdown。"""

WEIGHT_PCT = {"demand": 30, "competition": 25, "profit": 25, "compliance": 10, "logistics": 10}


def money(v):
    return f"${v:,.2f}"


def render(product, profit, compliance, score, forecast=None):
    lines = []
    lines.append(f"# 选品评估 · {product.get('title') or product.get('keyword', '未命名')}")
    lines.append("")
    lines.append(f"**结论：{score['verdict']}　总分 {score['total']}/100**")
    lines.append("")
    if score["hard_filters"]:
        lines.append("## 硬性否决")
        for f in score["hard_filters"]:
            lines.append(f"- {f}")
        lines.append("")
    lines.append("## 成本结构")
    lines.append("")
    lines.append("| 项目 | 金额 |")
    lines.append("|---|---|")
    rows = [
        ("采购 FOB", profit["cogs"]),
        ("头程运费", profit["freight"]),
        ("保险", profit["insurance"]),
        (f"关税（{profit['duty_rate']:.1%}）", profit["duty"]),
        ("贴标/预处理", profit["prep"]),
        ("入仓费", profit["inbound"]),
        ("FBA 配送费", profit["fba_fee"]),
        ("平台佣金", profit["referral"]),
        ("仓储", profit["storage"]),
        ("退货损耗", profit["returns"]),
        ("合计成本", profit["total_cost"]),
    ]
    for name, v in rows:
        lines.append(f"| {name} | {money(v)} |")
    lines.append("")
    lines.append("## 关键指标")
    lines.append("")
    lines.append(f"- 售价：{money(product['price_usd'])}")
    lines.append(f"- 单件利润：{money(profit['unit_profit'])}")
    lines.append(f"- 毛利率：{profit['margin']:.1%}")
    lines.append(f"- 投入回报率：{profit['roi']:.1%}")
    lines.append(f"- 盈亏平衡价：{money(profit['breakeven_price'])}")
    lines.append(f"- 尺寸档位：{profit['size_class']}　计费重：{profit['chargeable_kg']} kg")
    lines.append("")
    lines.append("## 评分拆解")
    lines.append("")
    lines.append("| 维度 | 分数 | 权重 |")
    lines.append("|---|---|---|")
    for k, v in score["sub_scores"].items():
        lines.append(f"| {k} | {v} | {WEIGHT_PCT[k]}% |")
    lines.append("")
    lines.append("## 合规")
    lines.append("")
    lines.append(f"- 扫描分：{compliance['score']}（{compliance['level']}）")
    if compliance["brand_hits"]:
        lines.append(f"- 品牌词命中：{', '.join(compliance['brand_hits'])}")
    if compliance["feature_hits"]:
        lines.append(f"- 特征词命中：{', '.join(compliance['feature_hits'])}")
    if compliance["certs"]:
        lines.append(f"- 需要的认证：{', '.join(compliance['certs'])}")
    lines.append("")
    lines.append("检索入口：")
    for name, url in compliance["links"].items():
        lines.append(f"- {name}: {url}")
    if forecast:
        lines.append("")
        lines.append("## 52 周三情景")
        lines.append("")
        lines.append(f"首批备货投入：{money(forecast['initial_outlay'])}")
        lines.append("")
        lines.append("| 情景 | 售价 | 单件利润 | 12 个月销量 | 12 个月利润 | 期末现金 | 回本月份 | 最差月 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for name, s in forecast["scenarios"].items():
            payback = f"第 {s['payback_month']} 月" if s["payback_month"] else "12 个月内未回本"
            lines.append(
                f"| {name} | {money(s['price_usd'])} | {money(s['unit_profit'])} | "
                f"{s['total_units']} | {money(s['total_profit'])} | {money(s['ending_cash'])} | "
                f"{payback} | {money(s['worst_month'])} |"
            )
        lines.append("")
        lines.append("中性情景逐月：")
        lines.append("")
        lines.append("| 月 | 销量 | 当月利润 | 累计 |")
        lines.append("|---|---|---|---|")
        for r in forecast["scenarios"]["中性"]["months"]:
            lines.append(f"| {r['month']} | {r['units']} | {money(r['profit'])} | {money(r['cumulative'])} |")
    return "\n".join(lines) + "\n"
