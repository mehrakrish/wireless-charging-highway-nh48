# Input data register

Every number used by `src/run_model.py`, its value and its source. The register is kept in the order it was
built: **sections 13, 14 and 15 record later corrections and override earlier rows** (kept for transparency).

Every number used by `src/run_model.py` is listed here with its source. "R" = read directly in the source;
"S" = secondary source quoting the primary; "A" = our assumption (stated and varied in sensitivity).

## 1. Electricity tariff (MSEDCL, Maharashtra), EV charging category

| Item | Value used | Basis | Source |
|---|---|---|---|
| EV charging tariff, HT and LT, FY 2026-27 | Rs 9.50 /kWh (base case) | S | IANS wire, 27 Mar 2026, on MERC Case No. 75 of 2025 (order 25 Mar 2026), https://www.newsgram.com/india/2026/03/27/maha-mahavitaran-tariff-cut-to-benefit-consumers-from-april-1 . Must be checked against Case 75/2025 tables before submission: https://www.mahadiscom.in/wp-content/uploads/2026/07/Tariff-Order_Case-No.-75-of-2025-dated-25th-March-2026.pdf |
| Fixed / demand charge for EV category | none (single-part tariff) | S | MSEDCL press note on MERC MYT order 28 Mar 2025 (Case 217/2024), Sec. 11.5 |
| ToD 00-09 h | 0 % | S | CARE Ratings, "Peak Power Costlier, Solar Cheaper", 28 May 2026 |
| ToD 09-17 h (solar hours) | -15 % Apr-Sep, -25 % Oct-Mar | S | same; EV eligibility not confirmed -> sensitivity case without rebate |
| ToD 17-24 h | +20 % | S | same; MSEDCL press note Mar 2025 p.8 note 3 |
| Tax on sale of electricity | 0.2894 Rs/kWh | R | MSEDCL Commercial Circular 354, 15 Apr 2026 (applicability to EV category unclear; included, conservative) |
| Export to grid | not credited in base case | A | Net metering for non-residential limited (no peak-hour banking); sensitivity only |

## 2. Grid CO2 emission factor (CEA CO2 Baseline Database)

| Item | Value | Basis | Source |
|---|---|---|---|
| Weighted average FY 2025-26 | 0.675 tCO2/MWh (base) | R | CEA User Guide v22.0, Aug 2026, Table S, https://cea.nic.in/api/cdm-report-version/view-pdf/en/82 |
| Combined margin FY 2025-26 | 0.705 tCO2/MWh (displacement of grid power by new PV) | R | same |
| Weighted average FY 2024-25 | 0.710 | R | CEA v21.0, Nov 2025, https://cea.nic.in/api/cdm-report-version/view-pdf/en/78 |
| Weighted average FY 2023-24 | 0.727 | R | CEA v20.0, Dec 2024, https://cea.nic.in/api/cdm-report-version/view-pdf/en/76 |

## 3. Finance

| Item | Value | Basis | Source |
|---|---|---|---|
| Discount rate (post-tax WACC) | 9.21 % | R | CERC order, Petition 06/SM/2025, 9 Jul 2025, paras 10-11, https://www.cercind.gov.in/2025/orders/6-SM-2025.pdf |
| O&M escalation | 5.25 %/yr | R | same, para 36 (used only to justify real-terms analysis; costs kept in real 2026 Rs) |
| Inflation (CPI) FY 2026-27 | 5.2 % | R | RBI MPC resolution 7 Oct 2026 (context only) |

## 4. Solar PV (India)

