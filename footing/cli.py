"""Command line: `python -m footing receipt --lat 37.13 --lon -80.41 --profile car,kids`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Settings
from .factors import catalog_markdown
from .pipeline import build_receipt, record_fixture_set
from .sources import ALL_SOURCES


def _summary(r: dict) -> str:
    out = [f"Settle Score: {r['settle_score']}  (confidence {r['confidence']} = {r['confidence_label']})",
           f"Area: {r['area'].get('county')}, {r['area'].get('state')}   tile {r['tile']['id']}   mode {r['mode']}",
           ""]
    for c in r["categories"]:
        s = "Unknown" if c["score"] is None else f"{c['score']:5.1f}"
        out.append(f"  {c['label']:<28} {s:>7}   weight {c['weight']:5.1f}   coverage {c['coverage']:.0%}")
    out.append("")
    for m in r["money"]:
        v = "Unknown" if m["value"] is None else f"{m['value']} {m['unit']}"
        out.append(f"  {m['label']:<48} {v}")
    out.append(f"\n{len(r['unknowns'])} parameters Unknown; see the JSON for reasons.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="footing", description="Footing open-data pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    rc = sub.add_parser("receipt", help="build a Settle Receipt for a point")
    rc.add_argument("--lat", type=float, required=True)
    rc.add_argument("--lon", type=float, required=True)
    rc.add_argument("--profile", default="", help="comma list: car,kids,tonight,on_foot")
    rc.add_argument("--mode", choices=["live", "replay", "record"])
    rc.add_argument("--fixtures", type=Path, help="fixture folder for replay/record")
    rc.add_argument("--cache", type=Path, help="SQLite response cache for live mode")
    rc.add_argument("--radius", type=int, help="search radius in meters (default 5000)")
    rc.add_argument("--out", type=Path, help="write the full JSON receipt here")
    rc.add_argument("--json", action="store_true", help="print JSON instead of the summary")
    rec = sub.add_parser("record", help="call every source live and save a replayable fixture set")
    rec.add_argument("--lat", type=float, required=True)
    rec.add_argument("--lon", type=float, required=True)
    rec.add_argument("--label", required=True, help='e.g. "Downtown Roanoke, VA"')
    rec.add_argument("--out", type=Path, required=True, help="e.g. fixtures/roanoke_2026-10-24")
    fc = sub.add_parser("factors", help="print the factor catalog")
    fc.add_argument("--markdown", action="store_true")
    sub.add_parser("sources", help="list data sources")
    args = ap.parse_args(argv)

    if args.cmd == "factors":
        print(catalog_markdown())
        return 0
    if args.cmd == "sources":
        for s in ALL_SOURCES:
            keys = ", ".join(s.needs) or "none"
            print(f"{s.name:<16} refresh={s.refresh:<8} keys={keys:<26} {s.license}")
        return 0

    if args.cmd == "record":
        m = record_fixture_set(args.lat, args.lon, args.label, args.out, Settings.from_env(mode="live"))
        print(f"Recorded {len(m['files'])} responses to {args.out}")
        for src, why in m["not_captured"].items():
            print(f"  not captured: {src}: {why}")
        return 0

    settings = Settings.from_env(mode=args.mode, fixture_dir=args.fixtures, cache_path=args.cache,
                                 radius_m=args.radius)
    receipt = build_receipt(args.lat, args.lon, args.profile, settings)
    text = json.dumps(receipt, indent=2, default=str)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text if args.json else _summary(receipt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
