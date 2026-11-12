# 06 - Power BI Dashboard Build Guide (SYNTHETIC DEMO DATA)

> A `.pbix` file cannot be created without Power BI Desktop (Windows), so this repository ships everything needed to build it in ~1-2 hours:
> a ready star schema (`powerbi/data/*.csv`), 32 DAX measures (`powerbi/measures.dax`), a soft theme (`powerbi/theme_soft_food_surplus.json`) and the page-by-page spec below.
> `kpi_python_reference.csv` lets you check every card against the Python results.

## 1. Load and model
1. *Get data -> Folder/Text-CSV*: load all CSVs from `powerbi/data/` (Transform: keep types; `date` columns as Date, `*_datetime` as Date/Time).
2. Mark `dim_date[date]` as the **date table**. Apply the theme: *View -> Themes -> Browse for themes*.
3. Relationships (all many-to-one, single direction):

| From (many) | To (one) |
|---|---|
| fact_surplus[date_key] | dim_date[date] |
| fact_surplus[donor_id] | dim_donor[donor_id] |
| fact_surplus[food_category] | dim_food_category[food_category] |
| fact_surplus[time_slot] | dim_time_slot[time_slot] |
| fact_surplus[volunteer_id] | dim_volunteer[volunteer_id] |
| fact_distribution[collection_id] | fact_surplus[collection_id] |
| fact_distribution[recipient_id] | dim_recipient[recipient_id] |
| fact_distribution[date_key] | dim_date[date] (**inactive**; use `USERELATIONSHIP`) |

`agg_*`, `forecast_daily` and `kpi_python_reference` are stand-alone (no relationships needed; relate `agg_zone_gap[sub_area]` to `dim_donor[sub_area]` only if you want cross-filtering).
4. Create a one-column table `_Measures` (Enter data), open *DAX query view*, paste `measures_dax_query_view.dax`, click *Update model with changes* (`measures.dax` is the same list in readable form). Sort `time_slot` by `dim_time_slot[sort_order]`, `month_name` by `month_num`.

## 2. Pages (16:9, soft background #F7F5F0, white cards)
**Every page**: a banner text box "SYNTHETIC DEMO DATA - illustrative, not verified real-world findings" (fill #D4A84B at 25% transparency) bound to `[Data Banner]`; slicers for Date (between), Donor zone, Donor category.

| # | Page | Visuals (fields) |
|---|---|---|
| 1 | **Overview** | KPI cards: Reported kg, Collected kg, Delivered kg, Portions Served, Redistribution Yield %, Collection Rate %, Median Response Min, Active Donors. Funnel/bar: reported -> collected -> delivered (agg_gap_decomposition). Line: Reported kg 7-Day Avg by date. Donut: food category share |
| 2 | **Donors and segments** | Table: donor, category, zone, kg, yield % (conditional colour via `[Yield Colour]`). Pareto (clustered column + cumulative line). Scatter: avg kg per report vs reports/month, colour = `dim_donor[segment]`. Matrix: segment profiles (`agg_segment_profiles`) |
| 3 | **Food and surplus reasons** | Treemap kg by food category; stacked bar reason x donor category; matrix food category x perishability; box-style table of median kg |
| 4 | **Time trends** | Monthly column + `kg per Active Donor` line; weekday x hour matrix heat map (conditional formatting on kg); `forecast_daily` line chart with series legend (Actual / Back-test / Forecast) and 80% band (lower/upper as error bars) |
| 5 | **Collection and distribution** | 100% stacked bar of `collection_status` by donor category and time slot; histogram of `response_min` (bins of 15); recipient utilisation bar (`dim_recipient` with Portions Served); wastage reasons bar (`fact_distribution`) |
| 6 | **Geography and gaps** | Map (or Azure/Filled map) with `agg_hotspot_cells` lat/lon, size = unserved_kg, colour = unserved_rate_%; recipient points from `dim_recipient`; zone gap table (`agg_zone_gap`); chart `agg_hourly_supply_availability` (reported_kg columns vs recipient_open_equivalents line); zone flow matrix (`agg_zone_flow`) |
| 7 | **Method and data notes** | Text: definitions, assumptions, limitations, "Synthetic vs real" legend, validation summary (`validation_report`) |

## 3. Distinguishing synthetic and real results
* Every table has `data_label`; `[Data Is Synthetic]` turns into a warning if any non-synthetic row appears.
* When real field data arrive, load them into **separate** tables (`*_field`) and add a page-level slicer "Data source". Never append to the synthetic tables.
* Page titles end with "(SYNTHETIC)" until the source is changed.

## 4. Accessibility and style
Muted palette only (navy, sage, terracotta, mustard, dusty rose, teal), no black or neon backgrounds, minimum 10 pt text, alt text on all visuals, colour never the only encoding.
