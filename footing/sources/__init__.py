"""Source registry. Order matters: the Census geocoder runs first and sets the county."""
from .keyed_sources import (BLSLaus, CensusACS, EIAGasoline, GooglePlacesText, HudFMR, KrogerBasket,
                            Transitland)
from .open_sources import NWS, CensusGeocoder, OpenMeteo, OSMOverpass, SnapRetailers, UrbanSchools
from .static_sources import HRSASites, StaticTables

ALL_SOURCES = [
    CensusGeocoder(),   # must be first
    NWS(), OpenMeteo(), SnapRetailers(), OSMOverpass(), UrbanSchools(),
    CensusACS(), BLSLaus(), HudFMR(), EIAGasoline(), GooglePlacesText(), Transitland(), KrogerBasket(),
    StaticTables(), HRSASites(),
]

__all__ = ["ALL_SOURCES"]