| Item | Value used | Basis | Source |
|---|---|---|---|
| Capex, ground-mount 3-5 MW | Rs 33,579 /kWp (base); range 29,000-57,100 | R (draft order) | HPERC generic tariff FY2026-27, Pet. 14/2026, 06.01.2026, p.5 (modules 85.37 + BOS 250.42 lakh/MW), https://jmkresearch.com/wp-content/uploads/2026/01/HPERC_GenericTariff_Solar.pdf ; low: UC Berkeley IECC May 2025 (USD 350/kW ~ Rs 2.9 cr/MW); high: CERC Pet. 175/GT/2024 (Rs 5.71 cr/MW) |
| Right-of-way mounting premium (median / barrier / canopy) | +25 % on capex (base), 0-100 % sensitivity | A | no Indian canopy/carport cost found |
| O&M | Rs 549 /kW/yr (base); 1,096 high | R | CERC Pet. 175/GT/2024, 20.03.2025, p.20 ; HPERC FY2026-27 p.6 |
| Degradation | 1.33 %/yr (ground rack c-Si, field mean) | R | NCPRE IIT Bombay + NISE, All-India Survey of PV Module Reliability 2018, exec. summary, https://nise.res.in/upload/All-India-Survey-of-Photovoltaic-Module-Reliability_2018_Report.pdf |
| Life | 25 yr | R | HPERC FY2026-27; CERC 175/GT/2024 |
| Module area | 4.49 m2/kWp (575 W, 2.278 x 1.134 m) | R (derived) | Waaree BiN-08 datasheet |
| Area incl. row spacing, fixed tilt | 11.6 m2/kWdc (US median) | R (derived) | Bolinger & Bolinger, IEEE J. Photovoltaics 2022, LBNL |

## 5. Battery storage (India)

| Item | Value used | Basis | Source |
|---|---|---|---|
| Capex all-inclusive | USD 115 /kWh = Rs 9,775 /kWh at Rs 85/USD (base); USD 140 high | R | IEEFA + JMK, "Viability of standalone BESS tariffs discovered in 2025", 19 May 2026, p.9; UC Berkeley IECC May 2025 Table 2 (114-140) |
| Round-trip efficiency (AC-AC) | 85 % | R | SECI ESS-3 RfS clarifications 27.01.2025 cl. 8.1 (minimum); IECC 2025 |
| O&M | 1.5 % of capex /yr | R | IEEFA-JMK 2026 p.9 |
| Usable depth of discharge | 80 % | R | IEEFA-JMK 2026 p.9 |
| Life | 12 yr | R | 12-yr BESPA tenor; IECC 2025 (standalone 12 yr) |
| Minimum duration (power <= energy/2) | 2 h | A | prices above are for 2-4 h systems |

## 6. DWPT road infrastructure (no Indian cost published; foreign data localised)

| Item | Value | Basis | Source |
|---|---|---|---|
| Purdue/INDOT per lane-mile split | charging system 2.23, power distribution 1.01-1.24, civil 3.08 M USD; total 6.32-6.55 M USD/lane-mile (= 3.93-4.07 M USD/lane-km) | R | FHWA/IN/JTRP-2021/25, Konstantinou, Haddad et al., Jun 2021, Table 1, https://rosap.ntl.bts.gov/view/dot/58272/dot_58272_DS1.pdf |
| China expressway | total 3.60-6.00 M RMB/km; coil 888-2,903 RMB/m; construction 646-1,009 RMB/m (grid excluded) | R | Li, Duan, Xia, Xiong, Energies 15, 6924 (2022), Sec. 3.1, Table A1 |
| UK DynaCoV itemised 100 m pilot | GBP 1.475 M (coils 0.4955 M, power electronics 0.221 M, civils 0.151 M, grid 0.083 M) | R | Cenex DynaCoV WP5 final report, 22 Dec 2021, Table 5 |
| Electreon vendor claim | ~EUR 0.7 M/km coils only | S | Connaissance des Energies, 18 Nov 2020 |
| O&M | 17,500 $/km/yr; life 15-20 yr | R | NRCan CanmetENERGY, MITAB 2021 Table 2 / 2022 Table 1 |
| Localisation method | base = China component costs (closest cost structure to India); high = Purdue US; reported as a range | A | stated in paper |

## 7. Grid connection (India HT)

| Item | Value | Basis | Source |
|---|---|---|---|
| HT connection (development + service line) | Rs 7,500-12,500 /kVA (base 10,000) | R (derived) | DERC Schedule of Charges 2017, p.4 (Rs 75 lakh-1.25 cr/MVA); TGERC draft Feb 2026: Rs 3,500-12,000 /kVA |

## 8. Traffic (NH-48 old Mumbai-Pune highway, Somatne Phata, MSRDC)

