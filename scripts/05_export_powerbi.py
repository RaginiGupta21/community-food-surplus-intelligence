# %% [markdown]
# # 05 - Export the Power BI star schema
# Builds a tidy star schema (dimensions + facts + analytic aggregates) in `powerbi/data/`.
# Every table carries `data_label = SYNTHETIC DEMO DATA` so the dashboard can never be mistaken for real findings.

# %%
import sys, pathlib
_here = pathlib.Path(__file__).resolve().parent if "__file__" in globals() else pathlib.Path.cwd()
_scripts = _here if (_here / "common.py").exists() else _here.parent / "scripts"
sys.path.insert(0, str(_scripts))

import numpy as np
import pandas as pd
from common import CLEAN, TAB, PBI, DATA_LABEL, ensure_dirs
from schema import FOOD_CATEGORIES

ensure_dirs()
m = pd.read_csv(CLEAN / "master_surplus.csv", parse_dates=["report_datetime", "report_date"])
md = pd.read_csv(CLEAN / "master_distribution.csv", parse_dates=["distribution_datetime"])
don = pd.read_csv(CLEAN / "donors.csv"); rec = pd.read_csv(CLEAN / "recipients.csv"); vol = pd.read_csv(CLEAN / "volunteers.csv")
ctx = pd.read_csv(CLEAN / "daily_context.csv", parse_dates=["date"])
seg = pd.read_csv(TAB / "donor_features_segments.csv")[["donor_id", "segment"]]
L = DATA_LABEL


def save(df, name):
    df = df.copy(); df["data_label"] = L
    df.to_csv(PBI / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"{name:34s} {len(df):6d} rows x {df.shape[1]} cols")


# ---- dimensions -------------------------------------------------------------------------
dd = ctx.drop(columns="data_label").copy()
dd["year"] = dd.date.dt.year; dd["month_num"] = dd.date.dt.month; dd["month_name"] = dd.date.dt.strftime("%b")
dd["year_month"] = dd.date.dt.strftime("%Y-%m"); dd["week_start"] = dd.date - pd.to_timedelta(dd.date.dt.weekday, unit="D")
dd["day_of_week_num"] = dd.date.dt.weekday + 1
save(dd.rename(columns={"rain_level": "rain_level_synthetic"}), "dim_date")
dn = don.drop(columns="data_label").merge(seg, on="donor_id", how="left"); dn["segment"] = dn.segment.fillna("Not clustered (<10 reports)")
save(dn, "dim_donor")
save(rec.drop(columns="data_label"), "dim_recipient")
save(vol.drop(columns="data_label"), "dim_volunteer")
fc = m.groupby("food_category").agg(perishability_class=("perishability_class", "first"), portion_size_kg=("portion_size_kg", "first")).reset_index()
fc["sort_order"] = fc.food_category.map({c: i + 1 for i, c in enumerate(FOOD_CATEGORIES)}); save(fc, "dim_food_category")
save(pd.DataFrame({"time_slot": ["Afternoon (12-17)", "Evening (17-21)", "Late Night (21-24)", "Morning (06-12)"], "sort_order": [2, 3, 4, 1],
                   "hour_from": [12, 17, 21, 6], "hour_to": [17, 21, 24, 12]}), "dim_time_slot")

# ---- facts ------------------------------------------------------------------------------
fs = m[["surplus_id", "collection_id", "donor_id", "volunteer_id", "report_date", "report_datetime", "report_hour", "time_slot", "food_category", "food_item",
        "diet_type", "surplus_reason", "quantity_kg", "est_portions", "declared_safe_window_hours", "collection_status", "uncollected_reason", "qty_collected_kg",
        "not_collected_kg", "delivered_kg", "post_collection_waste_kg", "portions_served", "assign_delay_min", "response_min", "collection_distance_km",
        "window_used_pct", "is_collected", "is_delivered", "final_outcome", "is_high_volume_event"]].rename(columns={"report_date": "date_key"})
fs["date_key"] = fs.date_key.dt.strftime("%Y-%m-%d"); save(fs, "fact_surplus")
fd = md[["distribution_id", "collection_id", "surplus_id", "donor_id", "recipient_id", "distribution_datetime", "delivery_hour", "qty_distributed_kg", "beneficiaries_served",
         "transport_distance_km", "wastage_kg", "wastage_reason", "distribution_status", "handover_record_complete", "pickup_to_delivery_min"]].copy()
fd["date_key"] = fd.distribution_datetime.dt.strftime("%Y-%m-%d"); save(fd, "fact_distribution")

# ---- analytic aggregates ----------------------------------------------------------------
zone = pd.read_csv(TAB / "gap_by_zone.csv")
cent = pd.concat([don[["sub_area", "latitude", "longitude"]], rec[["sub_area", "latitude", "longitude"]]]).groupby("sub_area").mean().reset_index()
save(zone.merge(cent, on="sub_area", how="left").rename(columns={"latitude": "zone_lat", "longitude": "zone_lon"}), "agg_zone_gap")
save(pd.read_csv(TAB / "hotspot_grid_cells.csv"), "agg_hotspot_cells")
save(pd.read_csv(TAB / "gap_decomposition.csv").rename(columns={"Unnamed: 0": "stage"}), "agg_gap_decomposition")
save(pd.read_csv(TAB / "hourly_supply_vs_recipient_availability.csv"), "agg_hourly_supply_availability")
flow = pd.read_csv(TAB / "flow_matrix_kg.csv", index_col=0).stack().rename("delivered_kg").reset_index()
flow.columns = ["donor_zone", "recipient_zone", "delivered_kg"]; save(flow, "agg_zone_flow")
save(pd.read_csv(TAB / "kmeans_segment_profiles.csv"), "agg_segment_profiles")
kp = pd.read_csv(TAB / "kpis.csv").rename(columns={"Unnamed: 0": "kpi", "value": "python_value"}); save(kp, "kpi_python_reference")

d = pd.read_csv(TAB / "daily_series.csv", parse_dates=["date"])[["date", "kg"]].rename(columns={"kg": "kg_value"}); d["series"] = "Actual"
bt = pd.read_csv(TAB / "forecast_backtest_detail.csv", parse_dates=["date"]); best = pd.read_csv(TAB / "forecast_summary.csv", index_col=0).loc["best_model"].iloc[0]
bt = bt[bt.model == best][["date", "pred"]].rename(columns={"pred": "kg_value"}); bt["series"] = "Back-test prediction"
f = pd.read_csv(TAB / "forecast_next_14_days.csv", parse_dates=["date"])
fl = pd.concat([d, bt, f[["date", "forecast_kg"]].rename(columns={"forecast_kg": "kg_value"}).assign(series="Forecast")])
fl = fl.merge(f[["date", "lower_80_kg", "upper_80_kg"]], on="date", how="left"); fl["model"] = best
save(fl, "forecast_daily")
print("\nPower BI export complete ->", PBI)
