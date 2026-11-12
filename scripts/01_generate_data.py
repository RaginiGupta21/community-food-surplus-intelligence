"""01 - Generate SYNTHETIC DEMO DATA for the Dadar-Matunga-Mahim study area.

All organisations, people and records are fictional. Coordinates are approximate
zone centroids with random jitter (not real addresses). The generator simulates the
*process* (reporting -> collection -> distribution) so relationships, dates and
quantities are internally consistent. Deterministic: seed = 2026.

Run:  python scripts/01_generate_data.py
"""
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, DATA, DATA_LABEL, SEED, ensure_dirs  # noqa: E402
from schema import (TABLES, DONOR_CATEGORIES, ZONES, FOOD_CATEGORIES, REASONS,  # noqa: E402
                    PACKAGING, STORAGE)

rng = np.random.default_rng(SEED)
START, END = date(2025, 11, 1), date(2026, 10, 31)
DAYS = [START + timedelta(days=i) for i in range((END - START).days + 1)]
ND = len(DAYS)

# ----------------------------------------------------------------------------- geography
ZONE_XY = {  # approximate centroids (lat, lon) - analyst approximation, not surveyed
    "Dadar West": (19.0185, 72.8415), "Dadar East": (19.0225, 72.8490),
    "Shivaji Park": (19.0275, 72.8380), "Matunga": (19.0270, 72.8570),
    "Mahim": (19.0405, 72.8405), "Dharavi Fringe": (19.0400, 72.8535)}


def jitter(zone, sd=0.0028):
    la, lo = ZONE_XY[zone]
    return round(la + rng.normal(0, sd), 5), round(lo + rng.normal(0, sd), 5)


def road_km(a, b):
    """Haversine x 1.3 (urban road factor), a/b = (lat, lon)."""
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dphi, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 1.3 * 2 * r * math.asin(math.sqrt(h))


# ----------------------------------------------------------------------------- calendar context
FESTIVALS = [  # dates cross-checked against several public 2026 India/Maharashtra holiday calendars (moon-dependent dates +-1 day)
    ("Christmas & New Year", date(2025, 12, 24), date(2026, 1, 1)),
    ("Makar Sankranti", date(2026, 1, 14), date(2026, 1, 14)),
    ("Holi", date(2026, 3, 3), date(2026, 3, 4)),                      # Holika Dahan 3 Mar, Holi 4 Mar
    ("Gudi Padwa & Eid-ul-Fitr", date(2026, 3, 19), date(2026, 3, 21)),  # Eid 20/21 Mar (moon sighting)
    ("Ram Navami", date(2026, 3, 26), date(2026, 3, 27)),
    ("Eid-ul-Adha", date(2026, 5, 27), date(2026, 5, 28)),
    ("Raksha Bandhan", date(2026, 8, 27), date(2026, 8, 28)),
    ("Janmashtami", date(2026, 9, 4), date(2026, 9, 5)),
    ("Ganeshotsav", date(2026, 9, 14), date(2026, 9, 24)),             # Chaturthi 14 Sep; visarjan ~10 days later
    ("Navratri & Dussehra", date(2026, 10, 11), date(2026, 10, 20))]   # Dussehra 20 Oct 2026
# Diwali 2025 fell on 20-21 Oct 2025 (before the window); Diwali 2026 is 8 Nov 2026 (after it) - neither is in the training window.
WEDDING = [(date(2025, 11, 20), date(2026, 2, 15)), (date(2026, 4, 15), date(2026, 5, 31))]
MONSOON_ONSET = date(2026, 6, 22)  # IMD/press: 2026 onset ~2 weeks later than the 10 Jun normal


def rain_params(d):
    """(P(rain day), share of rain days that are heavy). Monthly intensity follows IMD/press reports for 2026:
    late onset; June ~416 mm and July ~1,492 mm at Santacruz (July ~175% of its ~856 mm normal); dry spell 1-4 Aug;
    IMD outlook of below-normal Aug-Sep. Day-level placement of rain is simulated; Sept/Oct values are assumptions."""
    if d < MONSOON_ONSET:
        return 0.04, 0.2
    if d.month == 6:
        return 0.75, 0.35
    if d.month == 7:
        return 0.80, 0.50
    if d.month == 8:
        return (0.05, 0.1) if d.day <= 4 else (0.45, 0.30)
    if d.month == 9:
        return 0.35, 0.25
    return 0.04, 0.2

