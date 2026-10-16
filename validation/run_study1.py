"""
Study 1 - Inductive EV charging link: coupling and coil-to-coil efficiency vs air gap and misalignment.

Pipeline (each step is explained in METHODS.md):
  Step 1  Inputs from the reference prototype (Ibrahim & Mohammed, Batteries 2025, 11, 257)
  Step 2  Recover the unpublished turn spacing from each coil's measured self-inductance
  Step 3  Check the mutual-inductance formula against an independent brute-force integral
  Step 4  Validate against three sets of published measurements (none used in fitting)
  Step 5  Derive coil quality factors Q from the published wire and measured copper loss
  Step 6  Main results: k and efficiency over the SAE J2954 gap range and 0-200 mm offset
  Step 7  Sensitivity checks
  Step 8  Figures and CSV tables

Run:  python run_study1.py      (needs numpy, scipy, matplotlib; about 15 s)
"""

import csv
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import brentq

from wpt_model import (SpiralCoil, mutual_inductance, mutual_offset_filaments, mutual_neumann_bruteforce,
                       litz_dc_resistance, eta_optimal, eta_fixed_load, OMEGA)

HERE = os.path.dirname(os.path.abspath(__file__))
FIG, RES, DATA = (os.path.join(HERE, d) for d in ("figures", "results", "data"))
os.makedirs(FIG, exist_ok=True)
os.makedirs(RES, exist_ok=True)

# ===================================================================== STEP 1: INPUTS
# All values below are quoted from Ibrahim & Mohammed (2025), Batteries 11:257.
SRC = "Ibrahim & Mohammed 2025"
R_OUT = 0.200                 # outer radius, m       (Sec. 4.2: outer diameter fixed at 400 mm)
N1, N2 = 43, 11               # turns                 (Sec. 4.2: 43 primary, 11 secondary spiral turns)
D_WIRE = 1.9e-3               # conductor diameter, m (Table 1)
N_STRANDS, D_STRAND = 180, 0.102e-3   # Litz: 180 x AWG38 (Table 1)
L1_MEAS, L2_MEAS = 795e-6, 81e-6      # measured self-inductances (Table 3)
M_MEAS, K_MEAS, GAP_T3 = 50.25e-6, 0.198, 0.131   # measured M and k at 131 mm (Table 3)
# 200 W hardware test (Sec. 5): measured copper loss 7.0 W at i1 = 2.25 A, i2 = 4.92 A,
# cored version of the same windings: L1 = 1103.3 uH, L2 = 114.1 uH, f = 82.169 kHz
P_CU_MEAS, I1_TEST, I2_TEST = 7.0, 2.25, 4.92

# Measured coupling curves, extracted from the vector charts (Fig. 17, Fig. 20) by tools/extract_curves.py
def load(name):
    with open(os.path.join(DATA, name)) as f:
        r = list(csv.DictReader(f))
    return {k: np.array([float(x[k]) for x in r]) for k in r[0]}


F17 = load("ibrahim2025_fig17_k_vs_gap.csv")             # k vs coil distance, aligned
F20 = load("ibrahim2025_fig20_k_vs_offset_gap100.csv")   # k vs horizontal offset, 100 mm distance

# ===================================================================== STEP 2: GEOMETRY RECOVERY
# The paper does not publish turn spacing. We recover it from each coil's OWN measured self-inductance.
# Only L1 and L2 are used. M and k are never used -> every coupling comparison below is a blind test.
A_WIRE = D_WIRE / 2
p1 = brentq(lambda p: SpiralCoil(R_OUT, N1, p, wire_radius=A_WIRE).self_inductance() - L1_MEAS, D_WIRE, 4.4e-3)
p2 = brentq(lambda p: SpiralCoil(R_OUT, N2, p, wire_radius=A_WIRE).self_inductance() - L2_MEAS, D_WIRE, 0.017)


def make_pair(scale=1.0):
    tx = SpiralCoil(R_OUT * scale, N1, p1 * scale, wire_radius=A_WIRE * scale)
    rx = SpiralCoil(R_OUT * scale, N2, p2 * scale, wire_radius=A_WIRE * scale)
    return tx, rx


TX, RX = make_pair()
L1, L2 = TX.self_inductance(), RX.self_inductance()


