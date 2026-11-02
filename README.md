# megasonic_etch: megasonic-assisted TMAH etching of poly-Si in high-aspect-ratio slits

Model for Project 1 of the UA proposal *Megasonics for Improved Wet Processing of Materials in High Aspect
Ratio Structures*. After the 100:1 dry etch, 5 wt% TMAH at 60 °C recesses the poly-Si layers of an alternating
SiO₂/poly-Si stack (50/50 nm) along a 100 nm × 10 µm slit; SiO₂ stays. Single-wafer spin tool with a MegPie
megasonic transducer, 1–3 MHz, 0.5–2 W/cm². Transport: diffusion + electromigration (Nernst–Planck, zero
current, electroneutral) of OH⁻, silicate and dissolved H₂. Every formula, source and assumption:
[docs/formulation.md](docs/formulation.md).

| Part | Files | What |
|---|---|---|
| 1D reference | `etchsim/`, `run_1d.py`, `run_evolution.py` | fast, checked twice; recess growth and H₂-bubble scenarios |
| 2D Fluent | `fluent2d/` (mesh, UDF, case plan), `run_case.py`, `cases.csv` | slit mouth, megasonic oscillating flow, angle sweep |
| HPC | `run_case.slurm`, `submit_cases.sh`, `check_runs.sh` | Puma, 4 cores per case |
| Analysis | `analyze_2d.py` | angle_sweep.png, megasonic_mixing.png, frequency_power.png, verification.md |
| Tests | `tests/` | 27 checks (formulas, solver, mesh, UDF algebra vs 1D) |

## Running on Puma (folder ~/project1)

```bash
cd ~ && git clone https://github.com/arjun2022as/megasonic_etch.git project1      # later: cd ~/project1 && git pull
cd ~/project1
# 1. discovery (about 10 min): compiles the UDF and lists Fluent 2024 R1's settings for the UDF hookups
bash submit_cases.sh M0_none --discover
#    then send: tail -40 logs/M0_none_*.out   and   results/M0_none_discover/discover.txt
# 2. smoke test (after the hookups are confirmed)
bash submit_cases.sh A_f1_I2_t45 --setup-only
# 3. everything (16 jobs, 1-10 h each)
bash submit_cases.sh .
bash check_runs.sh
# 4. figures (compute node)
interactive -a krishna -t 00:30:00
cd ~/project1 && source ~/venvs/pyfluent241/bin/activate && python analyze_2d.py && exit
```

Uses the `~/venvs/pyfluent241` environment from `3d_nand`. The UDF is compiled by Fluent on the node.

## Local (no Fluent)

```bash
uv run --no-project --with numpy --with scipy --with matplotlib python run_1d.py
uv run --no-project --with numpy --with scipy --with matplotlib python run_evolution.py
uv run --no-project --with numpy --with scipy --with matplotlib python run_plug.py      # growing H2 plug cycle
uv run --no-project --with numpy --with scipy --with matplotlib python run_sideview.py  # finite bubbles along the trench
uv run --no-project --with numpy --with scipy --with matplotlib python run_nanobubble.py # case 5: sub-plug bubbles
uv run --no-project --with pytest --with numpy --with scipy pytest -q
```