ctx_rows = []
for d in DAYS:
    fest = next((n for n, s, e in FESTIVALS if s <= d <= e), "No Festival")
    wed = int(any(s <= d <= e for s, e in WEDDING))
    monsoon = int(MONSOON_ONSET <= d <= date(2026, 9, 30))
    p, hv = rain_params(d)
    r = rng.random()
    rain = "No Rain" if r >= p else ("Heavy" if rng.random() < hv else "Light/Moderate")
    ctx_rows.append(dict(date=d, day_name=d.strftime("%A"), is_weekend=int(d.weekday() >= 5),
                         festival_name=fest, wedding_season_flag=wed, monsoon_season_flag=monsoon,
                         rain_level=rain, data_label=DATA_LABEL))
ctx = pd.DataFrame(ctx_rows)
FEST = ctx["festival_name"].ne("No Festival").to_numpy()
WED = ctx["wedding_season_flag"].to_numpy().astype(bool)
RAINLV = ctx["rain_level"].to_numpy()
DOW = np.array([d.weekday() for d in DAYS])

# ----------------------------------------------------------------------------- donors
CAT = {  # n donors, base daily report prob, weekday multipliers Mon..Sun, qty (median,sigma,min,max)
    "Restaurant": dict(n=38, p=0.30, dow=[.8, .8, .85, .9, 1.2, 1.4, 1.3], fest=1.15, wed=1.0, q=(6, .55, 1, 30)),
    "Bakery": dict(n=22, p=0.50, dow=[.95, .95, .95, 1, 1.05, 1.1, 1.0], fest=1.1, wed=1.0, q=(3, .5, .5, 14)),
    "Caterer": dict(n=20, p=0.10, dow=[.5, .5, .6, .8, 1.3, 2.0, 2.0], fest=2.0, wed=1.9, q=(35, .6, 8, 150)),
    "Residential Society": dict(n=18, p=0.035, dow=[.3, .3, .3, .4, .9, 3.0, 3.0], fest=5.0, wed=1.2, q=(8, .5, 2, 40)),
    "Sweet Shop": dict(n=10, p=0.28, dow=[.9, .9, .9, 1, 1.1, 1.2, 1.2], fest=3.0, wed=1.2, q=(4, .5, .5, 20)),
    "Canteen/Mess": dict(n=12, p=0.36, dow=[1.2, 1.2, 1.2, 1.2, 1.0, .1, .05], fest=0.3, wed=1.0, q=(10, .45, 2, 40)),
    "Banquet/Event Hall": dict(n=8, p=0.12, dow=[.5, .5, .6, .8, 1.4, 2.0, 1.8], fest=1.6, wed=2.2, q=(45, .55, 10, 200)),
}
assert sum(v["n"] for v in CAT.values()) == 128
ZONE_W = {
    "Restaurant": [.28, .16, .16, .22, .14, .04], "Bakery": [.25, .15, .12, .20, .20, .08],
    "Caterer": [.20, .20, .05, .30, .15, .10], "Residential Society": [.25, .05, .35, .15, .20, 0.0],
    "Sweet Shop": [.30, .15, 0.0, .35, .15, .05], "Canteen/Mess": [.20, .20, .10, .30, .20, 0.0],
    "Banquet/Event Hall": [.20, .10, .30, .20, .20, 0.0]}
HOURS_MIX = {  # (weight, mean hour, sd, lo, hi)
    "Restaurant": [(.25, 15.7, .5, 14.5, 17.5), (.75, 22.6, .6, 21.5, 23.8)],
    "Bakery": [(.8, 20.8, .6, 19.5, 22.5), (.2, 13.5, 1.0, 12, 16)],
    "Caterer": [(.45, 15.0, 1.0, 13, 17), (.55, 22.5, .8, 21, 23.8)],
    "Residential Society": [(.4, 14.5, 1.2, 12.5, 17), (.6, 21.5, 1.0, 19.5, 23.5)],
    "Sweet Shop": [(.7, 21.0, .8, 19, 23), (.3, 15, 1.0, 13, 17)],
    "Canteen/Mess": [(.6, 15.3, .5, 14.5, 16.5), (.4, 20.8, .5, 20, 22)],
    "Banquet/Event Hall": [(.8, 22.8, .7, 21, 23.9), (.2, 15.5, .8, 14, 17)]}
FOOD_MIX = {
    "Restaurant": {"Cooked Meals": .65, "Snacks & Fast Food": .30, "Fruits & Raw Produce": .05},
    "Bakery": {"Bread & Bakery": .50, "Cakes & Pastries": .33, "Snacks & Fast Food": .12, "Packaged/Dry Food": .05},
    "Caterer": {"Cooked Meals": .85, "Sweets & Mithai": .08, "Snacks & Fast Food": .07},
    "Residential Society": {"Cooked Meals": .75, "Sweets & Mithai": .15, "Snacks & Fast Food": .10},
    "Sweet Shop": {"Sweets & Mithai": .75, "Snacks & Fast Food": .15, "Packaged/Dry Food": .10},
    "Canteen/Mess": {"Cooked Meals": .80, "Snacks & Fast Food": .15, "Fruits & Raw Produce": .05},
    "Banquet/Event Hall": {"Cooked Meals": .80, "Sweets & Mithai": .10, "Snacks & Fast Food": .10}}
