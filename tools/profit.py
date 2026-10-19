"""落地成本与利润核算。纯确定性计算，不依赖任何外部接口。"""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dims_cm(d):
    return [d["length_in"] * 2.54, d["width_in"] * 2.54, d["height_in"] * 2.54]


def volume_weight_kg(d_in):
    l, w, h = dims_cm(d_in)
    return l * w * h / 6000.0


def size_class(weight_oz, d):
    longest = max(d["length_in"], d["width_in"], d["height_in"])
    rest = sum([d["length_in"], d["width_in"], d["height_in"]]) - longest
    girth = longest + 2 * rest
    if weight_oz <= 16 and longest <= 15 and girth <= 30:
        return "small_standard"
    if weight_oz <= 320 and longest <= 18 and girth <= 54:
        return "large_standard"
    return "large_bulky"


def pickup_fee(weight_oz, cls, table):
    if cls in ("small_standard", "large_standard"):
        for limit, fee in table[cls]:
            if weight_oz <= limit:
                return fee
        over = table["large_standard_over"]
        return round(over["base"] + max(0, weight_oz - 64) * over["per_oz"], 2)
    bulky = table["large_bulky"]
    return round(bulky["base"] + max(0, weight_oz / 16 - 1) * bulky["per_lb"], 2)


def duty_for(origin, hs, table):
    key = (hs or "")[:4]
    if key in table["hs_overrides"]:
        rate = table["hs_overrides"][key]
    else:
        rate = table["default"].get(origin, {"mfn": 0.0, "section301": 0.0})
    return rate["mfn"] + rate.get("section301", 0.0)


def referral_rate(category, table):
    return table["referral"].get(category, table["referral"]["default"])


def calc(product, fee_table=None, duty_table=None):
    fee_table = fee_table or load(DATA / "fba_fees.json")
    duty_table = duty_table or load(DATA / "duty_rates.json")

    qty = product.get("qty", 1)
    fob = product["fob_usd"]
    price = product["price_usd"]
    weight_oz = product["weight_oz"]
    d = product["dims_in"]
    origin = product.get("origin", "CN")
    hs = product.get("hs_code", "")

    shipping = product.get("shipping_per_kg", 8.0)
    actual_kg = weight_oz * 0.0283495
    chargeable = max(actual_kg, volume_weight_kg(d)) * qty
    freight = chargeable * shipping
    insurance = fob * qty * product.get("insurance_rate", 0.005)
    duty_rate = duty_for(origin, hs, duty_table)
    duty = fob * qty * duty_rate
    prep = product.get("prep_fee", 0.35) * qty
    inbound = product.get("inbound_fee", 0.0) * qty

    cls = size_class(weight_oz, d)
    fba = pickup_fee(weight_oz, cls, fee_table)
    referral = price * referral_rate(product.get("category", ""), fee_table)

    cuft = (d["length_in"] * d["width_in"] * d["height_in"]) / 1728.0
    storage_rate = (
        fee_table["storage"]["standard_cuft_month"]
        if cls != "large_bulky"
        else fee_table["storage"]["oversize_cuft_month"]
    )
    storage = cuft * storage_rate * product.get("storage_months", 2.0)

    return_pct = product.get("return_rate", 0.05)
    returns = price * return_pct * product.get("return_processing_rate", 0.5)

    cogs = fob * qty
    landed = cogs + freight + insurance + duty + prep + inbound
    total = landed + fba + referral + storage + returns

    unit_profit = price - total
    margin = unit_profit / price if price else 0.0
    roi = unit_profit / landed if landed else 0.0

    return {
        "size_class": cls,
        "chargeable_kg": round(chargeable, 3),
        "cogs": round(cogs, 2),
        "freight": round(freight, 2),
        "insurance": round(insurance, 2),
        "duty_rate": round(duty_rate, 4),
        "duty": round(duty, 2),
        "prep": round(prep, 2),
        "inbound": round(inbound, 2),
        "landed": round(landed, 2),
        "fba_fee": round(fba, 2),
        "referral": round(referral, 2),
        "storage": round(storage, 2),
        "returns": round(returns, 2),
        "total_cost": round(total, 2),
        "unit_profit": round(unit_profit, 2),
        "margin": round(margin, 4),
        "roi": round(roi, 4),
        "breakeven_price": round(total, 2),
    }
