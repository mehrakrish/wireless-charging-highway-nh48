"""
Layer 2: hourly electricity demand of an electrified highway section, for one year (8760 h).

Inputs: real tolled traffic by class and month (MSRDC, Somatne Phata), hourly traffic profile (UPEIDA),
vehicle data (energy use, speed, air gap, receivers), coil design, and road infrastructure loads.

For each vehicle class c, hour h:
  flow_c(h)        vehicles per hour in the electrified lanes (both directions)
  equipped_c       share of class-c vehicles that are EVs with wireless receivers (scenario)
  e_del_c          energy delivered to one equipped vehicle per km  = n_rx * P_rx * pbar_c / v_c   (kWh/km)
  grid energy      = delivered / (eta_coil_c * eta_pe)   where eta_pe is the power-electronics chain
  demand_WPT(h)    = sum_c flow_c(h) * equipped_c * e_del_c * L_e / (eta_coil_c * eta_pe)        (kW)
Peak instantaneous power per road section (for inverter sizing) uses a Poisson model of vehicle arrivals.
"""
import csv
import os
import numpy as np
from scipy.stats import poisson
from coupler_layer import wander_average

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # repository root (src/ is one level down)
DATA = os.path.join(ROOT, "data")
CLASSES = ["car", "lcv", "bus", "mav"]
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _rows(name):
    with open(os.path.join(DATA, name)) as f:
        return [r for r in csv.reader(f) if r and not r[0].startswith("#")]


# Exempt & violation vehicles (physically on the road but not fee-paying), as a multiple of the tolled count.
# MSRDC fee statements, "Exemption & Violation" table: Oct-2025 MAV 33,505 / bus-truck 22,559 / LCV 9,976;
# Mar-2026 MAV 34,919 / bus-truck 24,569 / LCV 10,411 (tolled: Oct-25 60,489 / 40,508 / 28,448;
# Mar-26 64,725 / 43,394 / 32,651) -> factors 1.554/1.539, 1.557/1.566, 1.351/1.319 (two-month means below).
# Exempt cars (~20,000/day, mostly local non-transport vehicles) are excluded (conservative).
EXEMPT_FACTOR = dict(car=1.0, lcv=1.335, bus=1.56, mav=1.55)
# "Reuse & Exit" passages (upper-traffic sensitivity), Mar-2026 as a multiple of tolled:
# car 146,056/356,872, LCV 27,588/32,651, bus-truck 23,385/43,394, MAV 5,933/64,725
REUSE_FACTOR = dict(car=1.409, lcv=1.845, bus=1.539, mav=1.092)
TRAFFIC = dict(basis="tolled+exempt")      # "tolled", "tolled+exempt" (base), "all" (+ reuse)


def daily_counts():
    """Average vehicles per day on the road, by calendar month (1..12) and class. Jun/Jul use Aug-2025 (proxy).
    Category C of the MSRDC statements is "Bus/Truck" (two-axle buses and trucks); it is modelled as one class."""
    rows = _rows("msrdc_somatne_monthly.csv")
    head, body = rows[0], rows[1:]
    out = {}
    for r in body:
        m = int(r[0].split("-")[1])
        d = int(r[1])
        out[m] = {c: int(r[head.index(k)]) / d for c, k in zip(CLASSES, ["car_jeep", "lcv", "bus", "mav"])}
    for m in (6, 7):
        out[m] = dict(out[8])
    f = {c: 1.0 for c in CLASSES}
    if TRAFFIC["basis"] in ("tolled+exempt", "all"):
        f = dict(EXEMPT_FACTOR)
    if TRAFFIC["basis"] == "all":
        f = {c: f[c] + REUSE_FACTOR[c] - 1.0 for c in CLASSES}
    return {m: {c: out[m][c] * f[c] for c in CLASSES} for m in out}


def hourly_shares():
    rows = _rows("hourly_profile_katoghan.csv")[1:]
    p = np.array([float(r[1]) for r in rows])
    return p / p.sum()


HOURLY = dict(night_heavy=False)


def hourly_flow(lane_share):
    """Vehicles per hour (both directions) using the electrified lanes, 8760 x 4 array (classes in CLASSES order).
    Base: one measured all-class profile. Sensitivity (night_heavy): heavy classes follow a flattened profile
    (half the measured profile + half uniform), representing the night-time truck movement common in India."""
    dc, sh = daily_counts(), hourly_shares()
    flat = 0.5 * sh + 0.5 / 24.0
    flows = []
    for m, nd in enumerate(DAYS_IN_MONTH, start=1):
        cols = []
        for c in CLASSES:
            prof = flat if (HOURLY["night_heavy"] and c in ("bus", "mav")) else sh
            cols.append(prof * dc[m][c] * lane_share[c])
        flows.append(np.tile(np.array(cols).T, (nd, 1)))
    return np.vstack(flows)


def class_physics(design, veh):
    """pbar and coil efficiency for each class under lane wander, for a given coil design."""
    out = {}
    for c in CLASSES:
        pb, eta = wander_average(veh[c]["gap"], design["pitch"], veh[c]["sigma"], design["eta_on"], lam=design["lam"])
        out[c] = dict(pbar=pb, eta=eta)
    return out


def _ok(ph):
    return ph["pbar"] > 0 and np.isfinite(ph["eta"])