NONVEG_P = {"Restaurant": .35, "Caterer": .30, "Banquet/Event Hall": .40, "Canteen/Mess": .15}
REASON_MIX = {
    "Restaurant": {"Overproduction vs Demand": .35, "Unsold at Closing/End of Day": .35,
                   "Order Cancellation": .08, "Low Footfall/Attendance": .22},
    "Bakery": {"Unsold at Closing/End of Day": .70, "Near Best-Before": .20, "Overproduction vs Demand": .10},
    "Caterer": {"Guest Count Lower Than Estimated": .45, "Over-Estimation of Quantity": .35,
                "Event Cancelled/Shortened": .08, "Order Cancellation": .12},
    "Residential Society": {"Over-Estimation of Quantity": .50, "Festival Over-Stocking/Celebration": .35,
                            "Guest Count Lower Than Estimated": .15},
    "Sweet Shop": {"Unsold at Closing/End of Day": .40, "Near Best-Before": .25,
                   "Festival Over-Stocking/Celebration": .25, "Order Cancellation": .10},
    "Canteen/Mess": {"Low Footfall/Attendance": .50, "Overproduction vs Demand": .35,
                     "Event Cancelled/Shortened": .15},
    "Banquet/Event Hall": {"Guest Count Lower Than Estimated": .50, "Over-Estimation of Quantity": .30,
                           "Event Cancelled/Shortened": .20}}
ITEMS = {
    "Cooked Meals": (["Rice", "Dal", "Mixed Veg Sabzi", "Roti/Chapati", "Veg Pulao", "Khichdi",
                      "Paneer Curry", "Rajma/Chole", "Veg Biryani"], ["Chicken Curry", "Chicken Biryani", "Egg Curry"]),
    "Snacks & Fast Food": (["Samosa", "Vada Pav", "Veg Sandwich", "Pav Bhaji", "Fried Rice/Noodles", "Veg Puff"],
                           ["Chicken Roll", "Chicken Sandwich"]),
    "Bread & Bakery": (["Pav", "Sliced Bread", "Buns", "Khari/Toast", "Dinner Rolls"], []),
    "Cakes & Pastries": (["Plain Cake Slices", "Pastries", "Muffins", "Cookies"], []),
    "Sweets & Mithai": (["Laddoo", "Barfi", "Jalebi", "Gulab Jamun", "Peda", "Halwa"], []),
    "Packaged/Dry Food": (["Biscuits", "Rusk", "Chikki", "Namkeen Packets"], []),
    "Fruits & Raw Produce": (["Cut Fruit", "Salad", "Whole Fruit", "Raw Vegetables"], [])}
FOOD_PARAM = {  # shelf-life range (h), prep lag range before report (h), portion kg, class
    "Cooked Meals": ((4, 6), (0.5, 3), .35, "High"), "Snacks & Fast Food": ((4, 6), (0.5, 3), .15, "High"),  # FSSAI: cooked food 4-6 h at room temp
    "Bread & Bakery": ((24, 48), (6, 14), .10, "Medium"), "Cakes & Pastries": ((12, 36), (6, 20), .10, "Medium"),
    "Sweets & Mithai": ((12, 48), (6, 30), .06, "Medium"), "Packaged/Dry Food": ((120, 400), (24, 100), .08, "Low"),
    "Fruits & Raw Produce": ((12, 30), (2, 10), .15, "Medium")}
ITEM_SHELF = {"Cut Fruit": (18, 24), "Salad": (18, 24), "Whole Fruit": (24, 48), "Raw Vegetables": (24, 48)}  # FSSAI table: cut fruit 24 h, fresh produce 1-2 days
FEST_QTY = {"Residential Society": 1.5, "Caterer": 1.1, "Sweet Shop": 1.3}

