# Related work and what is new (literature check, Oct 2026)

## Closest prior work and what each one does NOT do

| Work | What it does | Gap relative to this work |
|---|---|---|
| Ghose, Qin, Sivaranjani, "Traffic-Aware Microgrid Planning for DWC Roadways", arXiv 2511.00941 (Nov 2025) | Cell-transmission traffic model → DWC demand → AC-OPF microgrid sizing (PV, storage, grid coupling); I-210W California; heavy trucks only, all assumed electric | No coil physics (demand = road-load equation; no coupling, pitch, misalignment); no road infrastructure loads; no partial EV/receiver adoption; no mixed traffic; no harvesting |
| Lewis, Gong, Erhardt, ..., Onar, Ozpineci, Ionel, "Sizing Considerations for EV DWC Systems with Integrated Energy Storage", IEEE ITEC 2022 (UKY/ORNL) | Kentucky I-75 traffic counts; coil segmentation rules; BESS sizing from traffic redistribution | Coil efficiency fixed at 90%; coil spacing not co-optimised with storage (stated by the authors as possible future work); no PV, no road loads |
| Agnihotri & Chaurasia, "Electric Road Systems for Smart Cities", arXiv 2512.12638 | SUMO + MATLAB framework, Delhi Outer Ring Road case; solar share claimed 60-70% | Efficiency effectively fixed (88-91%); no PV or storage sizing model; no k/gap/misalignment equations; no road lighting loads |
| Nguyen & Bui, JMST 84 (2025); CEC-500-2023-036 (2023) | Piezo pavement for distributed loads | Piezo only; no WPT; no proof that harvest is energy-neutral for vehicles |

## What this work contributes

1. A physics-to-planning chain: validated coupler model (3.2 % mean error against
   measurements) → row-averaged power and efficiency vs coil pitch, gap, coil scale and the statistical
   lane-wander of real traffic → hourly corridor demand → co-optimised sizing of PV, storage and grid.
2. Structural finding: with threshold-switched segments, lateral misalignment appears as a loss of
   delivered power (utilisation), not as a loss of efficiency. First run: 400 mm coils, 150 mm gap,
   0.4 m pitch: aligned p̄ = 75.6 %, eta = 96.4 %; with 254 mm wander s.d., p̄ = 34.0 %, eta = 95.5 %.
   Fixed-efficiency system models therefore mis-size the rated power and electrified length, not the
   energy bill. (To be quantified as a bias on cost.)
3. Joint design of coil layout (pitch, switch-on threshold, coil scale) with the energy system, instead
   of sizing them separately as in prior work.
4. India-specific case: real daily class-wise counts (MSRDC, Somatne Phata toll plaza, NH-48),
   heterogeneous traffic with partial receiver adoption, road infrastructure loads (lighting, toll plaza,
   ATMS) served from the same PV + storage.
5. Energy-honest treatment of harvesting: included only at forced-deceleration zones, with an explicit
   energy balance proving it does not raise vehicle consumption elsewhere; contrasted with the authors' companion study.

## Novelty status
No paper found that co-optimises coil layout with corridor PV/storage/grid, or that propagates
measured-validated coupling physics and lane-wander statistics into energy-system planning.
Searches run: arXiv, IEEE, MDPI, ORNL, UKY, DOAJ, CEC, patents (USPTO) on DWPT detection/control.

