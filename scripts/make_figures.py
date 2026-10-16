"""
Builds every figure of the paper from the result files in results/ (and the validated coupler layer in src/),
so the figures cannot drift from the results. IEEE single column 3.5 in, 8 pt serif, vector PDF + PNG.
Run from the repository root, after src/run_model.py:   python scripts/make_figures.py
"""
import csv
import json
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "figures")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "src"))
from coupler_layer import wander_average  # noqa: E402

BLUE, ORANGE, AQUA, YELLOW, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#888888"
INK, INK2, GRID = "#000000", "#444444", "#dddddd"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral"], "mathtext.fontset": "stix",
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7,
    "axes.edgecolor": INK2, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.3, "legend.frameon": False, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02, "pdf.fonttype": 42, "axes.titleweight": "normal",
})
W = 3.5


def rows(name):
    with open(os.path.join(RES, name)) as f:
        return list(csv.DictReader(f))


def fl(r, k):
    return float(r[k])


def save(fig, name):
    fig.savefig(os.path.join(OUT, name))
    fig.savefig(os.path.join(OUT, name.replace(".pdf", ".png")), dpi=200)
    plt.close(fig)


SUM = json.load(open(os.path.join(RES, "summary.json")))
BEST = SUM["best_design"]

# ------------------------------------------------------------------ Fig. 3: lane wander -> delivered power, efficiency
sig = np.linspace(0.0, 0.35, 15)
fig, (a, b) = plt.subplots(2, 1, figsize=(W, 4.1), sharex=True)
for lam, c in ((1.0, BLUE), (1.5, ORANGE), (2.0, AQUA)):
    for gap, ls in ((0.150, "-"), (0.250, "--")):
        res = [wander_average(gap, 0.4 * lam, s, 0.80, lam=lam) for s in sig]
        a.plot(sig * 1e3, [r[0] * 100 for r in res], color=c, ls=ls,
               label=f"{400*lam:.0f} mm coils, {gap*1e3:.0f} mm gap")
        b.plot(sig * 1e3, [r[1] * 100 for r in res], color=c, ls=ls)
for ax in (a, b):
    ax.axvspan(218, 285, color=GREY, alpha=0.15, lw=0)
a.text(254, 92, "measured\nwander", ha="center", va="top", fontsize=6.5, color=INK2)
a.set_ylabel("Delivered power (% of aligned)")
a.set_ylim(0, 100)
h, l = a.get_legend_handles_labels()
a.set_title("(a) average delivered power over the coil row", fontsize=8, loc="left")
b.set_ylabel("Coil-to-coil efficiency (%)")
b.set_xlabel("Lane-wander standard deviation (mm)")
b.set_ylim(88, 100)
b.set_title("(b) energy-weighted efficiency while coils are on", fontsize=8, loc="left")
fig.legend(h, l, loc="lower center", ncol=2, fontsize=6.5, bbox_to_anchor=(0.55, -0.02))
fig.tight_layout(h_pad=0.6, rect=(0, 0.12, 1, 1))
save(fig, "fig_wander.pdf")

# ------------------------------------------------------------------ Fig. 4: conventional prediction vs physics
C = rows("C_centred_vs_wander.csv")
fig, ax = plt.subplots(figsize=(W, 2.5))
pred = np.array([fl(r, "lcod_pred") for r in C])
true = np.array([fl(r, "lcod_true") for r in C])
lam = np.array([fl(r, "lam") for r in C])
ok = np.isfinite(pred) & np.isfinite(true) & (true < 400)
for l, c in ((1.0, BLUE), (1.25, YELLOW), (1.5, ORANGE), (2.0, AQUA)):
    m = ok & (lam == l)
    ax.plot(pred[m], true[m], "o", ms=3.2, mfc="none", mec=c, mew=0.9, label=f"{400*l:.0f} mm coils")