| Item | Value used | Basis | Source |
|---|---|---|---|
| Monthly tolled counts by class, Aug 2025 - May 2026 | `msrdc_somatne_monthly.csv` (all row sums verified) | R | MSRDC Monthly Fee Statements NH-48 (files listed in CSV) |
| Jun, Jul (monsoon; files not found) | Aug-2025 daily averages | A | proxy; Jun 2026 daily 1-21 range 14,899-19,879 total consistent |
| Direction | counts = both directions combined; 50/50 split | A (inference) | files do not state direction |
| Untolled local cars (Exemption & Violation) | ~20,000-23,000 /day, excluded from base case (local trips, incomplete records per Note 2) | R | same files, "Non-tollable traffic" table |
| Hourly profile (all classes) | `hourly_profile_katoghan.csv`; peak hour 6.25 % of daily | R | UPEIDA Ganga Expressway traffic study, Table 4.8 (NH-19 Katoghan) |
| Class-specific hourly profiles | not available; same profile for all classes (base), night-heavy truck profile in sensitivity | A | gap |

## 9. Vehicles

| Item | Car | LCV | Bus (12 m) | MAV truck | Basis / source |
|---|---|---|---|---|---|
| Energy use (kWh/km) | 0.130 | 0.138 | 1.0 (0.8-1.2) | 1.1 (0.96-1.40) | Car: Autocar India Nexon EV 45 highway test 18 Nov 2024 (R); LCV: WRI India 2023 Tata Ace EV range spec (proxy); Bus: UITP India Nov 2022 Table 2 (R, urban), Sustainable Bus 2020 (NL 1.15); Truck: Tesla Semi ABF pilot, CCJ 9 Jul 2025 (0.963), PepsiCo electrive 15 Aug 2023 (1.1), IPLT Rhino spec (1.40, proxy) |
| Speed (km/h) | 100 | 80 | 90 | 80 | MoRTH S.O. 1522(E), 6 Apr 2018, limits on 4-lane divided highways (R); lower speeds in sensitivity |
| Receiver air gap (mm) | 150 | 150 | 250 | 250 | SAE J2954 Z1-Z3 100-250 mm (ORNL APEC 2019); heavy-duty: Purdue US-231 203 mm, KAIST OLEV 200 mm |
| Receivers per vehicle | 1 | 1 | 3 | 4 | Electreon truck test 13 Oct 2020: 4 receivers, 100 kW; bus: 3 receivers, 60 kW (R) |
| Rated power per receiver | 25 kW (base) | | | | Electreon 2020 report: ~25 kW per receiver, 85 % (R) |
| Lane wander s.d. (mm) | 250 (200-290) | 250 | 250 | 250 (218-285) | MEPDG default 254 (via Gungor 2018); NCAT Timm & Priest 218; VTI Rv34 235-285; Costa Rica light 281 / heavy 290; within-driver SDLP 196 (Jongen 2017) |
| EV share scenarios (2030, NITI Aayog-RMI 2019) | 30 % | 70 % | 40 % | trucks: 2024 ~0.75 % of sales; 2050 75 % HDT | NITI Aayog & RMI 2019 p.8; NITI-RMI ZET 2022 p.28; NITI Aug 2025 |

## 10. Road infrastructure loads (10 km section around Somatne Phata plaza)

| Item | Value used | Basis | Source |
|---|---|---|---|
| Where lighting is mandated on NH | toll plaza + >=500 m approaches each side, interchanges, urban stretches, underpasses (not full length) | R | MoRTH Manual of Specs & Standards, Six-Laning of NH through PPP (2008), Cl. 2.8 p.10, Cl. 4.9.8 p.28, Cl. 4.23 p.37 |
| Lit length in the section | 1.2 km (plaza + approaches) + 0.6 km (two interchanges) = 1.8 km | A | from the clauses above |
| Luminaire | 180 W LED (23,400 lm) | proxy | Eveready Citylite PC (NHAI) product data |
| Pole spacing / arrangement | 30 m, twin-arm median poles (2 luminaires per pole) -> 67 luminaires/km = 12.0 kW/km | R (rule) + A | IS 1944 Parts I&II Cl. 8.3 (spacing <= 3 x 10 m mounting height for cut-off) |
| Lighting hours | sun below civil twilight (computed from solar position, ~9.9-12.2 h/day in Pune) | R (derived) | sunrisesunsettime.org Pune; computed hourly with pvlib |
| Toll plaza average load | 26 kW average (60 % lighting at night, 40 % constant) | proxy | Surat-Hazira NH-6 Mandal plaza 180 kW PV, 2.26 lakh kWh/yr (Energetica India 5 Jul 2024) -> 619 kWh/day; split 60/20/20 lighting/tolling/HVAC from Teixeira, ISEP 2018 (24 Portuguese plazas) |
| ATMS | 0.10 kW/km (PTZ camera 23 W per km + communications, VIDES and VMS share) | R spacing, proxy power | NHAI/IHMCL ATMS training deck (policy 10 Oct 2023); Trassir PTZ datasheet 23 W; Wang et al. E3S 573 (2024) |

