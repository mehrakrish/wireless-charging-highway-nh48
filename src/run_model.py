"""
Lane wander, utilization and local supply of a wireless-charging highway section.
Case study: NH-48 (old Mumbai-Pune highway), 10 km around Somatne Phata toll plaza, Maharashtra.

Questions
  Q1  How do coil size, coverage, switch-on threshold and real lane wander set the energy each vehicle class
      receives per km, and the efficiency?            (layer 1: coupler_layer.py, validated physics)
  Q2  What hourly electricity demand does the section create, including the road's own loads?  (layer 2)
  Q3  What mix of right-of-way solar, battery and grid supplies it at least cost; how much is self-supplied;
      what does a kWh delivered to a vehicle cost; how much CO2 is avoided?        (layer 3: optimiser.py)
  Q4  How wrong is planning that assumes centred vehicles?
  Q5  How many equipped heavy vehicles make the road competitive; which inputs matter; how uncertain is it?
  Q6  Braking-zone harvesting at the toll plaza.

Every input is listed with its source in docs/DATA_SOURCES.md.
Run from the repository root:  python src/run_model.py data/weather/<folder>/<Pune TMYx>.epw
"""
import csv
import json
import os
import sys
import numpy as np
import corridor
from corridor import (CLASSES, wpt_demand, installed_power_per_km, infra_load, class_physics,
                      corridor_peak_power, hourly_flow, daily_counts)
import coupler_layer
from optimiser import solve, crf
from pv_model import per_kwp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # repository root (src/ is one level down)
RES = os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)

# =============================================================================================== INPUTS
RS_PER_USD, RS_PER_RMB, RS_PER_CAD = 85.0, 12.0, 62.0     # A: Rs 85/USD (IEEFA-JMK 2026); RMB 7.1/USD; CAD 1.37/USD

VEH = {   # data/INPUTS.md section 9.  "bus" = MSRDC category C "Bus/Truck" (two-axle buses and trucks)
    "car": dict(kwh_km=0.130, speed=100, gap=0.150, n_rx=1, sigma=0.25),
    "lcv": dict(kwh_km=0.138, speed=80, gap=0.150, n_rx=1, sigma=0.25),
    "bus": dict(kwh_km=1.00, speed=80, gap=0.250, n_rx=3, sigma=0.25),
    "mav": dict(kwh_km=1.40, speed=80, gap=0.250, n_rx=4, sigma=0.25),
}
SPEED_LIMIT = {c: VEH[c]["speed"] for c in CLASSES}
# Equipped fleet shares in the electrified lane (explicit scenario assumptions, not forecasts).  For reference,
# NITI Aayog-RMI (2019) 2030 *sales* targets are 30 % private cars, 70 % commercial cars, 40 % buses; electric
# trucks were ~0.75 % of 2024 sales (NITI Aayog 2025).  Fleet shares lag sales shares.
SCENARIOS = {
    "low": dict(car=0.05, lcv=0.10, bus=0.10, mav=0.02),
    "mid": dict(car=0.15, lcv=0.30, bus=0.25, mav=0.10),
    "high": dict(car=0.30, lcv=0.60, bus=0.50, mav=0.30),
}
LANE_SHARE = dict(car=0.30, lcv=1.0, bus=1.0, mav=1.0)   # A: heavy vehicles keep left; 30 % of cars in that lane
L_SECTION = 10.0                                         # km of highway modelled
L_E = L_SECTION                                          # km of each carriageway's left lane electrified
LANE_KM = 2 * L_E                                        # both directions
ETA_PE = 0.86       # power electronics outside the coils: grid rectifier (0.97, A) x road inverter and vehicle rectifier
                    # (0.885), chosen so that coil-to-coil (~0.96) x 0.885 = 0.85, the measured roadway-DC-bus-to-
                    # vehicle-DC-bus efficiency (Purdue US-231, JTRP-2026/18; Electreon 2020: 85 %)
