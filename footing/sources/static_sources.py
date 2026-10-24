"""Sources backed by hand-maintained tables (footing/static/). They never touch the network."""
from __future__ import annotations

from .. import staticdata
from ..models import Measure, SourceResult
from .base import Context, Source


class StaticTables(Source):
    name = "static_tables"
    license = "U.S. Government works (DOL, USDA, HUD); curated rows cite their own source"
    refresh = "monthly"
    homepage = "footing/static/"

    def fetch(self, ctx: Context) -> SourceResult:
        m: dict[str, Measure] = {}
        wage, wage_as_of = staticdata.min_wage(ctx.state_abbr)
        if wage is not None:
            m["min_wage"] = Measure("min_wage", wage, "USD/hour", "dol_min_wage", as_of=wage_as_of)
        tfp, tfp_as_of = staticdata.tfp_weekly()
        m["tfp_week"] = Measure("tfp_week", tfp, "USD/week", "usda_tfp", as_of=tfp_as_of,
                                note="male 20-50, 4-person household basis")
        coc = staticdata.coc_capacity(ctx.county_fips)
        if coc:
            beds = sum(float(coc[k] or 0) for k in ("es_beds", "th_beds", "sh_beds"))
            unsheltered = float(coc["pit_unsheltered"] or 0)
            m["beds_per_unsheltered"] = Measure(
                "beds_per_unsheltered", round(beds / max(unsheltered, 1.0), 2), "ratio", "hud_hic_pit",
                as_of=f"HIC/PIT {coc['year']}", note=f"CoC {coc['coc_code']}")
        rules = staticdata.local_rules(ctx.county_fips)
        if rules:
            m["local_rules"] = Measure("local_rules", rules, "curated", "local_rules")
        return SourceResult(self.name, "ok", measures=m)


class HRSASites(Source):
    """HRSA health center sites from the data.hrsa.gov download, saved to static/hrsa_sites.csv."""
    name = "hrsa"
    license = "U.S. Government work (public domain)"
    refresh = "monthly"
    homepage = "https://data.hrsa.gov/data/download"

    def fetch(self, ctx: Context) -> SourceResult:
        rows = staticdata.hrsa_sites()
        if not rows:
            return SourceResult(self.name, "unknown",
                                "static/hrsa_sites.csv is empty: download HRSA health center sites first")
        places = [self.place(ctx, id=f"hrsa:{r['site_id']}", name=r["name"], kind="health_center",
                             lat=float(r["lat"]), lon=float(r["lon"]), source=self.name,
                             tags={"address": r.get("address"), "phone": r.get("phone"),
                                   "sliding_fee": True})
                  for r in rows]
        return SourceResult(self.name, "ok", places=[p for p in places if p.distance_m <= ctx.radius_m * 2])