# donor table -------------------------------------------------------------------
donors, dparams = [], {}
did = 0
for cat in DONOR_CATEGORIES:
    qmults = rng.lognormal(0, 0.35, CAT[cat]["n"])
    terc = np.quantile(qmults, [1 / 3, 2 / 3])
    for k in range(CAT[cat]["n"]):
        did += 1
        zone = rng.choice(ZONES, p=ZONE_W[cat])
        lat, lon = jitter(zone)
        if rng.random() < 0.55:
            onb = START
        else:
            onb = START + timedelta(days=int(rng.integers(1, 305)))
        wd = None
        if rng.random() < 0.08:
            wd = date(2026, 3, 1) + timedelta(days=int(rng.integers(0, 213)))
            wd = max(wd, onb + timedelta(days=60))
        if cat == "Residential Society":
            fs = "Not Applicable"
        else:
            fs = rng.choice(["Yes", "Pending", "No"], p=[.88, .07, .05])
        size = "Small" if qmults[k] < terc[0] else ("Medium" if qmults[k] < terc[1] else "Large")
        d_id = f"D{did:03d}"
        donors.append(dict(
            donor_id=d_id, donor_name=f"Demo {cat} {k + 1:02d}", donor_category=cat, sub_area=zone,
            latitude=lat, longitude=lon, donor_size_class=size, fssai_license_declared=fs,
            onboarded_date=onb, donor_status="Withdrawn" if wd else "Active", withdrawn_date=wd,
            reporting_channel=rng.choice(["Phone Call", "Messaging Form", "Walk-in Desk"], p=[.35, .55, .10]),
            data_label=DATA_LABEL))
        dparams[d_id] = dict(cat=cat, act=rng.gamma(3, 1 / 3), qm=qmults[k], onb=onb, wd=wd,
                             xy=(lat, lon), zone=zone)
donors = pd.DataFrame(donors)

# ----------------------------------------------------------------------------- recipients
REC_TYPES = {  # windows, capacity range, veg-only probability
    "Community Kitchen": ([(12.0, 15.0), (19.0, 22.0)], (150, 400), .40),
    "Night Shelter": ([(19.5, 23.9)], (60, 150), .15),
    "Children's Home": ([(12.0, 14.0), (18.5, 21.0)], (40, 120), .55),
    "Old-Age Home": ([(11.5, 13.5), (18.0, 20.5)], (30, 80), .65),
    "Street Community Group": ([(15.0, 17.0), (20.0, 23.5)], (80, 250), .20),
    "Informal Settlement Resident Group": ([(11.0, 16.0), (19.0, 22.5)], (100, 300), .25)}
REC_ZONE_N = {"Dharavi Fringe": 9, "Mahim": 5, "Matunga": 5, "Dadar East": 3, "Dadar West": 2, "Shivaji Park": 1}
REC_TYPE_P = {"Dharavi Fringe": [.25, .10, .10, .05, .20, .30], "Mahim": [.30, .20, .15, .10, .15, .10],
              "Matunga": [.25, .15, .20, .20, .10, .10], "Dadar East": [.30, .30, .20, .10, .10, 0.0],
              "Dadar West": [.20, .30, .20, .30, 0.0, 0.0], "Shivaji Park": [.2, .1, .4, .3, 0.0, 0.0]}


def hhmm(h):
    return f"{int(h):02d}:{int(round((h % 1) * 60)) % 60:02d}"


recs, rparams = [], {}
rid = 0
for zone, n in REC_ZONE_N.items():
    for _ in range(n):
        rid += 1
        rtype = rng.choice(list(REC_TYPES), p=REC_TYPE_P[zone])
        wins, (c0, c1), vegp = REC_TYPES[rtype]
        lat, lon = jitter(zone, 0.0022)
        cap = int(round(rng.integers(c0, c1 + 1), -1))
        veg_only = rng.random() < vegp
        cooked = rng.random() < .90
        r_id = f"R{rid:02d}"
        w2 = wins[1] if len(wins) > 1 else (None, None)
        recs.append(dict(
            recipient_id=r_id, recipient_name=f"Demo {rtype} {rid:02d}", recipient_type=rtype, sub_area=zone,
            latitude=lat, longitude=lon, daily_capacity_portions=cap,
            window1_start=hhmm(wins[0][0]), window1_end=hhmm(wins[0][1]),
            window2_start=hhmm(w2[0]) if w2[0] else None, window2_end=hhmm(w2[1]) if w2[1] else None,
            accepts_cooked_food="Yes" if cooked else "No", diet_acceptance="Veg-only" if veg_only else "Any",
            has_cold_storage="Yes" if rng.random() < .2 else "No",
            fssai_registration_status=rng.choice(["Declared Registered", "Not Declared"], p=[.6, .4]),
            verification_status="SYNTHETIC - not a real organisation", data_label=DATA_LABEL))
        rparams[r_id] = dict(xy=(lat, lon), cap=cap, wins=wins, cooked=cooked, veg=veg_only)
recs = pd.DataFrame(recs)