P_RX = 25.0                                              # kW per receiver (Electreon 2020)
PV_KWP_PER_KM = 515.0   # A: one 2.2 m single-row strip along the right-of-way per km (4.27 m2/kWp at latitude tilt)

COST = dict(   # data/INPUTS.md sections 3-7 (real 2026 Rs)
    r=0.050,           # real: CERC nominal 9.21 % deflated by RBI's 4 % CPI target: 1.0921/1.04 - 1 = 5.0 %
    capex_pv=33579 * 1.25, om_pv=1096, life_pv=25, degr_pv=0.0133,
    capex_be=9775 / 0.80, om_be_frac=0.015, capex_bp=0.0, life_bat=12, rte=0.85,
    capex_grid=10000, demand_charge=0.0, life_grid=25,
    tariff_base=9.73, tod=False,   # MERC Case 75/2025, p.100: HT IX EV charging FY2026-27: EC 8.92 + wheeling 0.81 Rs/kVAh, no demand charge
    tod_solar_rebate=(0.15, 0.25), tod_peak=0.20, tose=0.2894,
    # road hardware, per lane-metre: Li et al. (Energies 2022) costs are for two-way construction -> halved
    coil_rs_per_m=1896 / 2 * RS_PER_RMB, civil_rs_per_m=828 / 2 * RS_PER_RMB, w_ref=0.60,
    inv_rs_per_kw=12500, switch_rs_per_coil=5000.0, dist_ratio=1.01 / 2.23,
    dwpt_om_rs_per_lane_km=17500 / 2 * RS_PER_CAD, life_dwpt=15,
    section_m=100.0, p_exceed=1e-3, cost_mult_dwpt=1.0,
)
CO2_GRID, CO2_CM = 0.675, 0.705   # tCO2/MWh, CEA v22 FY2025-26: weighted average (emitted), combined margin (avoided)
INFRA = dict(light_kw_per_km=0.0, toll_kw=0.0, atms_kw_per_km=0.10, L_section=L_SECTION)
SITE = dict(lat=18.72, lon=73.68, alt=600)          # Somatne Phata (approx.), for solar position / dark hours
ETA_ONS = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95)
DESIGNS = [dict(lam=lam, pitch=0.4 * lam / cov, eta_on=eo, P_rx=P_RX, cov=cov)
           for lam in (1.0, 1.25, 1.5, 2.0) for cov in (1.0, 0.8, 0.67, 0.5) for eo in ETA_ONS]


def key(d):
    return (d["lam"], d["cov"], d["eta_on"])


def tariff_hourly():
    """MSEDCL EV-charging tariff (Rs/kWh) for each hour, incl. tax on sale.  Base: flat Rs 9.73 (MERC order; the only
    confirmed figure); COST['tod'] = True applies the general ToD structure (sensitivity)."""
    t = np.zeros(8760)
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    h = 0
    for m, nd in enumerate(days, start=1):
        rebate = COST["tod_solar_rebate"][0] if 4 <= m <= 9 else COST["tod_solar_rebate"][1]
        for _ in range(nd):
            for hr in range(24):
                f = 1.0
                if COST["tod"]:
                    if 9 <= hr < 17:
                        f -= rebate
                    elif hr >= 17:
                        f += COST["tod_peak"]
                t[h] = COST["tariff_base"] * f + COST["tose"]
                h += 1
    return t


