"""合规风险扫描。只做关键词命中与检索入口生成，不给出侵权结论。"""

import json
from pathlib import Path
from urllib.parse import quote_plus

DATA = Path(__file__).resolve().parent.parent / "data"


def load_terms():
    return json.loads((DATA / "risk_terms.json").read_text(encoding="utf-8"))


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
        "brand_hits": brand,
        "feature_hits": feature,
        "certs": certifications(product.get("category", ""), flags),
        "links": search_links(product.get("title", "") or product.get("keyword", "")),
        "note": "命中项是人工核查清单，不是侵权判定",
    }