def k_of(gap, off, tx=TX, rx=RX, l1=L1, l2=L2):
    return mutual_inductance(tx, rx, gap, off) / np.sqrt(l1 * l2)


# ===================================================================== STEP 3: FORMULA CROSS-CHECK
xcheck = []
for (a, b, c, d) in [(0.15, 0.12, 0.13, 0.05), (0.19, 0.19, 0.20, 0.20), (0.10, 0.18, 0.25, 0.15)]:
    g = float(mutual_offset_filaments(a, b, c, d))
    n = mutual_neumann_bruteforce(a, b, c, d)
    xcheck.append((a, b, c, d, g, n, abs(g - n) / abs(n) * 100))

# ===================================================================== STEP 4: VALIDATION
M_131 = mutual_inductance(TX, RX, GAP_T3, 0.0)
k_131 = M_131 / np.sqrt(L1 * L2)
k_gap_model = np.array([k_of(g * 1e-3, 0.0) for g in F17["x_mm"]])
k_off_model = np.array([k_of(0.100, d * 1e-3) for d in F20["x_mm"]])


def stats(model, meas):
    err = (model - meas) / meas * 100
    ss_res = np.sum((model - meas) ** 2)
    ss_tot = np.sum((meas - meas.mean()) ** 2)
    return dict(mean_abs=np.mean(np.abs(err)), max_abs=np.max(np.abs(err)),
                at=int(np.argmax(np.abs(err))), r2=1 - ss_res / ss_tot, err=err)


V = {}
for tag, xs, ours, d in [("gap", F17["x_mm"], k_gap_model, F17), ("offset", F20["x_mm"], k_off_model, F20)]:
    V[tag] = dict(x=xs, ours=stats(ours, d["k_measured"]),
                  theirs_an=stats(d["k_their_analytical"], d["k_measured"]),
                  theirs_fem=stats(d["k_their_FEM"], d["k_measured"]), model=ours, meas=d["k_measured"])

with open(os.path.join(RES, "validation_summary.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Test", "points", "this model: mean |error| %", "this model: max |error| %", "this model: R2",
                "authors' analytical: mean |error| %", "authors' FEM: mean |error| %", "authors' FEM: max |error| %"])
    w.writerow(["M and k at 131 mm (Table 3)", 1, f"{abs(k_131-K_MEAS)/K_MEAS*100:.2f}", "", "", "", "", ""])
    for tag, label in [("gap", "k vs coil distance 32-312 mm (Fig. 17)"), ("offset", "k vs offset 0-130 mm at 100 mm (Fig. 20)")]:
        o, a_, fe = V[tag]["ours"], V[tag]["theirs_an"], V[tag]["theirs_fem"]
        w.writerow([label, len(V[tag]["x"]), f"{o['mean_abs']:.2f}", f"{o['max_abs']:.2f} at {V[tag]['x'][o['at']]:.0f} mm",
                    f"{o['r2']:.4f}", f"{a_['mean_abs']:.2f}", f"{fe['mean_abs']:.2f}", f"{fe['max_abs']:.2f}"])

