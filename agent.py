"""亚马逊选品 Agent：成本 → 合规 → 评分 → 报告，一步一工具。"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from tools import compliance, forecast, profit, report, scoring


def step(n, total, name, fn):
    t0 = time.perf_counter()
    out = fn()
    ms = (time.perf_counter() - t0) * 1000
    print(f"[{n}/{total}] {name} ... ok {ms:.0f}ms")
    return out


def run(product, out_dir):
    total = 7
    print(f"目标: {product.get('title') or product.get('keyword')}")
    fees = step(1, total, "读取费率表", lambda: (
        profit.load(profit.DATA / "fba_fees.json"),
        profit.load(profit.DATA / "duty_rates.json"),
    ))
    p = step(2, total, "落地成本核算", lambda: profit.calc(product, fees[0], fees[1]))
    c = step(3, total, "合规扫描", lambda: compliance.check(product))
    s = step(4, total, "机会评分", lambda: scoring.score(product, p, c))
    f = step(5, total, "52 周三情景现金流", lambda: forecast.run(product))
    md = step(6, total, "渲染报告", lambda: report.render(product, p, c, s, f))

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = (product.get("title") or product.get("keyword") or "product").replace(" ", "_")[:40]
    md_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {"product": product, "profit": p, "compliance": c, "score": s, "forecast": f},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    step(7, total, "落盘", lambda: None)

    print()
    print(md)
    print(f"报告: {md_path}")
    return md_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product", help="产品 JSON 路径")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    data = json.loads(Path(args.product).read_text(encoding="utf-8"))
    if "products" in data:
        for item in data["products"]:
            run(item, args.out)
            print("-" * 60)
    else:
        run(data, args.out)


if __name__ == "__main__":
    main()
