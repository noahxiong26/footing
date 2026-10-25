"""The HUD HIC/PIT loader against small workbooks shaped like HUD's (real files not yet tested)."""
import csv

from openpyxl import Workbook

from scripts.load_hud_hic_pit import main


def test_loader_matches_columns_by_keyword(tmp_path):
    hic = Workbook()
    ws = hic.active
    ws.title = "2024"
    ws.append(["CoC Number", "CoC Name", "Total Year-Round Beds (ES)", "Total Year-Round Beds (TH)",
               "Total Year-Round Beds (SH)"])
    ws.append(["VA-521", "Virginia Balance of State CoC", 100, 50, 0])
    hic.save(tmp_path / "hic.xlsx")
    pit = Workbook()
    ws = pit.active
    ws.title = "2024"
    ws.append(["CoC Number", "CoC Name", "Overall Homeless", "Sheltered Total Homeless", "Unsheltered Homeless"])
    ws.append(["VA-521", "Virginia Balance of State CoC", 400, 300, 100])
    pit.save(tmp_path / "pit.xlsx")
    xw = tmp_path / "xw.csv"
    xw.write_text("county_fips,county_name,coc_code,coc_name,lpg,source\n51121,Montgomery,VA-521,BoS,,test\n")
    out = tmp_path / "cap.csv"
    main(["--hic", str(tmp_path / "hic.xlsx"), "--pit", str(tmp_path / "pit.xlsx"), "--year", "2024",
          "--crosswalk", str(xw), "--out", str(out)])
    rows = list(csv.DictReader(open(out)))
    assert rows == [{"county_fips": "51121", "coc_code": "VA-521", "year": "2024", "es_beds": "100",
                     "th_beds": "50", "sh_beds": "0", "pit_unsheltered": "100", "pit_total": "400",
                     "source": "HUD AHAR 2024 HIC+PIT by CoC"}]
