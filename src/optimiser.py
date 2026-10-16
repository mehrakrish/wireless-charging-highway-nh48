"""
Layer 3: least-cost supply of the corridor (solar PV + battery + grid), one year at hourly steps.

Linear programme (LP), solved with the open-source HiGHS solver.

Decision variables (sizes):    C_pv  solar capacity (kWp)          E_b  battery energy (kWh)
                               P_b   battery power (kW)             G    grid connection (kVA ~ kW at pf 1)
Decision variables (each hour t): g_t grid import, u_t solar used, c_t battery charge, d_t battery discharge,
                               s_t battery state of charge (kWh)

  energy balance      g_t + u_t + d_t = D_t + c_t
  solar available     u_t <= C_pv * y_t                (y_t = AC output per kWp in hour t)
  battery             s_{t+1} = s_t + eta_c c_t - d_t / eta_d,   0 <= s_t <= E_b,   s_T = s_0
                      c_t <= P_b,  d_t <= P_b
  grid                g_t <= G
  limits              C_pv <= C_pv_max (right-of-way area), optional E_b <= E_b_max
Objective (Rs per year):
  CRF*(capex_pv*C_pv + capex_be*E_b + capex_bp*P_b + capex_grid*G) + O&M
  + sum_t tariff_t * g_t + 12 * demand_charge * G
CRF (capital recovery factor) = r(1+r)^n / ((1+r)^n - 1) turns a one-off cost into an equal yearly cost.
"""
import numpy as np
import highspy


def crf(rate, years):
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)