def dwpt_annual(design, scen, phys):
    """Annualised cost of the road hardware for all lane-km:
       coils (coverage x width), per-coil solid-state switches and detection, civil works, inverters (compound-
       Poisson sizing), power distribution along the road (Purdue ratio to the charging system), O&M."""
    D = 0.4 * design["lam"]
    coverage = min(D / design["pitch"], 1.0)
    coil = COST["coil_rs_per_m"] * 1e3 * coverage * D / COST["w_ref"]
    switches = COST["switch_rs_per_coil"] * 1e3 / design["pitch"]
    civil = COST["civil_rs_per_m"] * 1e3
    kw, mean_rx, n_star = installed_power_per_km(design, VEH, scen, LANE_SHARE, section_m=COST["section_m"],
                                                 p_exceed=COST["p_exceed"], phys=phys)
    inv = COST["inv_rs_per_kw"] * kw
    dist = COST["dist_ratio"] * (coil + switches + inv)
    m = COST["cost_mult_dwpt"]
    per_km = (coil + switches + civil + inv + dist) * m
    capex = per_km * LANE_KM
    annual = crf(COST["r"], COST["life_dwpt"]) * capex + COST["dwpt_om_rs_per_lane_km"] * m * LANE_KM
    return annual, dict(capex_total=capex, per_lane_km=per_km, coil=coil * m, switches=switches * m, civil=civil * m,
                        inv=inv * m, dist=dist * m, inv_kw_per_lane_km=kw, n_star=n_star, coverage=coverage)


def dark_hours():
    """1 when the sun is below civil twilight (zenith > 96 deg) at mid-hour, else 0 (local time)."""
    import pandas as pd
    import pvlib
    t = pd.date_range("2023-01-01 00:30", periods=8760, freq="h", tz="Asia/Kolkata")
    z = pvlib.solarposition.get_solarposition(t, SITE["lat"], SITE["lon"], altitude=SITE["alt"])["zenith"].values
    return (z > 96.0).astype(float)


def provisional_pv():
    """PLACEHOLDER ONLY for testing when no weather file is supplied. Never used for reported results."""
    import pandas as pd
    import pvlib
    loc = pvlib.location.Location(SITE["lat"], SITE["lon"], tz="Asia/Kolkata", altitude=SITE["alt"])
    t = pd.date_range("2023-01-01 00:30", periods=8760, freq="h", tz="Asia/Kolkata")
    ghi = loc.get_clearsky(t).ghi.values
    f = np.where((t.month >= 6) & (t.month <= 9), 0.5, 0.75)
    y = ghi * f / 1000 * 0.80
    return y, dict(site="PROVISIONAL", yield_kwh_per_kwp=float(y.sum()), ghi_kwh_m2_yr=float((ghi * f).sum() / 1e3))


