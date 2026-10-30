# megasonic_etch: megasonic-assisted TMAH etching of poly-Si in high-aspect-ratio slits

Model for Project 1 of the UA proposal *Megasonics for Improved Wet Processing of Materials in High Aspect
Ratio Structures*: 5 wt% TMAH at 60 °C etching the poly-Si layers of an alternating SiO₂/poly-Si stack
along a 100 nm × 10 µm slit, with a 1–3 MHz megasonic field in a single-wafer spin tool.

- `docs/formulation.md`: every equation, property and assumption, with sources and the second check of each
- `etchsim/props.py`: conditions and properties (ASSUMED values marked)
- `etchsim/acoustics.py`: megasonic field at the wafer and in the slit (reflection from Si, Stokes layer, decay)
- `etchsim/slit1d.py`: quasi-steady 1D Nernst–Planck (diffusion + electromigration) + sidewall reaction
- `etchsim/pocket.py`: lateral recess pockets, H₂ bubble criterion
- `run_1d.py`: reference study, writes `results_1d/` (profiles.png, megasonic_effect.png, summary.csv)
- `run_evolution.py`: recess growth over 2 min, H₂ bubble-blocking scenarios, acoustic vs Laplace pressure
- `tests/test_formulas.py`: independent checks (20)

```bash
uv run --no-project --with numpy --with scipy --with matplotlib python run_1d.py
uv run --no-project --with pytest --with numpy --with scipy pytest -q
```

Stage 2 (planned): 2D Fluent 2024R1 model with UDFs for the slit mouth, the oscillating flow and the
recess pockets, checked against the 1D model.
