"""亚马逊选品决策 Agent · 网页版（Streamlit）。

部署：Streamlit Community Cloud 连本仓库，入口选 app.py 即可。
底层复用 tools/ 下的成本、合规、评分、现金流模块，与 CLI 完全同一套逻辑。
"""

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tools import compliance, forecast, profit, report, scoring  # noqa: E402

st.set_page_config(page_title="亚马逊选品决策 Agent", page_icon="📦", layout="wide")

CATEGORIES = [
    "electronics", "home_kitchen", "beauty", "food_contact",
    "toys", "apparel", "tools", "battery",
]

st.title("亚马逊选品决策 Agent")
st.caption(
    "输入一个候选产品，输出「做 / 观望 / 否决」结论、成本拆解、合规清单与 52 周现金流。"
    "成本与评分是确定性计算，同样的输入永远得到同样的结果。"
)

with st.form("product_form"):
    st.subheader("产品信息")
    c1, c2, c3 = st.columns(3)
    with c1:
        title = st.text_input("产品名", "便携 LED 化妆镜 可折叠 带补光")
        keyword = st.text_input("核心关键词（英文）", "portable led makeup mirror")
        category = st.selectbox("类目", CATEGORIES, index=0)
    with c2:
        fob = st.number_input("采购价 FOB（USD）", 0.1, 500.0, 4.2, 0.1)
        price = st.number_input("售价（USD）", 1.0, 999.0, 24.99, 0.5)
        shipping = st.number_input("头程单价（USD/kg）", 0.5, 50.0, 8.0, 0.5)
    with c3:
        weight_oz = st.number_input("单件重量（oz）", 0.1, 400.0, 9.0, 0.5)
        hs_code = st.text_input("HS 编码（可留空）", "9405.40")
        origin = st.selectbox("产地", ["CN", "VN", "IN", "US"], index=0)

    st.subheader("尺寸（英寸）")
    d1, d2, d3 = st.columns(3)
    length = d1.number_input("长", 0.1, 200.0, 8.0, 0.5)
    width = d2.number_input("宽", 0.1, 200.0, 6.0, 0.5)
    height = d3.number_input("高", 0.1, 200.0, 1.2, 0.2)

    st.subheader("市场与运营假设")
    m1, m2, m3, m4 = st.columns(4)
    month_sales = m1.number_input("预计月销量", 1, 100000, 900, 50)
    reviews = m2.number_input("头部竞品评论数", 0, 200000, 1200, 50)
    brand_conc = m3.slider("品牌集中度", 0.0, 1.0, 0.35, 0.05)
    return_rate = m4.slider("退货率", 0.0, 0.3, 0.05, 0.01)

    n1, n2, n3 = st.columns(3)
    stock_units = n1.number_input("首批备货（件）", 50, 50000, 1800, 100)
    launch_cost = n2.number_input("推广投入（USD）", 0, 100000, 1200, 100)
    fixed_cost = n3.number_input("月固定成本（USD）", 0, 50000, 600, 100)

    bullets_raw = st.text_area(
        "产品卖点（每行一条，用于合规关键词扫描）",
        "三色温补光，USB 充电\n折叠后仅 1.2 英寸厚，适合旅行\n高清镜面，无放大变形",
        height=90,
    )

    submitted = st.form_submit_button("开始评估", type="primary", use_container_width=True)

if submitted:
    product = {
        "title": title,
        "keyword": keyword,
        "category": category,
        "fob_usd": fob,
        "price_usd": price,
        "weight_oz": weight_oz,
        "dims_in": {"length_in": length, "width_in": width, "height_in": height},
        "origin": origin,
        "hs_code": hs_code.strip() or None,
        "shipping_per_kg": shipping,
        "storage_months": 2,
        "return_rate": return_rate,
        "month_sales": int(month_sales),
        "avg_reviews_top3": int(reviews),
        "brand_concentration": brand_conc,
        "monthly_fixed_usd": fixed_cost,
        "initial_stock_units": int(stock_units),
        "launch_cost_usd": launch_cost,
        "monthly_index": [1.0] * 12,
        "bullets": [b.strip() for b in bullets_raw.splitlines() if b.strip()],
    }

    try:
        fees = profit.load(profit.DATA / "fba_fees.json")
        duty = profit.load(profit.DATA / "duty_rates.json")
        p = profit.calc(product, fees, duty)
        c = compliance.check(product)
        s = scoring.score(product, p, c)
        f = forecast.run(product)
        md = report.render(product, p, c, s, f)
    except Exception as exc:  # noqa: BLE001
        st.error(f"计算失败：{exc}")
    else:
        verdict = s["verdict"]
        color = {"pass": "normal", "watch": "off", "reject": "inverse"}.get(verdict, "off")
        st.markdown("---")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("结论", verdict.upper())
        col_b.metric("总分", f"{s['total']}/100")
        col_c.metric("毛利率", f"{p['margin']:.1%}")

        if s["hard_filters"]:
            st.warning("命中硬性否决：" + "；".join(s["hard_filters"]))
        if c.get("category_warnings"):
            st.warning("类目校验告警：" + "；".join(c["category_warnings"]))

        st.markdown(md)

        st.download_button(
            "下载完整结果（JSON）",
            data=json.dumps(
                {"product": product, "profit": p, "compliance": c,
                 "score": s, "forecast": f},
                ensure_ascii=False, indent=2,
            ),
            file_name=f"{title[:20] or 'product'}_评估结果.json",
            mime="application/json",
        )

st.markdown("---")
st.caption(
    "费率表为 2024-04-15 美国站基准，正式决策前请按卖家后台最新费率核对。"
    "合规部分只给检索入口与认证清单，不构成侵权结论。"
)