lim = [0, max(true[ok].max(), pred[ok].max()) * 1.05]
ax.plot(lim, lim, color=INK2, lw=0.7, ls=":")
ax.text(lim[1] * 0.62, lim[1] * 0.56, "prediction = truth", rotation=33, fontsize=6.5, color=INK2)
conv = SUM["centred_pick"]
ax.annotate("centred-vehicle\nchoice", (conv["lcod_pred"], conv["lcod_true"]), xytext=(conv["lcod_pred"] + 45, conv["lcod_true"] - 30),
            fontsize=6.5, arrowprops=dict(arrowstyle="->", lw=0.6, color=INK2))
ax.set(xlabel="Predicted with centred vehicles, Rs/kWh", ylabel="With measured lane wander, Rs/kWh")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.legend(loc="lower right")
fig.tight_layout()
save(fig, "fig_conventional.pdf")

# ------------------------------------------------------------------ Fig. 5: design map (cost per delivered kWh)
B = rows("B_design_sweep_mid.csv")
lams = sorted({fl(r, "lam") for r in B})
covs = sorted({fl(r, "cov") for r in B})
Z = np.full((len(lams), len(covs)), np.nan)
for r in B:
    if r["valid"] != "True":
        continue
    i, j = lams.index(fl(r, "lam")), covs.index(fl(r, "cov"))
    v = fl(r, "lcod_Rs_kWh")
    Z[i, j] = v if np.isnan(Z[i, j]) else min(Z[i, j], v)            # best switch-on threshold per cell
fig, ax = plt.subplots(figsize=(W, 2.2))
im = ax.imshow(Z, cmap="Blues_r", aspect="auto", origin="lower", vmin=np.nanmin(Z), vmax=min(np.nanmax(Z), 3 * np.nanmin(Z)))
for i in range(len(lams)):
    for j in range(len(covs)):
        vmin_, vmax_ = np.nanmin(Z), min(np.nanmax(Z), 3 * np.nanmin(Z))
        frac = (min(Z[i, j], vmax_) - vmin_) / (vmax_ - vmin_)
        ax.text(j, i, f"{Z[i, j]:.0f}", ha="center", va="center", fontsize=7,
                color="white" if frac < 0.45 else INK)
ax.set_xticks(range(len(covs)))
ax.set_xticklabels([f"{c*100:.0f}%" for c in covs])
ax.set_yticks(range(len(lams)))
ax.set_yticklabels([f"{400*l:.0f}" for l in lams])
ax.set_xlabel("Coil coverage of the lane (coil diameter / pitch)")
ax.set_ylabel("Road-coil diameter (mm)")
ax.grid(False)
cb = fig.colorbar(im, ax=ax, pad=0.02)
cb.set_label("Rs per kWh delivered", fontsize=7)
cb.ax.tick_params(labelsize=7)
fig.tight_layout()
save(fig, "fig_design_map.pdf")

# ------------------------------------------------------------------ Fig. 7: break-even vs adoption
E = rows("E_breakeven_heavy.csv")
x = np.array([fl(r, "equipped_heavy_per_day") for r in E])
y = np.array([fl(r, "lcod_Rs_kWh") for r in E])
yg = np.array([fl(r, "lcod_grid_only_Rs_kWh") for r in E])
fig, ax = plt.subplots(figsize=(W, 2.4))
ax.axhspan(18, 30, color=AQUA, alpha=0.18, lw=0)
ax.text(x.max() * 0.98, 19.5, "public DC fast charging (retail)", ha="right", va="center", fontsize=6.5, color=INK2)
ax.axhspan(25, 38, color=YELLOW, alpha=0.18, lw=0)
ax.text(x.max() * 0.98, 33, "diesel parity, e-truck", ha="right", va="center", fontsize=6.5, color=INK2)
ax.plot(x, y, "-o", color=BLUE, ms=3, label="solar + battery + grid (optimised)")
ax.plot(x, yg, "--", color=ORANGE, label="grid only")
mid = [r for r in E if abs(fl(r, "heavy_mult") - 1.0) < 1e-9][0]
ax.plot([fl(mid, "equipped_heavy_per_day")], [fl(mid, "lcod_Rs_kWh")], "s", ms=5, mfc="none", mec=INK)
ax.annotate("mid\nscenario", (fl(mid, "equipped_heavy_per_day"), fl(mid, "lcod_Rs_kWh")),
            xytext=(fl(mid, "equipped_heavy_per_day") + x.max() * 0.08, fl(mid, "lcod_Rs_kWh") + 25), fontsize=6.5,
            arrowprops=dict(arrowstyle="->", lw=0.6, color=INK2))