def solve(D, y_pv, tariff, P, C_pv_max=np.inf, E_b_max=np.inf, export_price=None, firm_min=0.0,
          firm_hours=0.25, verbose=False):
    """D, y_pv, tariff: hourly arrays (kW, kW/kWp, Rs/kWh). P: dict of cost parameters (see run_model.py).
    Returns dict of sizes, hourly flows and cost breakdown."""
    T = len(D)
    for name, arr in (("demand", D), ("solar", y_pv), ("tariff", tariff)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"non-finite values in {name}")
    h = highspy.Highs()
    h.setOptionValue("output_flag", verbose)
    inf = highspy.kHighsInf
    a_pv = crf(P["r"], P["life_pv"]) * P["capex_pv"] + P["om_pv"]
    a_be = (crf(P["r"], P["life_bat"]) + P["om_be_frac"]) * P["capex_be"]
    a_bp = crf(P["r"], P["life_bat"]) * P["capex_bp"]
    a_g = crf(P["r"], P["life_grid"]) * P["capex_grid"] + 12 * P["demand_charge"]

    # variable layout: [C_pv, E_b, P_b, G, g(T), u(T), c(T), d(T), s(T), x(T) export]
    n_s = 4
    ig, iu, ic, idd, iss, ix = (n_s + k * T for k in range(6))
    nv = n_s + 6 * T
    cost = np.zeros(nv)
    cost[0], cost[1], cost[2], cost[3] = a_pv, a_be, a_bp, a_g
    cost[ig:ig + T] = tariff
    cost[ic:ic + T] = 1e-6          # tiny tie-breakers: avoid needless cycling
    cost[idd:idd + T] = 1e-6
    lb = np.zeros(nv)
    ub = np.full(nv, inf)
    ub[0], ub[1] = C_pv_max, E_b_max
    if export_price is None:
        ub[ix:ix + T] = 0.0
    else:
        cost[ix:ix + T] = -export_price
    h.addVars(nv, lb, ub)
    h.changeColsCost(nv, np.arange(nv, dtype=np.int32), cost)

    rows_lo, rows_hi, starts, idx, val = [], [], [], [], []

    def row(cols, coefs, lo, hi):
        starts.append(len(idx)); idx.extend(cols); val.extend(coefs); rows_lo.append(lo); rows_hi.append(hi)

    eta_c = eta_d = np.sqrt(P["rte"])
    for t in range(T):
        # balance: g + u + d - c - x = D
        row([ig + t, iu + t, idd + t, ic + t, ix + t], [1, 1, 1, -1, -1], D[t], D[t])
        # solar: u + x - C_pv*y <= 0   (export, if allowed, also comes from solar)
        row([iu + t, ix + t, 0], [1, 1, -y_pv[t]], -inf, 0.0)
        # battery power and energy limits
        row([ic + t, 2], [1, -1], -inf, 0.0)
        row([idd + t, 2], [1, -1], -inf, 0.0)
        row([iss + t, 1], [1, -1], -inf, 0.0)
        # grid limit
        row([ig + t, 3], [1, -1], -inf, 0.0)
        # state of charge (cyclic): s_{t+1} - s_t - eta_c c_t + d_t/eta_d = 0
        tn = (t + 1) % T
        row([iss + tn, iss + t, ic + t, idd + t], [1, -1, -eta_c, 1 / eta_d], 0.0, 0.0)
    # battery duration: P_b <= E_b / 2  (prices are for 2-4 h systems)
    row([2, 1], [1, -0.5], -inf, 0.0)
    # firm capacity without solar: G + P_b >= firm_min (instantaneous peak of the section, see corridor.py)
    if firm_min > 0:
        row([3, 2], [1, 1], firm_min, inf)
        # the battery must always hold enough energy to cover the shortfall (firm_min - G) for firm_hours:
        # s_t + firm_hours * G >= firm_hours * firm_min
        for t in range(T):
            row([iss + t, 3], [1, firm_hours], firm_hours * firm_min, inf)
    starts.append(len(idx))
    h.addRows(len(rows_lo), np.array(rows_lo), np.array(rows_hi), len(idx),
              np.array(starts[:-1], dtype=np.int32), np.array(idx, dtype=np.int32), np.array(val, dtype=float))
    h.run()
    status = h.modelStatusToString(h.getModelStatus())
    if status != "Optimal":
        raise RuntimeError(f"LP not optimal: {status}")
    x = np.array(h.getSolution().col_value)
    C_pv, E_b, P_b, G = x[:4]
    g, u, c, d, s, ex = (x[k:k + T] for k in (ig, iu, ic, idd, iss, ix))
    energy_cost = float(np.dot(tariff, g))
    out = dict(C_pv=C_pv, E_b=E_b, P_b=P_b, G=G, g=g, u=u, c=c, d=d, s=s, x=ex,
               annual_pv=a_pv * C_pv, annual_bat=a_be * E_b + a_bp * P_b, annual_grid_fixed=a_g * G,
               annual_energy=energy_cost, annual_export=float(np.dot(export_price, ex)) if export_price is not None else 0.0)
    out["annual_total"] = out["annual_pv"] + out["annual_bat"] + out["annual_grid_fixed"] + energy_cost - out["annual_export"]
    out["self_supply"] = 1 - g.sum() / D.sum()
    out["pv_curtailed"] = 1 - (u.sum() + ex.sum()) / max(C_pv * y_pv.sum(), 1e-9)
    return out


if __name__ == "__main__":
    # smoke test on a synthetic year: flat 100 kW demand, idealised sun, flat tariff
    T = 8760
    hr = np.arange(T) % 24
    y = np.clip(np.sin((hr - 6) / 12 * np.pi), 0, None) * 0.8
    D = np.full(T, 100.0)
    tariff = np.full(T, 9.0)
    P = dict(r=0.10, life_pv=25, life_bat=12, life_grid=25, capex_pv=40000, om_pv=600, capex_be=15000, om_be_frac=0.02,
             capex_bp=3000, capex_grid=5000, demand_charge=400, rte=0.88)
    o = solve(D, y, tariff, P)
    print({k: round(float(v), 3) for k, v in o.items() if np.ndim(v) == 0})
    # energy check: imports + solar used + net battery = demand
    lhs = o["g"].sum() + o["u"].sum() + o["d"].sum() - o["c"].sum()
    print("balance error (kWh):", round(lhs - D.sum(), 6))