# ----------------------------------------------------------------------------- volunteers
SHIFT_H = {"Morning": (7, 14), "Afternoon": (13, 19.5), "Evening": (17.5, 22.5), "Late": (21, 24)}
VEH = {"On foot": (8, 12.0), "Bicycle": (15, 6.0), "Two-wheeler": (35, 4.2), "Four-wheeler": (250, 5.0)}
vol_shifts = ["Morning"] * 8 + ["Afternoon"] * 12 + ["Evening"] * 11 + ["Late"] * 5
vol_veh = rng.permutation(["On foot"] * 6 + ["Bicycle"] * 5 + ["Two-wheeler"] * 18 + ["Four-wheeler"] * 7)
vol_zone = rng.choice(ZONES, size=36, p=[.22, .14, .12, .22, .20, .10])
vols, vparams = [], {}
for i in range(36):
    zone = vol_zone[i]
    lat, lon = jitter(zone, 0.0025)
    onb = START if rng.random() < .6 else START + timedelta(days=int(rng.integers(1, 180)))
    avail = rng.choice(["Weekdays", "Weekends", "All Days"], p=[.35, .25, .40])
    v_id = f"V{i + 1:02d}"
    vols.append(dict(volunteer_id=v_id, volunteer_name=f"Demo Volunteer {i + 1:02d}", home_sub_area=zone,
                     home_latitude=lat, home_longitude=lon, shift=vol_shifts[i], availability_days=avail,
                     vehicle_mode=vol_veh[i], max_load_kg=float(VEH[vol_veh[i]][0]),
                     fostac_trained="Yes" if rng.random() < .65 else "No", onboarded_date=onb,
                     data_label=DATA_LABEL))
    vparams[v_id] = dict(xy=(lat, lon), shift=SHIFT_H[vol_shifts[i]], avail=avail, veh=vol_veh[i],
                         load=VEH[vol_veh[i]][0], mpk=VEH[vol_veh[i]][1], onb=onb)
vols = pd.DataFrame(vols)

# volunteer-day availability matrix (rain reduces availability)
vol_ids = list(vparams)
VAV = np.zeros((36, ND), dtype=bool)
for vi, v in enumerate(vol_ids):
    vp = vparams[v]
    for di, d in enumerate(DAYS):
        if d < vp["onb"]:
            continue
        ok = (vp["avail"] == "All Days") or (vp["avail"] == "Weekdays" and d.weekday() < 5) or \
             (vp["avail"] == "Weekends" and d.weekday() >= 5)
        p = .62 * (.8 if RAINLV[di] == "Light/Moderate" else .6 if RAINLV[di] == "Heavy" else 1.0)
        VAV[vi, di] = ok and rng.random() < p

# ----------------------------------------------------------------------------- surplus records
def sample_hour(cat):
    mix = HOURS_MIX[cat]
    w = np.array([m[0] for m in mix])
    m = mix[rng.choice(len(mix), p=w / w.sum())]
    while True:
        h = rng.normal(m[1], m[2])
        if m[3] <= h <= m[4]:
            return h


def choose(d):
    keys = list(d)
    p = np.array([d[k] for k in keys], dtype=float)
    return keys[rng.choice(len(keys), p=p / p.sum())]


