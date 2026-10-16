# Formulas used in the model

Every equation implemented in `src/`, in the order the calculation runs, with the file and function where it lives.
Symbols are listed at the end.

---

## 1. Coil coupling (validated coupler model) — `src/wpt_model.py`

**Mutual inductance of two coaxial circular filaments** (Maxwell), radii $a$, $b$, axial distance $c$:

$$
M_{ab}=\mu_0\sqrt{ab}\left[\left(\frac{2}{\kappa}-\kappa\right)K(\kappa)-\frac{2}{\kappa}E(\kappa)\right],
\qquad \kappa^2=\frac{4ab}{(a+b)^2+c^2}
$$

$K$, $E$: complete elliptic integrals of the first and second kind (`scipy.special.ellipk/ellipe`, which take $m=\kappa^2$).

**Laterally offset filaments** (parallel axes, offset $d$): Grover's single-integral formula, evaluated with
64-point Gauss–Legendre quadrature (`mutual_offset_filaments`), cross-checked against a brute-force Neumann
double integral (`mutual_neumann_bruteforce`).

**Spiral coils** are sets of concentric filament turns; the total mutual inductance is the sum over all turn pairs:

$$ M=\sum_{i\in \text{road}}\sum_{j\in \text{vehicle}} M_{ij} $$

**Self-inductance** of a spiral: sum of mutual inductances between distinct turns plus the self term of each turn
(uniform-current round wire of radius $a_w$):

$$ L_{\text{turn}}=\mu_0 R\left[\ln\!\left(\frac{8R}{a_w}\right)-\frac{7}{4}\right] $$

**Coupling coefficient**:

$$ k=\frac{M}{\sqrt{L_1L_2}} $$

**Validation** (`validation/`): blind prediction against 28 published measurements of the 400 mm coupler of
Ibrahim & Mohammed (Batteries 2025): 14 distances (mean error 3.2 %, $R^2=0.9991$), 13 lateral offsets at 100 mm
(3.3 %), and one tabulated value at 131 mm (4.4 %).

---

## 2. Power, switching, lane wander — `src/coupler_layer.py`

**Series–series compensated link at resonance**, both coil currents regulated at rated values:

$$ P_{\text{out}}=\omega M I_1 I_2 - R_2 I_2^2, \qquad P_{\text{in}}=\omega M I_1 I_2 + R_1 I_1^2 $$

with $\omega=2\pi\cdot 85\,\text{kHz}$ (SAE J2954).

**Switch-on rule** (only the road coil nearest the receiver can be on):

$$ \text{on} \iff P_{\text{out}}>0 \;\;\text{and}\;\; P_{\text{out}} \ge \eta_{\text{on}}\,P_{\text{in}} $$

**Row average** for a receiver at lateral offset $y$, over one coil pitch $s$, normalised by the aligned standing
output $P_0$ (`row_average`):

$$ \epsilon_{\text{out}}(y)=\frac{1}{sP_0}\int_{-s/2}^{s/2} P_{\text{out}}(x,y)\,\mathbb{1}_{\text{on}}\,dx,
\qquad \epsilon_{\text{in}}(y)=\frac{1}{sP_0}\int_{-s/2}^{s/2} P_{\text{in}}(x,y)\,\mathbb{1}_{\text{on}}\,dx $$

**Lane wander**: offset $y\sim\mathcal N(0,\sigma^2)$; with $f(y)$ the half-normal density of $|y|$
(`wander_average`):

$$ \bar p=\int_0^\infty f(y)\,\epsilon_{\text{out}}(y)\,dy,
\qquad \bar\eta=\frac{\int_0^\infty f(y)\,\epsilon_{\text{out}}(y)\,dy}{\int_0^\infty f(y)\,\epsilon_{\text{in}}(y)\,dy} $$

**Coil-size scaling**: scaling every length by $\lambda$ multiplies $M$ and $L$ by $\lambda$, so $k$ is unchanged.
A coil of diameter $D=0.4\lambda$ m at gap $g$, offset $y$, pitch $s$ is evaluated as the validated coil at
$g/\lambda$, $y/\lambda$, $s/\lambda$. The quality factor is held at the validated value (conservative).

---

## 3. Corridor demand — `src/corridor.py`

**Energy delivered per equipped vehicle per km** (class $c$: receivers $n_c$, receiver rating $P_{\text{rx}}$,
speed $v_c$):

$$ e_c=\frac{n_c\,P_{\text{rx}}\,\bar p_c}{v_c} \quad [\text{kWh/km}] $$

**Hourly grid demand of the wireless lanes** (flow $q_c(t)$ in veh/h, equipped share $a_c$, electrified length
$L_e$, power-electronics efficiency $\eta_{\text{pe}}$):

$$ D_{\text{w}}(t)=\sum_c \frac{q_c(t)\,a_c\,e_c\,L_e}{\bar\eta_c\,\eta_{\text{pe}}} $$

**Inverter sizing (compound Poisson)**: in the busiest hour, class-$c$ vehicles on a section of length $\ell$ are
Poisson with mean $\mu_c=(q_c/2)\,a_c\,\ell/v_c$ and each brings its $n_c$ receivers at once:

$$ R=\sum_c n_c N_c,\qquad N_c\sim\text{Poisson}(\mu_c),
\qquad N^\ast=\min\{n:\Pr(R>n)<10^{-3}\},\;\; N^\ast\ge\max_c n_c $$

