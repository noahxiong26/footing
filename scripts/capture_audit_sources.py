"""Fetch only the primary bulk inputs needed for the ten-locality audit; keep responses unchanged.

Files go to ignored out/audit-sources; the manifest records failures and hashes so retries reuse success.
This is verification input, not a refresh of the app's committed captures.
"""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/audit-sources"
URLS = {
    "fmr.xlsx": "https://www.huduser.gov/portal/datasets/fmr/fmr2026/FY26_FMRs_revised.xlsx",
    "hic.xlsx": "https://www.huduser.gov/portal/sites/default/files/xls/2007-2025-HIC-Counts-by-CoC.xlsx",
    "pit.xlsb": "https://www.huduser.gov/portal/sites/default/files/xls/2007-2025-PIT-Counts-by-CoC.xlsb",
    "ice": "https://www.ice.gov/file-download/download/public/209716",
    "snap.json": "https://services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/snap_retailer_location_data/FeatureServer/0/query?" +
                 "where=State%3D%27VA%27&groupByFieldsForStatistics=County%2CStore_Type&" +
                 "outStatistics=%5B%7B%22statisticType%22%3A%22count%22%2C%22onStatisticField%22%3A%22ObjectId%22%2C%22outStatisticFieldName%22%3A%22n%22%7D%5D&returnGeometry=false&f=json",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "MANIFEST.json"
    prior = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    def fetch(item):
        name, url = item
        if prior.get(name, {}).get("status") == "ok" and prior[name].get("bytes", 0) > 0 and (OUT / name).exists():
            return name, prior[name]
        result = {"url": url, "checked_at": datetime.now(timezone.utc).isoformat()}
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Footing public-data audit)",
                                        "Accept": "*/*"})
            with urlopen(req, timeout=35) as response:
                body = response.read()
                result.update(status="ok", content_type=response.headers.get("Content-Type"),
                              bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), final_url=response.url)
            (OUT / name).write_bytes(body)
            if not body:
                raise ValueError("publisher returned an empty response; no data verified")
            if name.endswith((".xlsx", ".xlsb")) or name == "ice":
                if not body.startswith(b"PK"):
                    raise ValueError("response is not an Excel ZIP archive; no data verified")
            elif name.endswith(".json"):
                parsed = json.loads(body)
                if "error" in parsed or "features" not in parsed or parsed.get("exceededTransferLimit"):
                    raise ValueError("ArcGIS did not return a complete grouped query")
        except Exception as exc:
            result.update(status="unverified", error=f"{type(exc).__name__}: {exc}")
        print(f"{name}: {result['status']}", flush=True)
        return name, result

    with ThreadPoolExecutor(max_workers=4) as pool:
        result = dict(pool.map(fetch, URLS.items()))
    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