sur = []
for d_id, dp in dparams.items():
    cat, cp = dp["cat"], CAT[dp["cat"]]
    for di, d in enumerate(DAYS):
        if d < dp["onb"] or (dp["wd"] and d > dp["wd"]):
            continue
        p = cp["p"] * dp["act"] * cp["dow"][DOW[di]]
        if FEST[di]:
            p *= cp["fest"]
        if WED[di]:
            p *= cp["wed"]
        p = min(p, .95)
        if rng.random() >= p:
            continue
        nrec = 2 if (cat in ("Restaurant", "Caterer", "Banquet/Event Hall", "Sweet Shop") and rng.random() < .12) else 1
        used = set()
        for _ in range(nrec):
            fcat = choose(FOOD_MIX[cat])
            if fcat in used and len(FOOD_MIX[cat]) > 1:
                fcat = choose({k: v for k, v in FOOD_MIX[cat].items() if k not in used})
            used.add(fcat)
            veg_items, nv_items = ITEMS[fcat]
            nonveg = bool(nv_items) and rng.random() < NONVEG_P.get(cat, 0)
            item = str(rng.choice(nv_items if nonveg else veg_items))
            (smin, smax), (lmin, lmax), portion, pclass = FOOD_PARAM[fcat]
            shelf = round(float(rng.uniform(smin, smax)), 1)
            if item in ("Barfi", "Peda", "Gulab Jamun"):
                shelf = round(float(rng.uniform(12, 30)), 1)  # assumption (milk-based sweets)
            if item in ITEM_SHELF:
                shelf = round(float(rng.uniform(*ITEM_SHELF[item])), 1)
            lag = min(float(rng.uniform(lmin, lmax)), 0.6 * shelf)
            hr = sample_hour(cat)
            rep = datetime(d.year, d.month, d.day) + timedelta(hours=hr)
            rep = rep.replace(second=0, microsecond=0)
            prep = (rep - timedelta(hours=lag)).replace(second=0, microsecond=0)
            q0, sig, qmin, qmax = cp["q"]
            q = q0 * dp["qm"] * math.exp(rng.normal(0, sig))
            if FEST[di]:
                q *= FEST_QTY.get(cat, 1.0)
            if WED[di] and cat in ("Caterer", "Banquet/Event Hall"):
                q *= 1.25
            q = round(float(min(max(q, qmin), qmax)), 1)
            rmix = dict(REASON_MIX[cat])
            if cat == "Restaurant" and RAINLV[di] != "No Rain":
                rmix["Low Footfall/Attendance"] *= 3
            if cat in ("Sweet Shop", "Residential Society") and FEST[di]:
                rmix["Festival Over-Stocking/Celebration"] = rmix.get("Festival Over-Stocking/Celebration", .05) * 3
            reason = choose(rmix)
            if reason == "Near Best-Before" and fcat in ("Cooked Meals",):
                reason = "Overproduction vs Demand"
            if fcat == "Packaged/Dry Food":
                pack = "Original Sealed Packet"
            elif fcat == "Cooked Meals":
                pack = str(rng.choice(["Open/Bulk Container", "Sealed Container"], p=[.55, .45]))
            else:
                pack = str(rng.choice(["Boxed", "Sealed Container", "Open/Bulk Container"], p=[.5, .3, .2]))
            stor = "Hot-Held" if fcat in ("Cooked Meals", "Snacks & Fast Food") and rng.random() < .7 else \
                   ("Refrigerated" if fcat == "Cakes & Pastries" and rng.random() < .5 else "Room Temperature")
            sur.append(dict(
                donor_id=d_id, report_datetime=rep, prep_datetime=prep, food_category=fcat, food_item=item,
                diet_type="Non-Veg" if nonveg else "Veg", quantity_kg=q,
                est_portions=max(1, int(round(q / portion * rng.uniform(.9, 1.1)))), portion_size_kg=portion,
                surplus_reason=reason, packaging_type=pack, storage_condition=stor,
                declared_safe_window_hours=shelf, perishability_class=pclass, data_label=DATA_LABEL))
sur = pd.DataFrame(sur).sort_values(["report_datetime", "donor_id"]).reset_index(drop=True)
sur.insert(0, "surplus_id", [f"S{i + 1:06d}" for i in range(len(sur))])