ax.set_yscale("log")
ax.set_yticks([20, 30, 50, 100, 200, 300])
ax.set_yticklabels(["20", "30", "50", "100", "200", "300"])
ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set(xlabel="Equipped buses and trucks per day (both directions)", ylabel="Cost per kWh delivered (Rs)")
ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.98))
fig.tight_layout()
save(fig, "fig_breakeven.pdf")

# ------------------------------------------------------------------ Fig. 8: sensitivity (tornado)
F = rows("F_sensitivity.csv")
base = fl(F[0], "base_lcod")
F = sorted(F, key=lambda r: abs(fl(r, "high_lcod") - fl(r, "low_lcod")))
fig, ax = plt.subplots(figsize=(W, 3.6))
XMAX = base * 2.0
for i, r in enumerate(F):
    lo, hi = fl(r, "low_lcod"), fl(r, "high_lcod")
    for v, c in ((lo, BLUE), (hi, ORANGE)):
        ax.barh(i, min(v, XMAX) - base, left=base, color=c, height=0.6)
        if v > XMAX:
            ax.text(XMAX * 0.99, i, f"{v:.0f} \u2192", ha="right", va="center", fontsize=6.5, color="white")
ax.axvline(base, color=INK, lw=0.7)
ax.set_yticks(range(len(F)))
ax.set_yticklabels([r["parameter"] for r in F], fontsize=6.2)
ax.set_xlim(base * 0.65, XMAX)
ax.set_xlabel("Cost per kWh delivered (Rs), mid scenario")
ax.grid(axis="y", visible=False)
ax.plot([], [], color=BLUE, lw=5, label="low value")
ax.plot([], [], color=ORANGE, lw=5, label="high value")
ax.legend(loc="lower right")
fig.tight_layout()
save(fig, "fig_tornado.pdf")
print("figures:", sorted(os.listdir(OUT)))

# ------------------------------------------------------------------ Fig. 6: hourly dispatch, one dry and one monsoon week
Z = np.load(os.path.join(RES, "dispatch_base.npz"))
fig, axs = plt.subplots(2, 1, figsize=(W, 3.5), sharey=True)
for ax, (start, title) in zip(axs, ((24 * 59, "(a) a dry-season week (1-7 March)"),
                                    (24 * 195, "(b) a monsoon week (15-21 July)"))):
    sl = slice(start, start + 24 * 7)
    t = np.arange(24 * 7) / 24
    pv = Z["u"][sl]
    dis = Z["d"][sl]
    g = Z["g"][sl]
    ch = Z["c"][sl]
    ax.stackplot(t, pv - np.minimum(ch, pv), dis, g, colors=[YELLOW, AQUA, GREY], alpha=0.85, lw=0,
                 labels=["solar to load", "battery to load", "grid import"])
    ax.fill_between(t, -ch, 0, color=BLUE, alpha=0.35, lw=0, label="battery charging")
    ax.axhline(0, color=INK2, lw=0.5)
    ax.plot(t, Z["wpt"][sl] + Z["infra"][sl], color=INK, lw=0.8, label="demand (charging + road loads)")
    ax.plot(t, Z["infra"][sl], color=BLUE, lw=0.8, ls="--", label="road loads only")
    ax.set_title(title, fontsize=8, loc="left")
    ax.set_xlim(0, 7)
    ax.set_ylabel("Power (kW)")
axs[1].set_xlabel("Day of the week")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, fontsize=6.5, bbox_to_anchor=(0.55, -0.02))
fig.tight_layout(h_pad=0.6, rect=(0, 0.13, 1, 1))
save(fig, "fig_dispatch.pdf")
print("dispatch figure done")