def evaluate(design, scen, y_pv, tariff, dark, phys=None, supply=True, pv_cap=None):
    """Full chain for one coil design and one adoption scenario. Returns a flat dict of results."""
    phys = class_physics(design, VEH) if phys is None else phys
    pv_cap = PV_KWP_PER_KM * L_SECTION if pv_cap is None else pv_cap
    dem_wpt, dlv, pc = wpt_demand(design, VEH, scen, L_E, ETA_PE, LANE_SHARE, phys=phys)
    dem_inf = infra_load(dark, INFRA)
    D = dem_wpt + dem_inf
    a_dwpt, dw = dwpt_annual(design, scen, phys)
    p_peak, p_mean_peak, t_peak = corridor_peak_power(design, VEH, scen, LANE_SHARE, L_E, ETA_PE, phys,
                                                       p_exceed=COST["p_exceed"])
    firm = p_peak + dem_inf[t_peak]
    r = dict(lam=design["lam"], cov=design["cov"], pitch=design["pitch"], eta_on=design["eta_on"],
             valid=all(phys[c]["pbar"] > 0 for c in CLASSES),
             E_delivered_MWh=dlv.sum() / 1e3, E_wpt_grid_MWh=dem_wpt.sum() / 1e3, E_infra_MWh=dem_inf.sum() / 1e3,
             peak_hourly_kW=D.max(), firm_kW=firm, dwpt_annual_Rs=a_dwpt, inv_kw_per_lane_km=dw["inv_kw_per_lane_km"],
             n_star=dw["n_star"], dwpt_capex_Rs=dw["capex_total"], road_cr_per_lane_km=dw["per_lane_km"] / 1e7,
             road_coil_share=dw["coil"] / dw["per_lane_km"], road_inv_share=(dw["inv"] + dw["dist"]) / dw["per_lane_km"],
             **{f"pbar_{c}": pc[c]["pbar"] for c in CLASSES}, **{f"eta_{c}": pc[c]["eta"] for c in CLASSES},
             **{f"cover_{c}": pc[c]["cover"] for c in CLASSES})
    grid_only = crf(COST["r"], COST["life_grid"]) * COST["capex_grid"] * max(D.max(), firm) + float(np.dot(tariff, D))
    r["supply_grid_only_Rs"] = grid_only
    share_wpt = dem_wpt.sum() / D.sum()
    E_del = max(dlv.sum(), 1e-9)
    if supply:
        o = solve(D, y_pv, tariff, COST, C_pv_max=pv_cap, firm_min=firm)
        r.update(C_pv_kWp=o["C_pv"], E_b_usable_kWh=o["E_b"], P_b_kW=o["P_b"], G_kW=o["G"],
                 supply_opt_Rs=o["annual_total"], self_supply=o["self_supply"], pv_curtailed=o["pv_curtailed"],
                 grid_import_MWh=o["g"].sum() / 1e3,
                 co2_t=o["g"].sum() / 1e3 * CO2_GRID, co2_grid_only_t=D.sum() / 1e3 * CO2_GRID,
                 co2_avoided_t=(D.sum() - o["g"].sum()) / 1e3 * CO2_CM,
                 lcod_Rs_kWh=(a_dwpt + o["annual_total"] * share_wpt) / E_del,
                 lcod_grid_only_Rs_kWh=(a_dwpt + grid_only * share_wpt) / E_del,
                 supply_cost_Rs_kWh=o["annual_total"] / D.sum(), supply_grid_only_Rs_kWh=grid_only / D.sum(),
                 road_share_of_cost=a_dwpt / (a_dwpt + o["annual_total"] * share_wpt))
    else:
        r["lcod_grid_only_Rs_kWh"] = (a_dwpt + grid_only * share_wpt) / E_del
    return r


def write_csv(rows, name):
    keys = list(rows[0].keys())
    with open(os.path.join(RES, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, (float, np.floating)) else v) for k, v in row.items()})