Inverter capacity per lane-km $=N^\ast P_{\text{rx}}/\ell_{\text{km}}$ (`installed_power_per_km`).
The same distribution over the whole section gives the firm power $P_{\text{firm}}$ (`corridor_peak_power`).

**Road loads**: lighting (on when solar zenith $>96^\circ$) + toll plaza + traffic-management devices (`infra_load`).

---

## 4. Solar output — `src/pv_model.py`

Typical-year weather (TMYx, Pune) → sun position (NREL SPA) → plane-of-array irradiance (Perez model, albedo 0.2) →
cell temperature (Sandia model) → DC power (PVWatts, $\gamma=-0.37\,\%/^\circ$C) → AC power after 14 % system losses
and 96 % inverter efficiency, per kWp. Lifetime-average degradation factor:

$$ \bar d=\frac{1}{n}\sum_{k=0}^{n-1}(1-d)^k,\qquad d=1.33\,\%/\text{yr},\; n=25 $$

---

## 5. Least-cost supply (linear programme) — `src/optimiser.py`

Decision variables: solar $C_{\text{pv}}$, usable battery energy $E_b$, battery power $P_b$, grid connection $G$, and
for every hour $t$: grid import $g_t$, solar used $u_t$, charge $c_t$, discharge $d_t$, stored energy $s_t$.

$$
\begin{aligned}
\min\;& \textstyle\sum_j \alpha_j X_j+\sum_t \pi_t g_t \\
\text{s.t. }\;& g_t+u_t+d_t=D_{\text{w}}(t)+D_{\text{r}}(t)+c_t \\
& 0\le u_t\le C_{\text{pv}}\,y_t,\qquad 0\le g_t\le G,\qquad C_{\text{pv}}\le\bar C_{\text{pv}} \\
& s_{t+1}=s_t+\sqrt{\eta_{\text{rt}}}\,c_t-d_t/\sqrt{\eta_{\text{rt}}},\qquad s_{8760}=s_0 \\
& 0\le s_t\le E_b,\qquad 0\le c_t,d_t\le P_b\le E_b/2 \\
& G+P_b\ge P_{\text{firm}},\qquad s_t\ge\tau\,(P_{\text{firm}}-G),\;\tau=0.25\,\text{h}
\end{aligned}
$$

**Annualised cost** of each asset $X_j$ (capital recovery factor, real discount rate $r$, life $n$):

$$ \text{CRF}=\frac{r(1+r)^n}{(1+r)^n-1},\qquad \alpha_j=\text{CRF}\cdot\text{capex}_j+\text{O\&M}_j $$

Real discount rate: $r=1.0921/1.04-1=5.0\,\%$ (CERC nominal 9.21 %, RBI 4 % inflation target). Solved with HiGHS.

---

## 6. Cost per delivered kWh — `src/run_study4.py`

**Road hardware per lane-km** (coverage $\kappa=D/s$, switch cost $c_{\text{sw}}$ per coil, distribution share $\rho$):

$$ C_{\text{road}}=(1+\rho)\Big(10^3c_{\text{coil}}\,\kappa\frac{D}{D_{\text{ref}}}+\frac{10^3c_{\text{sw}}}{s}
+c_{\text{inv}}\frac{N^\ast P_{\text{rx}}}{\ell_{\text{km}}}\Big)+10^3c_{\text{civ}} $$

**Levelised cost per kWh delivered to vehicles**:

$$ \text{LCOD}=\frac{A_{\text{road}}+A_{\text{sup}}\,E_{\text{w}}/(E_{\text{w}}+E_{\text{r}})}{E_{\text{del}}} $$

**Avoided CO₂** $=(\text{demand}-\text{grid import})\times 0.705$ t/MWh (CEA combined margin).

**Diesel-parity electricity price** for a truck (diesel use $F$ L/km, price $p_d$, electric use $e$ kWh/km):

$$ p^\ast=\frac{F\,p_d}{e} = \frac{(0.360\text{–}0.538)\times 98.55}{1.4}\approx \text{Rs }25\text{–}38/\text{kWh} $$

**Braking-zone harvest** (upper bound): vehicles/day × 72.4 J per pass per module × modules × 365.
Kinetic energy shed by a car: $\tfrac12 m(v_1^2-v_2^2)$.

---

## Symbols

| Symbol | Meaning |
|---|---|
| $M, L, k$ | mutual inductance, self-inductance, coupling coefficient |
| $I_1, I_2, R_1, R_2$ | road / vehicle coil current and resistance |
| $s, D, \lambda, \kappa$ | coil pitch, coil diameter, scale factor, coverage $D/s$ |
| $\eta_{\text{on}}$ | switch-on efficiency threshold |
| $y, \sigma$ | lateral offset, lane-wander standard deviation |
| $\bar p, \bar\eta$ | wander-averaged delivered power (fraction of aligned) and efficiency |
| $q_c, a_c, n_c, v_c$ | flow, equipped share, receivers per vehicle, speed of class $c$ |
| $P_{\text{rx}}$ | rated power per receiver (25 kW) |
| $\eta_{\text{pe}}$ | power-electronics efficiency outside the coils (0.86) |
| $C_{\text{pv}}, E_b, P_b, G$ | solar, battery energy, battery power, grid connection |
| $\pi_t, y_t$ | tariff and solar output per kWp in hour $t$ |
| LCOD | levelised cost per kWh delivered to vehicles |