# ----------------------------------------------------------------------------- collections
dxy = {k: v["xy"] for k, v in dparams.items()}
date_idx = {d: i for i, d in enumerate(DAYS)}
pickups_today = {}
cols = []
for r in sur.itertuples(index=False):
    d0 = r.report_datetime.date()
    di = date_idx[d0]
    cat = dparams[r.donor_id]["cat"]
    expiry = r.prep_datetime + timedelta(hours=r.declared_safe_window_hours)
    base = dict(surplus_id=r.surplus_id, volunteer_id=None, assigned_datetime=None, pickup_datetime=None,
                qty_collected_kg=0.0, collection_distance_km=None, partial_reason=None,
                rejection_reason=None, data_label=DATA_LABEL)
    if rng.random() < (0.06 if cat == "Residential Society" else 0.03):
        cols.append({**base, "collection_status": "Cancelled by Donor"})
        continue
    ack = timedelta(minutes=float(rng.lognormal(math.log(6), .6)))
    assigned = (r.report_datetime + ack).replace(second=0, microsecond=0)
    hour = assigned.hour + assigned.minute / 60
    cands, wts = [], []
    for vi, v in enumerate(vol_ids):
        vp = vparams[v]
        if not VAV[vi, di] or pickups_today.get((v, d0), 0) >= 4:
            continue
        lo, hi = vp["shift"]
        if not (lo <= hour <= hi):
            continue
        dist = road_km(vp["xy"], dxy[r.donor_id])
        w = 1.0 / (dist + 0.6)
        w *= 4.0 if vp["load"] >= r.quantity_kg else 1.0
        cands.append(v)
        wts.append(w)
    if not cands or rng.random() < (0.06 + (0.06 if RAINLV[di] != "No Rain" else 0)):
        cols.append({**base, "collection_status": "Missed - No Volunteer Available"})
        continue
    wts = np.array(wts)
    v = cands[rng.choice(len(cands), p=wts / wts.sum())]
    vp = vparams[v]
    pickups_today[(v, d0)] = pickups_today.get((v, d0), 0) + 1
    dist = road_km(vp["xy"], dxy[r.donor_id])
    rain_f = 1.0 if RAINLV[di] == "No Rain" else 1.25
    mob = float(rng.lognormal(math.log(10), .7)) + (12 if RAINLV[di] == "Light/Moderate" else
                                                     25 if RAINLV[di] == "Heavy" else 0)
    mob += 20 if vp["shift"] == (21, 24) else 0
    # occasional long delay (volunteer stuck in traffic / double-booked); more likely in heavy rain
    if rng.random() < (0.10 if RAINLV[di] == "Heavy" else 0.045):
        mob += float(rng.uniform(60, 240))
    arrive = assigned + timedelta(minutes=mob + dist * vp["mpk"] * rain_f + 5)
    arrive = arrive.replace(second=0, microsecond=0)
    common = {**base, "volunteer_id": v, "assigned_datetime": assigned, "pickup_datetime": arrive,
              "collection_distance_km": round(dist, 2)}
    if arrive > expiry:
        cols.append({**common, "collection_status": "Missed - Arrived Beyond Safe Window"})
        continue
    frac = (arrive - r.prep_datetime).total_seconds() / 3600 / r.declared_safe_window_hours
    if rng.random() < 0.015 + 0.10 * frac ** 2:
        reason = str(rng.choice(["Time-temperature concern (volunteer judgement)",
                                 "Visible spoilage or off-smell (volunteer judgement)",
                                 "Packaging damaged/contaminated (volunteer judgement)"], p=[.5, .3, .2]))
        cols.append({**common, "collection_status": "Rejected - Failed Volunteer Safety Check",
                     "rejection_reason": reason})
        continue
    qty, status, pr = r.quantity_kg, "Collected - Full", None
    if qty > vp["load"]:
        qty, status, pr = float(vp["load"]), "Collected - Partial", "Vehicle/Load Capacity"
    elif rng.random() < 0.05:
        qty, status, pr = round(qty * float(rng.uniform(.5, .9)), 1), "Collected - Partial", "Donor Released Less"
    cols.append({**common, "collection_status": status, "qty_collected_kg": round(qty, 1), "partial_reason": pr})
col = pd.DataFrame(cols)
col.insert(0, "collection_id", [f"C{i + 1:06d}" for i in range(len(col))])

# ----------------------------------------------------------------------------- distributions
rec_ids = list(rparams)
rd_km = {(d, r): road_km(dxy[d], rparams[r]["xy"]) for d in dxy for r in rec_ids}
used_cap = {}
sur_i = sur.set_index("surplus_id")
dist_rows = []


def next_slot(wins, arrive):
    """Earliest time >= arrive inside a recipient window on arrive's date; None if no window left that day."""
    h = arrive.hour + arrive.minute / 60
    for s, e in wins:
        if s <= h <= e:
            return arrive
        if h < s:
            t = datetime(arrive.year, arrive.month, arrive.day) + timedelta(hours=s + float(rng.uniform(0, .25)))
            return t.replace(second=0, microsecond=0)
    return None