def wpt_demand(design, veh, scen, L_e, eta_pe, lane_share, phys=None):
    """Hourly grid demand of the wireless lanes (kW) and energy delivered to vehicles (kWh per hour).
    A class that receives no power under a design (pbar = 0) contributes nothing."""
    phys = class_physics(design, veh) if phys is None else phys
    F = hourly_flow(lane_share)
    dem = np.zeros(F.shape[0])
    dlv = np.zeros(F.shape[0])
    per_class = {}
    for j, c in enumerate(CLASSES):
        v = veh[c]
        if not _ok(phys[c]):
            per_class[c] = dict(e_del_kwh_km=0.0, cover=0.0, delivered_kwh=0.0, grid_kwh=0.0, **phys[c])
            continue
        e_del = v["n_rx"] * design["P_rx"] * phys[c]["pbar"] / v["speed"]            # kWh per km per vehicle
        d_c = F[:, j] * scen[c] * e_del * L_e                                          # kWh delivered per hour
        dlv += d_c
        dem += d_c / (phys[c]["eta"] * eta_pe)
        per_class[c] = dict(e_del_kwh_km=e_del, cover=e_del / v["kwh_km"], delivered_kwh=d_c.sum(),
                            grid_kwh=(d_c / (phys[c]["eta"] * eta_pe)).sum(), **phys[c])
    return dem, dlv, per_class


def _compound_poisson_pmf(means, sizes, n_max=4000):
    """pmf of R = sum_c sizes[c] * N_c with N_c ~ Poisson(means[c]) independent (vehicles arrive independently;
    all receivers of one vehicle arrive together)."""
    pmf = np.zeros(n_max + 1)
    pmf[0] = 1.0
    for m, k in zip(means, sizes):
        if m <= 0:
            continue
        nv = int(poisson.ppf(1 - 1e-12, m)) + 1
        pv = poisson.pmf(np.arange(nv + 1), m)
        comp = np.zeros(n_max + 1)
        idx = np.arange(nv + 1) * k
        keep = idx <= n_max
        comp[idx[keep]] = pv[keep]
        pmf = np.convolve(pmf, comp)[: n_max + 1]
    return pmf


def peak_hour(scen, veh, lane_share):
    """Index of the hour of the year with the most equipped receivers per km (all classes jointly)."""
    F = hourly_flow(lane_share)
    dens = sum(F[:, j] * scen[c] * veh[c]["n_rx"] / veh[c]["speed"] for j, c in enumerate(CLASSES))
    return int(np.argmax(dens)), F


def installed_power_per_km(design, veh, scen, lane_share, section_m=100.0, p_exceed=1e-3, phys=None):
    """Inverter capacity per lane-km (kW). Each road section of length section_m is fed by one inverter.
    At the busiest hour (joint over classes), the number of receivers on a section is compound Poisson: vehicles
    of class c arrive as Poisson with mean q_c/2 * a_c * l / v_c, each bringing n_c receivers at once.
    The inverter rating N* x P_rx is the smallest with P(R > N*) < p_exceed, and at least one vehicle's worth."""
    t, F = peak_hour(scen, veh, lane_share)
    means, sizes, nmax = [], [], 1
    for j, c in enumerate(CLASSES):
        if phys is not None and not _ok(phys[c]):
            continue
        m = F[t, j] / 2.0 * scen[c] * (section_m / 1e3) / veh[c]["speed"]
        means.append(m)
        sizes.append(veh[c]["n_rx"])
        if scen[c] > 0:
            nmax = max(nmax, veh[c]["n_rx"])
    pmf = _compound_poisson_pmf(means, sizes)
    tail = 1.0 - np.cumsum(pmf)
    assert np.any(tail < p_exceed), "compound-Poisson tail truncated before reaching p_exceed"
    n_design = int(np.argmax(tail < p_exceed))
    n_design = max(n_design, nmax)
    mean_rx = sum(m * k for m, k in zip(means, sizes))
    return n_design * design["P_rx"] * (1e3 / section_m), mean_rx, n_design


def corridor_peak_power(design, veh, scen, lane_share, L_e, eta_pe, phys, p_exceed=1e-3):
    """Grid-side instantaneous power of the whole electrified section that is exceeded with probability
    p_exceed at the busiest hour. Vehicles in both directions are compound-Poisson; each receiver draws its
    average P_rx * pbar_c (grid side: / (eta_c * eta_pe)). Used as a firm-capacity check on grid + battery."""
    t, F = peak_hour(scen, veh, lane_share)
    unit = 5.0                                                   # kW resolution of the distribution
    means, sizes = [], []
    for j, c in enumerate(CLASSES):
        if not _ok(phys[c]):
            continue
        means.append(F[t, j] * scen[c] * L_e / veh[c]["speed"])
        p_veh = veh[c]["n_rx"] * design["P_rx"] * phys[c]["pbar"] / (phys[c]["eta"] * eta_pe)
        sizes.append(max(int(round(p_veh / unit)), 1))
    pmf = _compound_poisson_pmf(means, sizes, n_max=20000)
    tail = 1.0 - np.cumsum(pmf)
    assert np.any(tail < p_exceed), "compound-Poisson tail truncated before reaching p_exceed"
    return float(np.argmax(tail < p_exceed) * unit), float(sum(m * k for m, k in zip(means, sizes)) * unit), t


def infra_load(hours_dark, P):
    """Road infrastructure electrical load per hour (kW) for the section: lighting (dark hours only),
    toll plaza base load, ATMS devices."""
    light = P["light_kw_per_km"] * P["L_section"] * hours_dark
    return light + P["toll_kw"] + P["atms_kw_per_km"] * P["L_section"]
