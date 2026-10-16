# Validation of the coupler model

`run_study1.py` reproduces the blind validation of the coil model (`wpt_model.py`) against the published
measurements of Ibrahim & Mohammed, *Batteries* 11(7):257, 2025 (400 mm coreless circular coupler, 85 kHz):

| Data set | Points | Mean absolute error | Notes |
|---|---|---|---|
| Coupling vs. distance (aligned), Fig. 17 of the source | 14 | 3.2 % | R^2 = 0.9991 |
| Coupling vs. lateral offset at 100 mm, Fig. 20 | 13 | 3.3 % | maximum 9.7 % at 130 mm |
| Tabulated M and k at 131 mm, Table 3 | 1 | 4.4 % | |

No parameter is fitted to coupling data: turn pitches are fitted to the measured self-inductances only.

- `data/` - the measured and FEM coupling values, read from the vector graphics of the source PDF
  (`tools/extract_curves.py` shows how).
- `METHODS.md` - every step, input and source.

Run from this folder:  `python run_study1.py`  (writes `figures/` and `results/` here).