## 11. Braking-zone harvesting (toll plaza)

| Item | Value | Basis | Source |
|---|---|---|---|
| Measured harvester output | 72.4 J per light-vehicle pass per 0.33 m2 module; 52.6 % mean efficiency at 50 km/h | R | Ferreira, PAVENERGY results, IConETech-2020 (UWI), Sec. 3.5 p.136 |
| FASTag lane entry speed | 25-30 km/h | R | NHAI SoP for FASTag users, Sec. 3b |
| Car mass | 1,078 kg fleet average curb | R | Deo & Yang, ICCT WP 2020-13, Table 1 |
| Vehicles physically crossing the plaza | tolled (~16,600/day) + exempt cars (~20,000/day) | R | MSRDC fee statements |
| Modules per lane per direction | 20 (6.6 m2) base; 100 upper case | A | |
| Barrier-free tolling (MLFF) live on NH-48 at Choryasi; 104 plazas planned | removes forced deceleration | R | IBTimes 30 Jul 2026 (Rajya Sabha reply) |

## 12. Benchmarks for the cost of a delivered kWh

| Item | Value | Basis | Source |
|---|---|---|---|
| Public DC fast charging, India | Rs 18-30 /kWh (worked example Rs 24) | S | MeraEV, "EV Charging Cost in India (2026)", 19 Jul 2026, https://www.meraev.com/blog/ev-charging-cost-in-india-full-guide |
| Diesel, Pune | Rs 98.55 /L (16 Oct 2026) | R | Business Today fuel price page, https://www.businesstoday.in/fuel-price/diesel-price-in-pune-today |
| Heavy truck diesel use | 36.0 L/100 km (42 t rigid 10x2) - 53.8 L/100 km (55 t tractor-trailer) | R (simulated, validated <5 %) | Yadav, Narla, Delgado, ICCT White Paper, Jun 2023, Table 2 p.6 |
| Diesel-parity electricity price for an e-truck at 1.1 kWh/km | Rs 32-48 /kWh (energy only; excludes vehicle cost differences) | derived | (0.360-0.538 L/km x 98.55) / 1.1 |

## 13. Changes after the independent review (16 Oct 2026) - these override earlier rows