if __name__ == "__main__":
    LIT_KM, LUM_KW_PER_KM, TOLL_AVG_KW = 1.8, 67 * 0.180, 26.0
    if len(sys.argv) > 1:
        y_pv, t_air, pv_info = per_kwp(sys.argv[1])
    else:
        y_pv, pv_info = provisional_pv()
        print("WARNING: no weather file given -> PROVISIONAL solar profile (testing only)")
    y_pv = y_pv * np.mean((1 - COST["degr_pv"]) ** np.arange(COST["life_pv"]))   # lifetime-average degradation
    dark = dark_hours()
    toll_dark = 0.60 * TOLL_AVG_KW * 8760 / dark.sum()
    INFRA.update(light_kw_per_km=(LIT_KM * LUM_KW_PER_KM + toll_dark) / L_SECTION, toll_kw=0.40 * TOLL_AVG_KW)
    tariff = tariff_hourly()
    dc = daily_counts()
    traffic_info = {c: float(np.mean([dc[m][c] for m in dc])) for c in CLASSES}
    print("solar:", pv_info)
    print(f"dark hours/yr {dark.sum():.0f}; tariff mean {tariff.mean():.2f} Rs/kWh; mean daily traffic {traffic_info}")
    MID = SCENARIOS["mid"]

    # ======================================================================== physics table
    phys = {key(d): class_physics(d, VEH) for d in DESIGNS}
    phys0 = {key(d): class_physics(d, {c: dict(VEH[c], sigma=0.0) for c in CLASSES}) for d in DESIGNS}
    rowsA = []
    for d in DESIGNS:
        for c in CLASSES:
            p0, p1 = phys0[key(d)][c], phys[key(d)][c]
            rowsA.append(dict(lam=d["lam"], coil_mm=400 * d["lam"], cov=d["cov"], pitch_m=d["pitch"], eta_on=d["eta_on"],
                              cls=c, gap_mm=VEH[c]["gap"] * 1e3, pbar_aligned=p0["pbar"], eta_aligned=p0["eta"],
                              pbar_wander=p1["pbar"], eta_wander=p1["eta"],
                              pbar_loss_pct=(100 * (1 - p1["pbar"] / p0["pbar"]) if p0["pbar"] > 0 else float("nan")),
                              eta_loss_pts=100 * (p0["eta"] - p1["eta"])))
    write_csv(rowsA, "A_physics_wander.csv")
    print("A done")

    # ======================================================================== B. design sweep, mid scenario
    rowsB = [evaluate(d, MID, y_pv, tariff, dark, phys=phys[key(d)]) for d in DESIGNS]
    write_csv(rowsB, "B_design_sweep_mid.csv")
    valid = [r for r in rowsB if r["valid"]]
    best = min(valid, key=lambda r: r["lcod_Rs_kWh"])
    BEST = next(d for d in DESIGNS if key(d) == (best["lam"], best["cov"], best["eta_on"]))
    print("B done; best design:", {k: best[k] for k in ("lam", "cov", "pitch", "eta_on", "lcod_Rs_kWh")})

    # ======================================================================== C. centred-vehicle planning vs wander
    # Same model, but vehicles assumed centred (sigma = 0): what it predicts for each design vs the truth.
    rowsC = []
    for d, rb in zip(DESIGNS, rowsB):
        if not rb["valid"]:
            continue
        rc = evaluate(d, MID, y_pv, tariff, dark, phys=phys0[key(d)], supply=False)
        sup_per_kwh = rb["supply_opt_Rs"] / ((rb["E_wpt_grid_MWh"] + rb["E_infra_MWh"]) * 1e3)
        lcod_pred = (rc["dwpt_annual_Rs"] + sup_per_kwh * rc["E_wpt_grid_MWh"] * 1e3) / (rc["E_delivered_MWh"] * 1e3)
        rowsC.append(dict(lam=d["lam"], cov=d["cov"], eta_on=d["eta_on"], E_pred_MWh=rc["E_delivered_MWh"],
                          E_true_MWh=rb["E_delivered_MWh"], lcod_pred=lcod_pred, lcod_true=rb["lcod_Rs_kWh"],
                          overestimate_pct=100 * (rc["E_delivered_MWh"] / rb["E_delivered_MWh"] - 1),
                          cost_under_pct=100 * (1 - lcod_pred / rb["lcod_Rs_kWh"])))
    write_csv(rowsC, "C_centred_vs_wander.csv")
    conv = min(rowsC, key=lambda r: r["lcod_pred"])
    print("C done; centred-planning pick:", conv)

    # ======================================================================== D. scenarios at the best design
    rowsD = []
    for name, sc in SCENARIOS.items():
        r = evaluate(BEST, sc, y_pv, tariff, dark, phys=phys[key(BEST)])
        r["scenario"] = name
        rowsD.append(r)
    write_csv(rowsD, "D_scenarios_best_design.csv")
    print("D done")

    # ======================================================================== E. break-even vs equipped heavy vehicles
    # Heavy classes scaled together; cars and LCVs held at the mid scenario. Design re-chosen at each point.
    F_day = hourly_flow(LANE_SHARE).sum(axis=0) / 365.0
    rowsE = []
    for k in (0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0):
        sc = dict(MID, bus=min(MID["bus"] * k, 1.0), mav=min(MID["mav"] * k, 1.0))
        scr = []
        for d in DESIGNS:
            if not all(phys[key(d)][c]["pbar"] > 0 for c in CLASSES):
                continue
            scr.append((evaluate(d, sc, y_pv, tariff, dark, phys=phys[key(d)], supply=False)["lcod_grid_only_Rs_kWh"], d))
        _, dk = min(scr, key=lambda t: t[0])
        r = evaluate(dk, sc, y_pv, tariff, dark, phys=phys[key(dk)])
        r.update(heavy_mult=k, share_bus=sc["bus"], share_mav=sc["mav"],
                 equipped_heavy_per_day=sum(F_day[j] * sc[c] for j, c in enumerate(CLASSES) if c in ("bus", "mav")))
        rowsE.append(r)
        print(f"  E k={k}: design {dk['lam']},{dk['cov']},{dk['eta_on']} heavy/day {r['equipped_heavy_per_day']:.0f} "
              f"lcod {r['lcod_Rs_kWh']:.1f}")
    write_csv(rowsE, "E_breakeven_heavy.csv")

    # ======================================================================== F. one-at-a-time sensitivity
    base = evaluate(BEST, MID, y_pv, tariff, dark, phys=phys[key(BEST)])
    rowsF = []

    def sens(label, lo_hi, setter, lo_lab=None, hi_lab=None):
        out = dict(parameter=label)
        for tag, val, lab in zip(("low", "high"), lo_hi, (lo_lab, hi_lab)):
            undo = setter(val)
            try:
                r = evaluate(BEST, MID, y_pv, tariff_hourly(), dark, phys=None)
            finally:
                undo()
            out[f"{tag}_value"] = lab if lab is not None else val
            out[f"{tag}_lcod"] = r["lcod_Rs_kWh"]
            out[f"{tag}_self_supply"] = r["self_supply"]
        out["base_lcod"] = base["lcod_Rs_kWh"]
        chk = evaluate(BEST, MID, y_pv, tariff_hourly(), dark, phys=None)["lcod_Rs_kWh"]
        assert abs(chk - base["lcod_Rs_kWh"]) < 1e-6 * base["lcod_Rs_kWh"], f"setter for {label} not restored"
        rowsF.append(out)
        print("  F", label, round(out["low_lcod"], 1), round(out["high_lcod"], 1))

    def set_cost(k):
        def f(v):
            old = COST[k]
            COST[k] = v
            return lambda: COST.__setitem__(k, old)
        return f

    def set_veh(field, scale=False):
        def f(v):
            old = {c: VEH[c][field] for c in CLASSES}
            for c in CLASSES:
                VEH[c][field] = old[c] * v if scale else v
            return lambda: [VEH[c].__setitem__(field, old[c]) for c in CLASSES]
        return f

    def set_global(name):
        def f(v):
            g = globals()
            old = g[name]
            g[name] = v
            return lambda: g.__setitem__(name, old)
        return f

    def set_dict(dct, k):
        def f(v):
            old = dct[k]
            dct[k] = v
            return lambda: dct.__setitem__(k, old)
        return f

    def set_lane_car(v):
        old = LANE_SHARE["car"]
        LANE_SHARE["car"] = v
        return lambda: LANE_SHARE.__setitem__("car", old)

    def set_rx(v):
        BEST["P_rx"] = v
        return lambda: BEST.__setitem__("P_rx", P_RX)

    sens("Road hardware cost (x0.5 ... x2)", (0.5, 2.0), set_cost("cost_mult_dwpt"))
    # US cost: Purdue JTRP-2021/25 total 3.93-4.07 M USD per lane-km (mid 4.0) relative to our base road cost
    US_MULT = 4.0e6 * RS_PER_USD / (base["road_cr_per_lane_km"] * 1e7)
    print(f"  US cost multiplier = {US_MULT:.2f}")
    sens("Road hardware at US cost", (1.0, US_MULT), set_cost("cost_mult_dwpt"), "base", f"x{US_MULT:.1f}")
    sens("Receiver rating (kW)", (15.0, 40.0), set_rx)
    sens("Vehicle speed (x0.75 ... x1)", (0.75, 1.0), set_veh("speed", scale=True))
    sens("Traffic basis (tolled only ... incl. reuse)", ("tolled", "all"), set_dict(corridor.TRAFFIC, "basis"))
    sens("Lane wander s.d. (m)", (0.20, 0.29), set_veh("sigma"))
    sens("Coil quality factor (x0.5 ... x2)", (0.5, 2.0), set_dict(coupler_layer.QFAC, "f"))
    sens("Road hardware life (yr)", (10, 20), set_cost("life_dwpt"))
    sens("Real discount rate", (0.03, 0.07), set_cost("r"))
    sens("Road O&M (x0.5 ... x2)", (0.5 * COST["dwpt_om_rs_per_lane_km"], 2 * COST["dwpt_om_rs_per_lane_km"]),
         set_cost("dwpt_om_rs_per_lane_km"))
    sens("Inverter cost (Rs/kW)", (8000, 20000), set_cost("inv_rs_per_kw"))
    sens("Inverter overload probability", (1e-4, 1e-2), set_cost("p_exceed"))
    sens("Section length per inverter (m)", (50.0, 200.0), set_cost("section_m"))
    sens("Share of cars in charging lane", (0.10, 0.60), set_lane_car)
    sens("Heavy vehicles at night (flattened profile)", (False, True), set_dict(corridor.HOURLY, "night_heavy"),
         "measured", "flattened")
    sens("Power-electronics efficiency", (0.82, 0.90), set_global("ETA_PE"))
    sens("Solar capex incl. mounting premium (Rs/kWp)", (33579 * 1.0, 33579 * 2.0), set_cost("capex_pv"))
    sens("Battery capex (Rs/usable kWh)", (8000 / 0.8, 140 * RS_PER_USD / 0.8), set_cost("capex_be"))
    sens("Solar land (kWp per km)", (0.0, 1e6), set_global("PV_KWP_PER_KM"), "none", "unlimited")
    sens("Time-of-day tariff", (False, True), set_cost("tod"), "flat", "ToD")
    write_csv(rowsF, "F_sensitivity.csv")

    # ======================================================================== M. Monte Carlo uncertainty (grid supply,
    # supply effect on LCOD is small; reported as the distribution of the cost per delivered kWh)
    rng = np.random.default_rng(2026)
    sup_ratio = base["lcod_Rs_kWh"] / base["lcod_grid_only_Rs_kWh"]
    mc = []
    for i in range(300):
        draws = dict(cost_mult_dwpt=float(np.exp(rng.uniform(np.log(0.5), np.log(2.0)))),
                     inv_rs_per_kw=float(rng.uniform(8000, 20000)), life_dwpt=float(rng.uniform(10, 20)),
                     r=float(rng.uniform(0.03, 0.07)),
                     dwpt_om_rs_per_lane_km=float(COST["dwpt_om_rs_per_lane_km"] * rng.uniform(0.5, 2.0)))
        sig = float(rng.uniform(0.20, 0.29))
        spd = float(rng.uniform(0.75, 1.0))
        eta_pe = float(rng.uniform(0.82, 0.90))
        old_cost = {k: COST[k] for k in draws}
        old_v = {c: (VEH[c]["sigma"], VEH[c]["speed"]) for c in CLASSES}
        old_pe = ETA_PE
        COST.update(draws)
        for c in CLASSES:
            VEH[c]["sigma"], VEH[c]["speed"] = sig, SPEED_LIMIT[c] * spd
        ETA_PE = eta_pe
        try:
            r = evaluate(BEST, MID, y_pv, tariff, dark, phys=None, supply=False)
        finally:
            COST.update(old_cost)
            for c in CLASSES:
                VEH[c]["sigma"], VEH[c]["speed"] = old_v[c]
            ETA_PE = old_pe
        mc.append(dict(**draws, sigma=sig, speed_mult=spd, eta_pe=eta_pe,
                       lcod_est=r["lcod_grid_only_Rs_kWh"] * sup_ratio))
    write_csv(mc, "M_monte_carlo.csv")
    q = np.percentile([m["lcod_est"] for m in mc], [5, 50, 95])
    print("M Monte Carlo LCOD 5/50/95 %:", np.round(q, 1))

    # ======================================================================== G. braking-zone harvest at the plaza
    # Measured device: up to 72.4 J per light-vehicle pass per 0.33 m2 module, 52.6 % mean efficiency
    # (Ferreira 2020).  Applied to light vehicles only (cars incl. exempt local cars, LCVs).
    J_MAX = 72.4
    exempt_cars_per_day = 20000.0
    light_per_day = traffic_info["car"] + exempt_cars_per_day + traffic_info["lcv"]
    harvest = {m: light_per_day * J_MAX * m / 3.6e6 * 365 for m in (20, 100)}
    G = dict(light_veh_per_day=light_per_day, kWh_yr_20_modules=harvest[20], kWh_yr_100_modules=harvest[100],
             infra_MWh=base["E_infra_MWh"], share_of_infra_pct_20=harvest[20] / 1e3 / base["E_infra_MWh"] * 100,
             share_of_infra_pct_100=harvest[100] / 1e3 / base["E_infra_MWh"] * 100,
             car_KE_80_to_30_kJ=0.5 * 1078 * ((80 / 3.6) ** 2 - (30 / 3.6) ** 2) / 1e3)

    # hourly dispatch of the base case (for the dispatch figure)
    dem_wpt, _, _ = wpt_demand(BEST, VEH, MID, L_E, ETA_PE, LANE_SHARE, phys=phys[key(BEST)])
    dem_inf = infra_load(dark, INFRA)
    o = solve(dem_wpt + dem_inf, y_pv, tariff, COST, C_pv_max=PV_KWP_PER_KM * L_SECTION, firm_min=base["firm_kW"])
    np.savez(os.path.join(RES, "dispatch_base.npz"), wpt=dem_wpt, infra=dem_inf, y_pv=y_pv, C_pv=o["C_pv"],
             g=o["g"], u=o["u"], c=o["c"], d=o["d"], s=o["s"], E_b=o["E_b"], tariff=tariff, dark=dark)
    json.dump(dict(pv=pv_info, us_mult=US_MULT, traffic_mean_per_day=traffic_info, best_design=BEST, base=base, centred_pick=conv,
                   harvest=G, monte_carlo_5_50_95=list(q), n_designs=len(DESIGNS), n_valid=len(valid)),
              open(os.path.join(RES, "summary.json"), "w"), indent=1, default=float)
    print("G harvest:", G)

    # ======================================================================== W. weather-file robustness
    # Re-run the base case with every other TMYx year-set found next to the main weather file.
    rowsW = []
    if len(sys.argv) > 1:
        import glob
        for epw in sorted(glob.glob(os.path.join(ROOT, "data", "weather", "*", "*.epw"))):
            yw, _, iw = per_kwp(epw)
            yw = yw * np.mean((1 - COST["degr_pv"]) ** np.arange(COST["life_pv"]))
            rw = evaluate(BEST, MID, yw, tariff, dark, phys=phys[key(BEST)])
            rowsW.append(dict(weather=os.path.basename(epw), ghi=iw["ghi_kwh_m2_yr"], yield_kwh_kwp=iw["yield_kwh_per_kwp"],
                              lcod=rw["lcod_Rs_kWh"], self_supply=rw["self_supply"], C_pv_kWp=rw["C_pv_kWp"],
                              E_b_kWh=rw["E_b_usable_kWh"], co2_avoided_t=rw["co2_avoided_t"]))
            print(f"  W {os.path.basename(epw)}: yield {iw['yield_kwh_per_kwp']:.0f}, LCOD {rw['lcod_Rs_kWh']:.1f}, "
                  f"self-supply {rw['self_supply']*100:.0f} %")
        write_csv(rowsW, "W_weather_robustness.csv")
    print("ALL DONE")
