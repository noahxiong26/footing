"""Derived views over receipts: Compare towns, Tonight Mode, Pocket Card."""
from __future__ import annotations

import io
import re
from html import escape

TONIGHT_KINDS = [("shelter", "Shelter"), ("day_center", "Day center"), ("soup_kitchen", "Meal"),
                 ("food_bank", "Food bank"), ("library", "Library (warm, Wi-Fi)"), ("toilets", "Restroom"),
                 ("drinking_water", "Drinking water")]
MAX_CARD_WALK_MIN = 45
CARD_KINDS = ["shelter", "soup_kitchen", "food_bank", "snap_retailer", "library", "clinic", "health_center",
              "post_office", "toilets"]


def compare(receipts: list[dict]) -> dict:
    """Side-by-side categories and money lines, with the differences spelled out."""
    def label(r):
        return (r["area"].get("nws_city") or r["area"].get("county")
                or f"No data for tile {r['tile']['id']}")

    names = [label(r) for r in receipts]
    rows = []
    for i, cat in enumerate(receipts[0]["categories"]):
        vals = [r["categories"][i]["score"] for r in receipts]
        rows.append({"category": cat["label"], "scores": vals,
                     "best": None if any(v is None for v in vals) else names[vals.index(max(vals))]})
    money = []
    for i, m in enumerate(receipts[0]["money"]):
        vals = [r["money"][i]["value"] for r in receipts]
        money.append({"label": m["label"], "values": vals, "unit": m["unit"]})
    changes = []
    if len(receipts) >= 2:
        a, b = receipts[0], receipts[1]
        for ca, cb in zip(a["categories"], b["categories"]):
            if ca["score"] is None or cb["score"] is None:
                continue
            d = cb["score"] - ca["score"]
            if abs(d) >= 10:
                changes.append(f"{ca['label']} is {'better' if d > 0 else 'worse'} in {names[1]} "
                               f"({cb['score']:.0f} vs {ca['score']:.0f}).")
        both_unknown = [ca["label"] for ca, cb in zip(a["categories"], b["categories"])
                        if ca["score"] is None or cb["score"] is None]
        if both_unknown:
            changes.append("Not compared (data missing in at least one place): " + ", ".join(both_unknown) + ".")
    return {"areas": names, "settle_scores": [r["settle_score"] for r in receipts],
            "confidence": [r["confidence"] for r in receipts], "categories": rows, "money": money,
            "what_changes": changes}


def tonight(receipt: dict) -> dict:
    items = []
    for kind, label in TONIGHT_KINDS:
        for p in receipt.get("nearest", {}).get(kind, []):
            if p.get("walk_min") is not None and p["walk_min"] > 60:
                continue
            items.append({"kind": kind, "label": label, "name": p["name"], "walk_min": p.get("walk_min"),
                          "open_now": p.get("open_now"), "closes": p.get("closes"),
                          "phone": p.get("tags", {}).get("phone"), "id": p["id"],
                          "lat": p["lat"], "lon": p["lon"]})
    # open first, then unknown hours, then closed; nearer first within each group
    rank = {True: 0, None: 1, False: 2}
    items.sort(key=lambda x: (rank[x["open_now"]], x["kind"] != "shelter", x["walk_min"] or 1e9))
    shelter_state = next((c for c in receipt["categories"] if c["id"] == "shelter"), {}).get("state")
    lows = receipt.get("lows_f") or []
    return {"local_time": receipt.get("local_time"), "alerts": receipt.get("alerts", []),
            "tonight_low_f": lows[0] if lows else None, "places": items[:8],
            "shelter_data": "unknown" if shelter_state != "known" else "known",
            "fallback": "Call 211 for tonight's shelter beds; bed counts are not published.",
            "message": None if shelter_state == "known" else
            "We could not confirm shelters near here from public data. Call 211."}


def pocket_card_svg(receipt: dict, link: str) -> str:
    """A 3.5 x 6 inch printable card: up to 6 places with walk time, hours, phone, plus a QR code."""
    import qrcode
    import qrcode.image.svg

    qr = qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage, border=1)
    buf = io.BytesIO()
    qr.save(buf)
    qr_svg = buf.getvalue().decode()
    view_box = re.search(r'viewBox="([^"]+)"', qr_svg).group(1)
    qr_inner = qr_svg[qr_svg.find(">", qr_svg.find("<svg")) + 1: qr_svg.rfind("</svg>")]
    labels = {"shelter": "Shelter", "soup_kitchen": "Meal site", "food_bank": "Food bank",
              "snap_retailer": "Takes EBT", "library": "Library: Wi-Fi, charging", "clinic": "Clinic",
              "health_center": "Health center", "post_office": "Post office: General Delivery",
              "toilets": "Public restroom"}
    picked = []
    for kind in CARD_KINDS:
        pool = [p for p in receipt.get("nearest", {}).get(kind, [])
                if p.get("walk_min") is None or p["walk_min"] <= MAX_CARD_WALK_MIN]
        if kind == "snap_retailer":
            pool.sort(key=lambda p: (not p.get("tags", {}).get("full_grocery"), p.get("walk_min") or 1e9))
        if pool:
            picked.append((kind, pool[0]))
        if len(picked) >= 5:
            break

    def clip(text: str, n: int) -> str:
        return text if len(text) <= n else text[: n - 1].rstrip() + "…"

    area = escape(receipt["area"].get("nws_city") or receipt["area"].get("county") or "")
    rows, y = [], 112
    for kind, p in picked:
        name = p["name"] if p["name"] != "(unnamed)" else labels.get(kind, kind)
        hours = p.get("tags", {}).get("opening_hours") or "hours unknown, call first"
        h1, h2 = (hours, "") if len(hours) <= 40 else (hours[:hours.rfind(";", 0, 40) + 1 or 40], hours[hours.rfind(";", 0, 40) + 1 or 40:].strip())
        phone = p.get("tags", {}).get("phone") or ""
        walk = f" · {p['walk_min']:.0f} min walk" if p.get("walk_min") is not None else ""
        lines = [f'<text x="20" y="{y}" font-size="15" font-weight="700">{escape(clip(name, 32))}</text>',
                 f'<text x="20" y="{y + 18}" font-size="12">{escape(labels.get(kind, kind))}{walk}</text>',
                 f'<text x="20" y="{y + 34}" font-size="11.5">{escape(clip(h1, 46))}</text>']
        dy = 50
        if h2:
            lines.append(f'<text x="20" y="{y + dy}" font-size="11.5">{escape(clip(h2, 46))}</text>')
            dy += 16
        if phone:
            lines.append(f'<text x="20" y="{y + dy}" font-size="12">{escape(phone)}</text>')
            dy += 16
        rows.append("".join(lines))
        y += dy + 14
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="336" height="576" viewBox="0 0 336 576" '
            f'font-family="Helvetica, Arial, sans-serif" fill="#111">'
            f'<rect width="336" height="576" fill="#fff" stroke="#111" stroke-width="2"/>'
            f'<text x="20" y="40" font-size="22" font-weight="800">FOOTING</text>'
            f'<text x="20" y="62" font-size="13">{area}</text>'
            f'<text x="20" y="80" font-size="11">Made {escape((receipt.get("local_time") or "")[:10])} · confirm hours by phone</text>'
            f'{"".join(rows)}'
            f'<text x="20" y="548" font-size="13" font-weight="700">No signal? Call 211.</text>'
            f'<svg x="232" y="468" width="88" height="88" viewBox="{view_box}">{qr_inner}</svg>'
            f'</svg>')