with open(os.path.join(RES, "validation_points.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["test", "x_mm", "k_measured", "k_this_model", "error_this_model_%", "k_their_FEM", "error_their_FEM_%"])
    for tag, d in [("gap", F17), ("offset", F20)]:
        for i, x in enumerate(d["x_mm"]):
            w.writerow([tag, int(x), f"{d['k_measured'][i]:.4f}", f"{V[tag]['model'][i]:.4f}",
                        f"{V[tag]['ours']['err'][i]:+.2f}", f"{d['k_their_FEM'][i]:.4f}", f"{V[tag]['theirs_fem']['err'][i]:+.2f}"])

# ===================================================================== STEP 5: QUALITY FACTOR
# R_dc from Table 1 wire and recovered geometry; AC/DC factor F_R calibrated on the measured 7.0 W copper loss.
R1_DC = litz_dc_resistance(TX, N_STRANDS, D_STRAND)
R2_DC = litz_dc_resistance(RX, N_STRANDS, D_STRAND)
F_R = P_CU_MEAS / (I1_TEST ** 2 * R1_DC + I2_TEST ** 2 * R2_DC)


def q_pair(fr, tx=TX, rx=RX, l1=L1, l2=L2):
    r1 = fr * litz_dc_resistance(tx, N_STRANDS, D_STRAND)
    r2 = fr * litz_dc_resistance(rx, N_STRANDS, D_STRAND)
    return OMEGA * l1 / r1, OMEGA * l2 / r2, r1, r2


Q1, Q2, R1, R2 = q_pair(F_R)

with open(os.path.join(RES, "quality_factor.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["quantity", "transmitter (road)", "receiver (car)", "how obtained"])
    w.writerow(["wire length (m)", f"{np.sum(2*np.pi*TX.radii):.2f}", f"{np.sum(2*np.pi*RX.radii):.2f}", "sum of turn circumferences"])
    w.writerow(["R_dc (mOhm)", f"{R1_DC*1e3:.1f}", f"{R2_DC*1e3:.1f}", "rho * length / (180 strands x AWG38 area)"])
    w.writerow(["AC/DC factor F_R", f"{F_R:.3f}", f"{F_R:.3f}", "measured copper loss 7.0 W at 2.25 A / 4.92 A"])
    w.writerow(["R_ac at 85 kHz (mOhm)", f"{R1*1e3:.1f}", f"{R2*1e3:.1f}", "F_R * R_dc"])
    w.writerow(["Q = wL/R_ac", f"{Q1:.0f}", f"{Q2:.0f}", "omega = 2*pi*85 kHz"])

# ===================================================================== STEP 6: MAIN RESULTS
GAPS = np.round(np.arange(0.100, 0.2501, 0.005), 3)      # SAE J2954 classes Z1-Z3 span 100-250 mm
OFFS = np.round(np.arange(0.0, 0.2001, 0.005), 3)
Mgrid = np.array([[mutual_inductance(TX, RX, g, d) for d in OFFS] for g in GAPS])
Kgrid = Mgrid / np.sqrt(L1 * L2)
ETA_OPT = eta_optimal(Kgrid, Q1, Q2)

G_DESIGN = 0.150                                           # design point: aligned, 150 mm
k_design = k_of(G_DESIGN, 0.0)
RL = R2 * np.sqrt(1 + k_design ** 2 * Q1 * Q2)            # load that maximises efficiency at the design point
ETA_FIX = eta_fixed_load(Mgrid, R1, R2, RL)


def ix(arr, v):
    return int(np.argmin(np.abs(arr - v)))


# Check: the closed-form best efficiency must equal a brute-force search over load resistance.
eta_check = []
for (g, d) in [(0.100, 0.0), (0.175, 0.100), (0.250, 0.200)]:
    m = mutual_inductance(TX, RX, g, d)
    rl = np.logspace(-2, 3, 200001)
    brute = np.max(eta_fixed_load(m, R1, R2, rl))
    closed = eta_optimal(m / np.sqrt(L1 * L2), Q1, Q2)
    eta_check.append((g, d, closed, brute, abs(closed - brute)))


with open(os.path.join(RES, "main_results_grid.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["gap_mm", "offset_mm", "M_uH", "k", "eta_matched_load_%", "eta_fixed_load_%"])
    for i, g in enumerate(GAPS):
        for j, d in enumerate(OFFS):
            w.writerow([round(g * 1e3), round(d * 1e3), f"{Mgrid[i, j]*1e6:.3f}", f"{Kgrid[i, j]:.4f}",
                        f"{ETA_OPT[i, j]*100:.2f}", f"{ETA_FIX[i, j]*100:.2f}"])

# Conservative lower bound: the model over-predicted measured k by at most K_ERR (Step 4),
# so every k is reduced by that amount and efficiency recomputed.
K_ERR = max(V["gap"]["ours"]["max_abs"], V["offset"]["ours"]["max_abs"]) / 100
ETA_OPT_LO = eta_optimal(Kgrid * (1 - K_ERR), Q1, Q2)
ETA_FIX_LO = eta_fixed_load(Mgrid * (1 - K_ERR), R1, R2, RL)

HEAD_G, HEAD_D = [0.100, 0.150, 0.200, 0.250], [0.0, 0.050, 0.100, 0.150, 0.200]
with open(os.path.join(RES, "headline_table.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["gap_mm", "offset_mm", "k", "eta_matched_%", f"eta_matched_lower_bound_% (k -{K_ERR*100:.1f}%)",
                "eta_fixed_%", f"eta_fixed_lower_bound_% (k -{K_ERR*100:.1f}%)", "fixed-load penalty (points)"])
    for g in HEAD_G:
        for d in HEAD_D:
            i, j = ix(GAPS, g), ix(OFFS, d)
            w.writerow([round(g*1e3), round(d*1e3), f"{Kgrid[i,j]:.3f}", f"{ETA_OPT[i,j]*100:.1f}",
                        f"{ETA_OPT_LO[i,j]*100:.1f}", f"{ETA_FIX[i,j]*100:.1f}", f"{ETA_FIX_LO[i,j]*100:.1f}",
                        f"{(ETA_OPT[i,j]-ETA_FIX[i,j])*100:.1f}"])

# ===================================================================== STEP 7: SENSITIVITY
G_S, D_S = 0.175, 0.100
i_s, j_s = ix(GAPS, G_S), ix(OFFS, D_S)
k_s = Kgrid[i_s, j_s]
base = eta_optimal(k_s, Q1, Q2)
sens = []
for fr in (1.0, F_R, 1.5, 2.0, 3.0):
    q1, q2, *_ = q_pair(fr)
    sens.append(("AC/DC resistance factor F_R", f"{fr:.2f}", f"Q1={q1:.0f}, Q2={q2:.0f}", eta_optimal(k_s, q1, q2)))
kerr = max(V["gap"]["ours"]["max_abs"], V["offset"]["ours"]["max_abs"]) / 100
for f_ in (1 - kerr, 1 + kerr):
    sens.append(("coupling k shifted by worst validation error", f"x{f_:.3f}", "", eta_optimal(k_s * f_, Q1, Q2)))
SIZES = [1.0, 1.25, 1.5, 1.75]
size_curves = {}
for s in SIZES:
    t, r = make_pair(s)
    l1, l2 = t.self_inductance(), r.self_inductance()
    kk = np.array([mutual_inductance(t, r, G_S, d) for d in OFFS]) / np.sqrt(l1 * l2)
    q1, q2, *_ = q_pair(F_R, t, r, l1, l2)
    size_curves[s] = (kk, eta_optimal(kk, q1, q2))
    sens.append(("coil outer diameter (all dimensions scaled)", f"{400*s:.0f} mm", f"Q1={q1:.0f}, Q2={q2:.0f}",
                 eta_optimal(kk[j_s], q1, q2)))

with open(os.path.join(RES, "sensitivity.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([f"parameter varied (gap {G_S*1e3:.0f} mm, offset {D_S*1e3:.0f} mm; others at baseline)",
                "value", "note", "eta_matched_%", "change vs baseline (points)"])
    for p, v, n, e in sens:
        w.writerow([p, v, n, f"{e*100:.2f}", f"{(e-base)*100:+.2f}"])

# ===================================================================== STEP 8: FIGURES
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SERIES = [BLUE, ORANGE, AQUA, YELLOW]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
                     "lines.linewidth": 2.0, "legend.frameon": False})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, name), dpi=200)
    plt.close(fig)


def end_label(ax, x, y, text):
    ax.annotate(text, (x[-1], y[-1]), xytext=(4, 0), textcoords="offset points", va="center", fontsize=9, color=INK2)


# Fig 1 - validation vs coil distance
gx = np.linspace(0.03, 0.32, 59)
fig, ax = plt.subplots(figsize=(6.4, 4.2))
ax.plot(gx * 1e3, [k_of(g, 0.0) for g in gx], color=BLUE, label="This model (blind prediction)")
ax.plot(F17["x_mm"], F17["k_measured"], "o", ms=8, mfc="none", mec=ORANGE, mew=2, label=f"Measured, {SRC}")
ax.plot(F17["x_mm"], F17["k_their_FEM"], "s", ms=4, color=AQUA, label="Their 3D FEM (COMSOL)")
o = V["gap"]["ours"]
ax.text(0.97, 0.62, f"14 points, mean |error| {o['mean_abs']:.1f}%\nmax {o['max_abs']:.1f}%, R² = {o['r2']:.4f}",
        transform=ax.transAxes, ha="right", fontsize=9, color=INK2)
ax.set(xlabel="Coil distance (mm)", ylabel="Coupling coefficient k", title="Validation 1: coupling vs coil distance (aligned)")
ax.set_ylim(0, None)
ax.legend(fontsize=8.5)
save(fig, "fig1_validation_vs_distance.png")

# Fig 2 - validation vs horizontal offset
ox = np.linspace(0, 0.135, 28)
fig, ax = plt.subplots(figsize=(6.4, 4.2))
ax.plot(ox * 1e3, [k_of(0.100, d) for d in ox], color=BLUE, label="This model (blind prediction)")
ax.plot(F20["x_mm"], F20["k_measured"], "o", ms=8, mfc="none", mec=ORANGE, mew=2, label=f"Measured, {SRC}")
ax.plot(F20["x_mm"], F20["k_their_FEM"], "s", ms=4, color=AQUA, label="Their 3D FEM (COMSOL)")
o = V["offset"]["ours"]
ax.text(0.03, 0.06, f"13 points, mean |error| {o['mean_abs']:.1f}%\nmax {o['max_abs']:.1f}%, R² = {o['r2']:.4f}",
        transform=ax.transAxes, fontsize=9, color=INK2)
ax.set(xlabel="Sideways offset (mm), coil distance 100 mm", ylabel="Coupling coefficient k",
       title="Validation 2: coupling vs sideways offset")
ax.legend(fontsize=8.5, loc="upper right")
save(fig, "fig2_validation_vs_offset.png")

# Fig 3 - k vs offset at four gaps
fig, ax = plt.subplots(figsize=(6.4, 4.2))
for c, g in zip(SERIES, HEAD_G):
    y = Kgrid[ix(GAPS, g)]
    ax.plot(OFFS * 1e3, y, color=c, label=f"{g*1e3:.0f} mm")
    end_label(ax, OFFS * 1e3, y, f"{g*1e3:.0f} mm")
ax.set(xlabel="Sideways offset (mm)", ylabel="Coupling coefficient k", title="Coupling across the SAE J2954 gap range")
ax.set_xlim(0, 228)
ax.set_ylim(0, None)
ax.legend(title="Air gap", fontsize=8.5, title_fontsize=8.5)
save(fig, "fig3_k_vs_offset.png")

# Fig 4 - efficiency map
fig, ax = plt.subplots(figsize=(6.4, 4.5))
pcm = ax.pcolormesh(OFFS * 1e3, GAPS * 1e3, ETA_OPT * 100, cmap="Blues", shading="gouraud", vmin=85, vmax=100)
cs = ax.contour(OFFS * 1e3, GAPS * 1e3, ETA_OPT * 100, levels=[93, 95, 97, 98], colors=INK, linewidths=1.0)
ax.clabel(cs, fmt="%d%%", fontsize=8.5)
fig.colorbar(pcm, ax=ax).set_label("Coil-to-coil efficiency, matched load (%)")
ax.set(xlabel="Sideways offset (mm)", ylabel="Air gap (mm)", title=f"Efficiency map (Q1 = {Q1:.0f}, Q2 = {Q2:.0f})")
ax.grid(False)
save(fig, "fig4_efficiency_map.png")

# Fig 5 - matched vs fixed load
fig, ax = plt.subplots(figsize=(6.4, 4.2))
for c, g in [(BLUE, 0.150), (ORANGE, 0.250)]:
    i = ix(GAPS, g)
    ax.plot(OFFS * 1e3, ETA_OPT[i] * 100, color=c, label=f"{g*1e3:.0f} mm gap, load re-matched")
    ax.plot(OFFS * 1e3, ETA_FIX[i] * 100, color=c, ls="--", label=f"{g*1e3:.0f} mm gap, fixed load")
ax.set(xlabel="Sideways offset (mm)", ylabel="Coil-to-coil efficiency (%)",
       title="Fixed load (tuned at 150 mm, aligned) vs re-matched load")
ax.legend(fontsize=8.5, loc="lower left")
save(fig, "fig5_matched_vs_fixed_load.png")

# Fig 6 - sensitivity to F_R (coil losses)
fig, ax = plt.subplots(figsize=(6.4, 4.2))
for c, fr in zip(SERIES, (1.0, F_R, 2.0, 3.0)):
    q1, q2, *_ = q_pair(fr)
    y = eta_optimal(Kgrid[i_s], q1, q2) * 100
    lab = f"F_R = {fr:.2f}" + (" (calibrated)" if fr == F_R else "")
    ax.plot(OFFS * 1e3, y, color=c, label=lab)
    end_label(ax, OFFS * 1e3, y, f"{fr:.2f}")
ax.set(xlabel="Sideways offset (mm)", ylabel="Coil-to-coil efficiency (%)",
       title=f"Sensitivity to coil resistance (gap {G_S*1e3:.0f} mm)")
ax.set_xlim(0, 228)
ax.legend(fontsize=8.5, loc="lower left")
save(fig, "fig6_sensitivity_resistance.png")

# Fig 7 - sensitivity to coil size
fig, ax = plt.subplots(figsize=(6.4, 4.2))
for c, s in zip(SERIES, SIZES):
    kk, _ = size_curves[s]
    ax.plot(OFFS * 1e3, kk, color=c, label=f"{400*s:.0f} mm")
    end_label(ax, OFFS * 1e3, kk, f"{400*s:.0f} mm")
ax.set(xlabel="Sideways offset (mm)", ylabel="Coupling coefficient k", title=f"Sensitivity to coil size (gap {G_S*1e3:.0f} mm)")
ax.set_xlim(0, 228)
ax.set_ylim(0, None)
ax.legend(title="Coil diameter", fontsize=8.5, title_fontsize=8.5)
save(fig, "fig7_sensitivity_size.png")

# ===================================================================== CONSOLE SUMMARY
print(f"Geometry: wire radius {A_WIRE*1e3:.2f} mm; pitch tx {p1*1e3:.3f} mm, rx {p2*1e3:.3f} mm; "
      f"inner radius tx {TX.inner_radius*1e3:.1f} mm, rx {RX.inner_radius*1e3:.1f} mm")
print(f"Formula cross-check, max difference: {max(r[6] for r in xcheck):.1e} %")
print(f"Table 3 test (131 mm): M {M_131*1e6:.2f} vs {M_MEAS*1e6:.2f} uH ({(M_131-M_MEAS)/M_MEAS*100:+.2f}%), "
      f"k {k_131:.4f} vs {K_MEAS} ({(k_131-K_MEAS)/K_MEAS*100:+.2f}%)")
for tag in ("gap", "offset"):
    o, a_, fe = V[tag]["ours"], V[tag]["theirs_an"], V[tag]["theirs_fem"]
    print(f"{tag:6s}: this model mean {o['mean_abs']:.2f}% max {o['max_abs']:.2f}% R2 {o['r2']:.4f} | "
          f"their analytical mean {a_['mean_abs']:.2f}% | their FEM mean {fe['mean_abs']:.2f}% max {fe['max_abs']:.2f}%")
print(f"Q: R_dc {R1_DC*1e3:.1f}/{R2_DC*1e3:.1f} mOhm, F_R {F_R:.3f}, Q1 {Q1:.0f}, Q2 {Q2:.0f}")
print(f"Design point: k {k_design:.3f}, R_L {RL:.2f} ohm")
for g, d, c_, b_, e_ in eta_check:
    print(f"Efficiency formula check gap {g*1e3:.0f} off {d*1e3:.0f}: closed {c_*100:.4f}% brute-force {b_*100:.4f}% diff {e_*100:.1e} pts")
print(f"\nConservative bound: k reduced by {K_ERR*100:.2f}%; largest efficiency drop over grid: "
      f"matched {np.max(ETA_OPT-ETA_OPT_LO)*100:.2f} pts, fixed {np.max(ETA_FIX-ETA_FIX_LO)*100:.2f} pts")
print("\ngap | off |   k   | matched (low) | fixed (low) | penalty")
for g in HEAD_G:
    for d in HEAD_D:
        i, j = ix(GAPS, g), ix(OFFS, d)
        print(f"{g*1e3:4.0f}|{d*1e3:4.0f} | {Kgrid[i,j]:.3f} |  {ETA_OPT[i,j]*100:5.1f} ({ETA_OPT_LO[i,j]*100:5.1f}) |"
              f" {ETA_FIX[i,j]*100:5.1f} ({ETA_FIX_LO[i,j]*100:5.1f}) | {(ETA_OPT[i,j]-ETA_FIX[i,j])*100:4.1f}")
print("\nSensitivity (gap 175, offset 100): baseline", f"{base*100:.2f}%")
for p, v, n, e in sens:
    print(f"  {p:45s} {v:>9s} {n:22s} {e*100:6.2f}%  ({(e-base)*100:+.2f})")
