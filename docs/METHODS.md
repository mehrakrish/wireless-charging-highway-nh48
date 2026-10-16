# Methods in plain words

## The question

The coil studies answered "how well do the coils work?". This model asks the question a highway authority asks:
**if we electrify a real stretch of Indian highway, what does each kWh delivered to a vehicle cost, how much
of the energy can the road supply itself from solar and batteries, and which coil design should we build?**

Published system studies take the energy delivered to vehicles from a fixed coil efficiency (e.g. 90 %) or from the
vehicles' driving power; none models how much power a coil can pass to a vehicle that is not centred over it. Real vehicles drift sideways in the lane
("lane wander"); pavement engineers have measured this drift for decades (standard deviation about 220-290 mm).
Our road coils are only 200-400 mm in radius, so this drift is large. The model feeds the drift through our
validated coil model and follows the effect all the way to rupees per kWh.

## The chain (three layers)

### Layer 1: coil physics with lane wander (`coupler_layer.py`)

1. **Coil model.** Same as the validated coupler model (`validation/`): mutual inductance from Maxwell's and Grover's formulas, validated blind
   against 28 published measurements (mean error 3.2-3.3 %).
2. **Power along the row.** As the vehicle moves along a row of road coils, the coupling (M) changes with
   position. Power out and power in follow the series-series formulas
   P_out = wMI1I2 - R2 I2^2,   P_in = wMI1I2 + R1 I1^2.
3. **Switching rule.** Only the road coil under the vehicle is on, and only while it works efficiently enough:
   P_out >= eta_on x P_in. eta_on (the "switch-on threshold") is a design choice (50-95 %).
4. **Row average.** Average P_out over one coil spacing (pitch) -> "pbar", the average power as a fraction of the
   power a perfectly aligned, standing vehicle would get. Ratio of energy out to energy in -> efficiency.
5. **Lane wander.** Repeat for every sideways offset y and average with the bell-curve (normal) probability of
   each offset, standard deviation 250 mm.
6. **Coil size.** Coreless-coil formulas are purely geometric: making every length lam times larger leaves the
   coupling coefficient k unchanged. So a coil lam times larger at gap g behaves like our validated coil at gap
   g/lam. Its quality factor Q would grow (about lam^2); we keep the validated Q, which is conservative.

**Key finding of layer 1:** wander barely changes efficiency (coils only switch on where coupling is good) but
cuts the delivered power by roughly a third to a half. The vehicle simply receives less energy.

### Layer 2: the highway section (`corridor.py`)

1. **Traffic.** Real monthly toll counts by class (car, LCV, bus/truck, multi-axle truck) at Somatne Phata, NH-48
   (MSRDC, Aug 2025 - May 2026), plus the exempt and violating buses, trucks and LCVs listed in the same statements
   (+54-57 % / +32-35 %), spread over the 24 hours with a measured Indian highway profile (UPEIDA).
2. **Who uses the charging lane.** All buses, LCVs and trucks keep left; 30 % of cars use that lane (assumption,
   varied).
3. **Who is equipped.** Explicit scenario shares of each class that are EVs with receivers (low / mid / high; they
   are assumptions, not forecasts; break-even is reported per equipped heavy vehicle per day).
4. **Energy per vehicle per km:** e = receivers x 25 kW x pbar / speed.
5. **Grid demand each hour:** sum over classes of (flow x equipped share x e x 10 km) / (coil efficiency x 0.86).
   0.86 = power electronics, chosen so that the end-to-end DC efficiency matches the measured 85 % of the
   Purdue US-231 and Electreon pilots.
6. **Inverter size.** Each 100 m section has one inverter. The number of vehicles on it at once is random (Poisson),
   and each vehicle brings all its receivers together (compound Poisson). The inverter is sized so that, in the
   busiest hour, the chance of more receivers than its rating is below 1 in 1,000, and never below one vehicle.
7. **Firm power.** The same calculation for the whole section gives the instantaneous peak; grid + battery must
   cover it, and the battery must always hold 15 minutes of the shortfall.
8. **The road's own loads.** Street lighting where Indian rules require it (toll plaza +- 500 m, interchanges),
   on at night (computed from the sun's position); the toll plaza (26 kW average, from an Indian plaza's solar
   plant output); traffic-management cameras and signs (NHAI spacing).

### Layer 3: least-cost supply (`optimiser.py`, `pv_model.py`)

1. **Solar output** per kWp for each of the 8,760 hours from the Pune typical-year weather file (pvlib: Perez
   sky model, Sandia cell temperature, PVWatts losses, Indian field degradation 1.33 %/yr).
2. **Linear programme.** Chooses solar size, battery size and grid connection size together with the hour-by-hour
   operation, to minimise yearly cost: annualised equipment cost (real discount rate 5 %) + electricity bought at the
   flat MSEDCL EV tariff (time-of-day tariff as a sensitivity). Solar is limited to a 2.2 m strip of right-of-way. Constraints: energy balance every hour, solar available, battery charge/discharge and state of charge,
   grid limit. Solved with HiGHS (open-source solver).
3. **Cost per delivered kWh** = (yearly cost of road hardware + the charging lanes' share of yearly supply cost) /
   energy delivered to vehicles.

## The analyses (src/run_model.py)

| Section | What it does |
|---|---|
| A | Physics table: pbar and efficiency, centred vs wander, all 80 designs and 4 classes |
| B | Every coil design (4 sizes x 4 coverages x 6 thresholds) with the supply optimised for each -> best design |
| C | The same model with centred vehicles, for every design: what it predicts vs the truth with wander |
| D | Best design under low / mid / high adoption |
| E | Cost per kWh as equipped buses/trucks grow from 0.25x to 10x the mid case (design re-chosen) -> break-even |
| F | One-at-a-time sensitivity on 20 inputs |
| M | Monte Carlo: 300 joint random draws of the uncertain inputs -> 5-95 % range |
| G | Braking-zone harvesting at the toll plaza (measured harvester output) |

## Limitations (also in the paper)

1. Coreless circular coils only; ferrite or DD pads may tolerate wander differently.
2. Q held fixed when coils are scaled (conservative for big coils).
3. Wander assumed normal; no Indian intercity measurement found.
4. No Indian DWPT cost published; Chinese component costs are the base, US costs the upper bound.
5. One hourly traffic profile for all classes (night-heavy truck profile as sensitivity); speeds are speed limits.
6. Hourly steps average out second-by-second power swings (inverters and firm power are sized separately).
7. EV tariff and its eligibility for the solar-hours rebate should be confirmed against the full MERC order.