| Item | Now used | Basis | Source / reason |
|---|---|---|---|
| Discount rate | 5.0 % real (3-7 % sensitivity) | derived | CERC 9.21 % is nominal; deflated by the 4 % CPI target retained to Mar 2031 (Outlook Money, 26 Mar 2026): 1.0921/1.04 - 1 |
| Road coil and civil cost | Li et al. per-metre figures halved (two-way construction -> per lane) | R + A | Li, Duan, Xia, Xiong, Energies 15:6924, Sec. 3 "two-way construction configuration" |
| Per-coil solid-state switch + detection | Rs 5,000 per coil | A | needed (companion paper: relays unsuitable); no published unit cost |
| Power distribution along the road | 1.01/2.23 = 45 % of coil + switch + inverter cost | R ratio | Purdue JTRP-2021/25 Table 1 (distribution vs charging system, medium uptake) |
| Road O&M | CAD 17,500 per route-km/yr -> CAD 8,750 per lane-km x Rs 62/CAD = Rs 5.4 lakh/lane-km/yr | R + A | Qiu, Ribberink, Entchev, MITAB 2021 Table 2 (currency not stated; Canadian authors) |
| Solar O&M | Rs 1,096 /kW/yr | R | HPERC FY2026-27 (same source as capex) |
| Battery O&M | 1.5 % of capex /yr, scales with capex | R | IEEFA-JMK 2026 |
| Battery round-trip efficiency | 85 % | R | SECI ESS-3 clarifications 27 Jan 2025 (minimum, AC-AC); IEEFA model assumes 90 % |
| Battery duration | P_b <= E_b/2 enforced in the LP | A | prices are for 2-4 h systems |
| Firm capacity | grid + battery power >= 99.9th-percentile instantaneous section demand at the busiest hour + road loads | derived | compound-Poisson model (corridor.py) |
| Tariff base case | flat Rs 9.50/kWh + ToSE (ToD only as sensitivity) | R | Newsgram/IANS 27 Mar 2026 confirms Rs 9.50 for EV stations; ToD solar rebate reported for industrial/commercial/domestic only |
| Heavy-vehicle traffic | tolled x exemption factor: LCV 1.335, bus/truck 1.56, MAV 1.55; cars tolled only | R | MSRDC "Exemption & Violation" tables, Oct-2025 and Mar-2026 (two-month means); "Reuse & Exit" added only in sensitivity |
| Category C | "Bus/Truck" (two-axle buses and trucks); modelled at 80 km/h, 3 receivers, 1.0 kWh/km | R label | MSRDC fee statements |
| MAV energy use | 1.40 kWh/km (full-payload Indian proxy; US pilots 0.96-1.1 at partial load) | proxy | WRI India 2023 (IPLT Rhino 5536 range spec) |
| Adoption scenarios | equipped fleet shares low 5/10/10/2, mid 15/30/25/10, high 30/60/50/30 % (car/LCV/bus-truck/MAV) | A | explicit scenarios; NITI-RMI 2019 2030 targets are sales shares (reference only) |
| Solar land | 515 kWp per km (one 2.2 m single-row strip, 4.27 m2/kWp at latitude tilt) | A | none / unlimited in sensitivity |
| Avoided CO2 | combined margin 0.705 tCO2/MWh | R | CEA v22 |
| Wander default | 254 mm | R | NCHRP 1-37A (MEPDG), 2004; measured: Timm & Priest BCRRA 2005 (218 mm); Erlingsson et al. EPAM 2012 |
| Harvest | 72.4 J is the maximum output per light-vehicle pass; applied to light vehicles only (cars incl. exempt, LCVs) | R | Ferreira, IConETech-2020 |
| Diesel-parity band (replaces section 12 last row) | Rs 25-38 /kWh = (0.360-0.538 L/km x Rs 98.55) / 1.4 kWh/km (equally loaded Indian e-truck, WRI India 2023) | derived | ICCT full-payload diesel use; e-truck at full payload |

## 14. Weather (solar resource)

| Item | Value | Basis | Source |
|---|---|---|---|
| Typical year | TMYx 2011-2025, Pune, WMO station 430630 (18.533 N, 73.850 E, 592 m); GHI 1,851 kWh/m2/yr; specific AC yield 1,440 kWh/kWp (before lifetime degradation) | R | climate.onebuilding.org (Lawrie & Crawley), file IND_MH_Pune.430630_TMYx.2011-2025.epw, supplied by the author 17 Oct 2026 |
| Robustness | TMYx 2004-2018 (GHI 2,142), 2007-2021 (1,872), 2009-2023 (1,848) re-run in section W | R | same site |

## 15. Tariff verified against the MERC order (17 Oct 2026) - overrides section 1 and section 13 tariff rows

| Item | Value | Basis | Source |
|---|---|---|---|
| HT IX: HT - Electric Vehicle Charging Station, FY 2026-27 | no fixed/demand charge; energy charge Rs 8.92/kVAh + wheeling Rs 0.81/kVAh = Rs 9.73/kVAh (taken = per kWh, unity power factor) | R | MERC Order, Case No. 75 of 2025, 25 Mar 2026, "Summary of HT Tariff for FY 2026-27", p.100 (EHV-connected: 8.92, no wheeling) |
| Average billing rate, HT IX, FY 2026-27 | Rs 9.50/unit (the figure reported by IANS) | R | same order, Table 11 (category-wise ABR), p.87 |
| ToD | revised slots: 0-9 h 0 %, 9-17 h solar rebate -15 % (Apr-Sep) / -25 % (Oct-Mar), 17-24 h +20 % for "eligible consumer categories"; the order does not list whether EV charging is eligible | R | same order, Table 8, para 18.13 |
| Base case used | flat Rs 9.73 + ToSE Rs 0.29 | | ToD as sensitivity |
