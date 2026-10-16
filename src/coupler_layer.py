"""
Layer 1: from validated coil physics to the two numbers the corridor model needs.

For a row of road coils and a vehicle coil passing over it, the corridor model needs:
  pbar  = average power delivered over the row, as a fraction of the aligned standing power
  eta   = energy-weighted coil-to-coil efficiency while coils are on
Both depend on: coil pitch (spacing), air gap, sideways offset, coil size, and the switch-on rule.

What this layer adds to the plain coil model:
  (a) Lane wander. Real vehicles do not drive centred. The sideways offset y is random, normally distributed
      about the lane centre with standard deviation sigma (pavement-engineering data). We average over it.
  (b) Coil size scaling. All formulas for coreless coils are geometric: if every length (radii, pitch,
      gap, offset, wire) is multiplied by lam, the coupling coefficient k is unchanged exactly, and the
      quality factor Q grows ~ lam^2 (validation/METHODS.md). We keep Q at the validated value (conservative), so
      a coil of size lam at gap g behaves like the validated coil at gap g/lam, offset y/lam, pitch s/lam.
  (c) The switch-on threshold eta_on is a design choice, not a constant.

Everything is computed from the validated model (see validation/) (wpt_model.py).
"""
import numpy as np
from scipy.optimize import brentq
from wpt_model import SpiralCoil, mutual_inductance, litz_dc_resistance, OMEGA

# ---------------------------------------------------------------- validated coil pair (as validated in validation/)
R_OUT, N1, N2, A_WIRE = 0.200, 43, 11, 0.95e-3
L1_MEAS, L2_MEAS = 795e-6, 81e-6
p1 = brentq(lambda p: SpiralCoil(R_OUT, N1, p, wire_radius=A_WIRE).self_inductance() - L1_MEAS, 1.9e-3, 4.4e-3)
p2 = brentq(lambda p: SpiralCoil(R_OUT, N2, p, wire_radius=A_WIRE).self_inductance() - L2_MEAS, 1.9e-3, 0.017)
TX = SpiralCoil(R_OUT, N1, p1, wire_radius=A_WIRE)
RX = SpiralCoil(R_OUT, N2, p2, wire_radius=A_WIRE)
R1_DC = litz_dc_resistance(TX, 180, 0.102e-3)
R2_DC = litz_dc_resistance(RX, 180, 0.102e-3)
F_R = 7.0 / (2.25 ** 2 * R1_DC + 4.92 ** 2 * R2_DC)          # calibrated on the reported 7.0 W copper loss
R1, R2 = F_R * R1_DC, F_R * R2_DC
I1, I2 = 1.71, 4.29                                          # rated currents of the reference design

RHO = np.linspace(0.0, 0.80, 161)                            # centre-to-centre distance grid, 5 mm steps
_M = {}


def m_of_rho(gap, rho):
    key = round(gap, 6)
    if key not in _M:
        _M[key] = np.array([mutual_inductance(TX, RX, gap, r) for r in RHO])
    return np.interp(rho, RHO, _M[key], right=0.0)


QFAC = dict(f=1.0)        # quality-factor multiplier (sensitivity): resistances scale as 1/f


def power(M):
    pt = OMEGA * M * I1 * I2
    return pt - R2 / QFAC["f"] * I2 ** 2, R1 / QFAC["f"] * I1 ** 2 + pt              # (output, input)


def row_average(gap, pitch, y, eta_on, n=601):
    """Validated-scale coil. Returns (pbar, e_out_rel, e_in_rel) over one pitch period.
    Only the nearest road coil is energised, and only while delivering positive power at eta >= eta_on."""
    x = np.linspace(-pitch / 2, pitch / 2, n)
    p_out, p_in = power(m_of_rho(gap, np.hypot(x, y)))
    valid = (p_out > 0) & (p_in > 0)
    on = valid & (p_out >= eta_on * np.where(valid, p_in, np.inf))
    p_ref = power(m_of_rho(gap, 0.0))[0]
    e_out = np.trapezoid(np.where(on, p_out, 0.0), x) / (pitch * p_ref)
    e_in = np.trapezoid(np.where(on, p_in, 0.0), x) / (pitch * p_ref)
    return e_out, e_out, e_in


def wander_average(gap, pitch, sigma, eta_on, lam=1.0, n_y=49):
    """Average over a normal lateral offset (s.d. sigma) for a coil scaled by lam.
    Returns pbar (fraction of aligned standing power) and the energy-weighted efficiency."""
    g, s = gap / lam, pitch / lam
    if sigma <= 0:
        pb, eo, ei = row_average(g, s, 0.0, eta_on)
        return pb, (eo / ei if ei > 0 else np.nan)
    ys = np.linspace(0.0, 3.5 * sigma, n_y)                  # |y| is half-normal
    w = np.exp(-0.5 * (ys / sigma) ** 2)
    w /= np.trapezoid(w, ys)
    eo = np.array([row_average(g, s, y / lam, eta_on)[1] for y in ys])
    ei = np.array([row_average(g, s, y / lam, eta_on)[2] for y in ys])
    EO, EI = np.trapezoid(w * eo, ys), np.trapezoid(w * ei, ys)
    return EO, (EO / EI if EI > 0 else np.nan)


if __name__ == "__main__":
    print(f"check: aligned 150 mm, pitch 0.4 m, eta_on 0.90 -> {wander_average(0.15, 0.4, 0.0, 0.90)}")
    print(f"check: wander 254 mm                         -> {wander_average(0.15, 0.4, 0.254, 0.90)}")