for c in col.itertuples(index=False):
    if c.qty_collected_kg <= 0:
        continue
    s = sur_i.loc[c.surplus_id]
    v = vparams[c.volunteer_id]
    expiry = s.prep_datetime + timedelta(hours=s.declared_safe_window_hours)
    ready = c.pickup_datetime
    remaining, rows, excl = float(c.qty_collected_kg), [], set()
    waste_reason = None
    for _ in range(2):
        if remaining <= 0.05:
            break
        best, best_score, flags = None, 1e9, dict(type=False, window=False, cap=False)
        for rid_ in rec_ids:
            rp = rparams[rid_]
            if rid_ in excl:
                continue
            if (s.diet_type == "Non-Veg" and rp["veg"]) or (s.food_category == "Cooked Meals" and not rp["cooked"]):
                continue
            flags["type"] = True
            km = rd_km[(s.donor_id, rid_)]
            arrive = ready + timedelta(minutes=km * v["mpk"] + float(rng.uniform(5, 12)))
            t = next_slot(rp["wins"], arrive)
            if t is None or t > expiry:
                continue
            flags["window"] = True
            left = rp["cap"] - used_cap.get((rid_, t.date()), 0)
            if left < max(5, remaining / s.portion_size_kg * 0.15):
                continue
            flags["cap"] = True
            score = ((t - arrive).total_seconds() / 3600) * 2 + km
            score *= float(rng.uniform(.85, 1.15))
            if score < best_score:
                best, best_score, best_t, best_km, best_left = rid_, score, t, km, left
        if best is None:
            waste_reason = ("No Recipient Accepts Food Type/Diet" if not flags["type"] else
                            "No Recipient Window Within Safe Time" if not flags["window"] else
                            "Recipient Capacity Exhausted")
            break
        alloc = min(remaining, best_left * s.portion_size_kg)
        alloc = round(alloc, 1)
        if alloc <= 0:
            waste_reason = "Recipient Capacity Exhausted"
            break
        servings = int(alloc / s.portion_size_kg)
        used_cap[(best, best_t.date())] = used_cap.get((best, best_t.date()), 0) + servings
        rows.append(dict(recipient_id=best, distribution_datetime=best_t, qty=alloc, servings=servings,
                         km=round(best_km, 2)))
        excl.add(best)
        remaining = round(remaining - alloc, 1)
    if remaining > 0.05 and waste_reason is None:
        waste_reason = "Recipient Capacity Exhausted"
    # occasional quality loss on the last delivered row (volunteer/recipient check at hand-over)
    handling_loss = 0.0
    if rows and rng.random() < 0.03:
        handling_loss = round(rows[-1]["qty"] * float(rng.uniform(.1, .4)), 1)
        rows[-1]["qty"] = round(rows[-1]["qty"] - handling_loss, 1)
        rows[-1]["servings"] = int(rows[-1]["qty"] / s.portion_size_kg)
    total_waste = round(float(c.qty_collected_kg) - sum(r_["qty"] for r_ in rows), 1)
    if not rows:
        dist_rows.append(dict(collection_id=c.collection_id, recipient_id=None, distribution_datetime=None,
                              qty_distributed_kg=0.0, beneficiaries_served=0, transport_distance_km=None,
                              wastage_kg=total_waste, wastage_reason=waste_reason,
                              distribution_status="Not Delivered"))
        continue
    for i, r_ in enumerate(rows):
        last = i == len(rows) - 1
        wr = None
        if last and total_waste > 0.04:
            wr = waste_reason if (remaining > 0.05) else "Quality Loss During Handling"
        dist_rows.append(dict(collection_id=c.collection_id, recipient_id=r_["recipient_id"],
                              distribution_datetime=r_["distribution_datetime"],
                              qty_distributed_kg=r_["qty"], beneficiaries_served=r_["servings"],
                              transport_distance_km=r_["km"], wastage_kg=total_waste if last else 0.0,
                              wastage_reason=wr, distribution_status="Delivered"))
dist = pd.DataFrame(dist_rows)
dist["handover_record_complete"] = np.where(rng.random(len(dist)) < .94, "Yes", "No")
dist["data_label"] = DATA_LABEL
dist.insert(0, "distribution_id", [f"X{i + 1:06d}" for i in range(len(dist))])

# ----------------------------------------------------------------------------- write RAW csvs (with realistic entry noise)
def noisy(series, frac=0.025):
    s = series.astype("object").copy()
    idx = rng.choice(len(s), size=int(len(s) * frac), replace=False)
    for i in idx:
        v = str(s.iloc[i])
        mode = rng.integers(0, 4)
        s.iloc[i] = (v.upper() if mode == 0 else v.lower() if mode == 1 else f" {v} " if mode == 2
                     else v.replace("&", "and"))
    return s


def blank(series, frac):
    s = series.astype("object").copy()
    s.iloc[rng.choice(len(s), size=int(len(s) * frac), replace=False)] = np.nan
    return s


sur_raw, don_raw, col_raw = sur.copy(), donors.copy(), col.copy()
for c in ("food_category", "surplus_reason"):
    sur_raw[c] = noisy(sur_raw[c])
sur_raw["packaging_type"] = blank(sur_raw["packaging_type"], .03)
sur_raw["storage_condition"] = blank(sur_raw["storage_condition"], .02)
don_raw["sub_area"] = noisy(don_raw["sub_area"], .04)

ensure_dirs()
tables = dict(donors=don_raw, recipients=recs, volunteers=vols, daily_context=ctx,
              surplus_records=sur_raw, collections=col, distributions=dist)
for name, df in tables.items():
    cols_expected = [c[0] for c in TABLES[name]]
    df = df[cols_expected]
    df.to_csv(RAW / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"{name:16s} rows={len(df):6d}")

dd = pd.DataFrame([(t, *row) for t, rows in TABLES.items() for row in rows],
                  columns=["table", "column", "data_type", "description", "allowed_values_or_range", "nullable"])
dd.to_csv(DATA / "data_dictionary.csv", index=False)
print("data dictionary rows:", len(dd))
