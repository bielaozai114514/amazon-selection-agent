"""52 周三情景现金流：价格三档 × 销量三档，逐月滚动。"""

import copy

from . import profit as profit_mod

SCENARIOS = [
    {"name": "悲观", "price_factor": 0.90, "volume_factor": 0.60},
    {"name": "中性", "price_factor": 1.00, "volume_factor": 1.00},
    {"name": "乐观", "price_factor": 1.10, "volume_factor": 1.30},
]


def run(product, months=12):
    base_units = product.get("month_sales") or 300
    fixed = product.get("monthly_fixed_usd", 0.0)
    index = product.get("monthly_index") or [1.0] * 12
    stock_units = product.get("initial_stock_units") or int(base_units * 2)
    initial_outlay = stock_units * product["fob_usd"] + product.get("launch_cost_usd", 0.0)

    out = {}
    for sc in SCENARIOS:
        p = copy.deepcopy(product)
        p["price_usd"] = round(product["price_usd"] * sc["price_factor"], 2)
        per_unit = profit_mod.calc(p)["unit_profit"]

        cumulative = -initial_outlay
        payback = None
        rows = []
        for m in range(months):
            units = int(round(base_units * sc["volume_factor"] * index[m]))
            flow = units * per_unit - fixed
            cumulative += flow
            if payback is None and cumulative >= 0:
                payback = m + 1
            rows.append(
                {
                    "month": m + 1,
                    "units": units,
                    "profit": round(flow, 2),
                    "cumulative": round(cumulative, 2),
                }
            )

        out[sc["name"]] = {
            "price_usd": p["price_usd"],
            "unit_profit": round(per_unit, 2),
            "months": rows,
            "total_units": sum(r["units"] for r in rows),
            "total_profit": round(sum(r["profit"] for r in rows), 2),
            "ending_cash": round(cumulative, 2),
            "payback_month": payback,
            "worst_month": round(min(r["profit"] for r in rows), 2),
        }
    return {"initial_outlay": round(initial_outlay, 2), "scenarios": out}
