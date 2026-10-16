"""
Study 1 - Coil model for inductive (wireless) EV charging.

What this file computes, in plain words:
  * how strongly two circular spiral coils are magnetically linked
    (mutual inductance M and coupling coefficient k),
  * for any air gap (vertical distance) and sideways offset (lateral misalignment),
  * and from that, the best possible coil-to-coil efficiency.

Physics used (all standard, textbook-level):
  1. Each spiral coil is treated as a set of concentric circular turns (filaments).
  2. Mutual inductance between two coaxial turns  -> Maxwell's formula
     (complete elliptic integrals K and E).
  3. Mutual inductance between two turns with a sideways offset -> Grover's
     single-integral formula for circular filaments with parallel axes.
  4. Self-inductance of one turn of round wire with uniform current
     (uniform because Litz wire is assumed):  L = mu0*R*(ln(8R/a) - 7/4).
  5. Coil self-inductance = sum of turn self-inductances + all turn-to-turn
     mutual inductances inside the same coil.
  6. Coupling k = M / sqrt(L1*L2).
  7. Series-series compensated link at resonance:
       best efficiency (optimal load):  eta = x / (1 + sqrt(1 + x))^2,  x = k^2 Q1 Q2
       efficiency with a fixed load R_L:
         eta = (wM)^2 R_L / [ (R2 + R_L) * ( R1 (R2 + R_L) + (wM)^2 ) ]

Units: SI throughout (metres, henries, ohms, hertz).
"""

import numpy as np
from scipy.special import ellipk, ellipe

MU0 = 4e-7 * np.pi
F_SAE = 85e3                      # SAE J2954 nominal operating frequency, Hz
OMEGA = 2 * np.pi * F_SAE

# Gauss-Legendre nodes on [0, pi] for Grover's integral (64 points is far
# more than needed; accuracy is checked against a brute-force Neumann integral).
_GL_X, _GL_W = np.polynomial.legendre.leggauss(64)
_PHI = 0.5 * np.pi * (_GL_X + 1.0)
_PHI_W = 0.5 * np.pi * _GL_W


def _psi(k):
    """Psi(k) = (2/k - k) K(k) - (2/k) E(k);  scipy uses parameter m = k^2."""
    m = k * k
    return (2.0 / k - k) * ellipk(m) - (2.0 / k) * ellipe(m)


def mutual_coaxial_filaments(a, b, c):
    """Maxwell's formula: two coaxial circular filaments of radii a, b at axial distance c."""
    k = np.sqrt(4.0 * a * b / ((a + b) ** 2 + c ** 2))
    return MU0 * np.sqrt(a * b) * _psi(k)


def mutual_offset_filaments(Rp, Rs, c, d):
    """
    Grover's formula: circular filaments with parallel axes.
    Rp, Rs : radii of primary / secondary turn (broadcastable arrays)
    c      : axial distance between the turn planes
    d      : lateral (sideways) offset between the axes
    """
    Rp = np.asarray(Rp, float)[..., None]
    Rs = np.asarray(Rs, float)[..., None]
    alpha = Rs / Rp
    beta = c / Rp
    dl = d / Rs
    V = np.sqrt(1.0 + dl ** 2 - 2.0 * dl * np.cos(_PHI))
    k = np.sqrt(4.0 * alpha * V / ((1.0 + alpha * V) ** 2 + beta ** 2))
    k = np.clip(k, 1e-12, 1.0 - 1e-15)
    integrand = (1.0 - dl * np.cos(_PHI)) * _psi(k) / V ** 1.5
    return (MU0 / np.pi) * np.sqrt(Rp[..., 0] * Rs[..., 0]) * (integrand @ _PHI_W)


def mutual_neumann_bruteforce(a, b, c, d, n=1500):
    """Independent check: direct double Neumann integral, two filaments (slow, used only for validation)."""
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    T1, T2 = np.meshgrid(th, th, indexing="ij")
    dx = a * np.cos(T1) - (d + b * np.cos(T2))
    dy = a * np.sin(T1) - b * np.sin(T2)
    r = np.sqrt(dx ** 2 + dy ** 2 + c ** 2)
    integrand = a * b * np.cos(T1 - T2) / r
    return MU0 / (4 * np.pi) * integrand.sum() * (2 * np.pi / n) ** 2


class SpiralCoil:
    """Flat circular spiral coil approximated as N concentric turns."""

    def __init__(self, outer_radius, turns, pitch, wire_radius=None):
        self.R_out = outer_radius
        self.N = int(turns)
        self.p = pitch
        self.a = pitch / 2.0 if wire_radius is None else wire_radius
        # turn centre-line radii, outermost first
        self.radii = outer_radius - self.a - pitch * np.arange(self.N)
        if self.radii[-1] <= self.a:
            raise ValueError("Too many turns for this outer radius and pitch.")

    @property
    def inner_radius(self):
        return self.radii[-1] - self.a

    def self_inductance(self):
        R = self.radii
        L_turns = np.sum(MU0 * R * (np.log(8.0 * R / self.a) - 1.75))
        Ri, Rj = np.meshgrid(R, R, indexing="ij")
        off = ~np.eye(self.N, dtype=bool)
        L_mut = np.sum(mutual_coaxial_filaments(Ri[off], Rj[off], 0.0))
        return L_turns + L_mut


def mutual_inductance(tx, rx, gap, offset):
    """Total mutual inductance between two spiral coils (gap = axial distance, offset = lateral)."""
    Ri, Rj = np.meshgrid(tx.radii, rx.radii, indexing="ij")
    if offset == 0:
        return float(np.sum(mutual_coaxial_filaments(Ri, Rj, gap)))
    return float(np.sum(mutual_offset_filaments(Ri, Rj, gap, offset)))


def coupling(tx, rx, gap, offset, L1=None, L2=None):
    L1 = tx.self_inductance() if L1 is None else L1
    L2 = rx.self_inductance() if L2 is None else L2
    return mutual_inductance(tx, rx, gap, offset) / np.sqrt(L1 * L2)


RHO_CU = 1.72e-8                  # copper resistivity at 20 C, ohm*m


def litz_dc_resistance(coil, n_strands, strand_diameter, rho=RHO_CU):
    """DC resistance of a coil wound with Litz wire: rho * (total wire length) / (total copper area)."""
    length = np.sum(2 * np.pi * coil.radii)
    area = n_strands * np.pi * (strand_diameter / 2) ** 2
    return rho * length / area


def eta_optimal(k, Q1, Q2):
    """Maximum coil-to-coil efficiency of a series-series link (load matched to every position)."""
    x = (k ** 2) * Q1 * Q2
    return x / (1.0 + np.sqrt(1.0 + x)) ** 2


def eta_fixed_load(M, R1, R2, RL, omega=OMEGA):
    """Coil-to-coil efficiency of a series-series link at resonance with a fixed load resistance."""
    wm2 = (omega * M) ** 2
    return wm2 * RL / ((R2 + RL) * (R1 * (R2 + RL) + wm2))
