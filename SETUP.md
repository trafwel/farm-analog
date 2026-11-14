# farm-analog: Development Setup

How to get a working Python environment for the farm-analog project (NASA Space Apps 2026, *Field Shift: Adapting Farms with NASA Data*). Every teammate does steps 1–6 once.

We use **conda-forge through Miniforge** because it installs geospatial libraries (GDAL, rasterio, GeoPandas) cleanly on Mac, Windows and Linux.

---

## 1. Clone the repo

```bash
git clone https://github.com/trafwel/farm-analog.git
cd farm-analog
```

## 2. Install Miniforge (once per computer)

**macOS**

```bash
brew install miniforge
conda init zsh
```

Restart your terminal afterwards.

**Windows / Linux:** download the installer from <https://github.com/conda-forge/miniforge> and run it, then restart your terminal.

## 3. Create the environment

```bash
conda env create -f environment.yml
conda activate farm-analog
```

Make the environment available in Jupyter:

```bash
python -m ipykernel install --user --name farm-analog
```

## 4. Set up your secrets

Copy the template and fill in your own values:

```bash
cp .env.example .env
```

| Variable | What it is | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Key for the LLM assistant (Claude) | console.anthropic.com → API Keys |
| `EE_PROJECT` | The team's Google Cloud project ID with Earth Engine enabled | Ask the team lead |

`.env` is gitignored. **Never put keys in code or notebooks.** If a key is ever committed by accident, revoke it immediately and make a new one.

## 5. Log in to Earth Engine (once per person)

You need access to the team's Google Cloud project with Earth Engine enabled (noncommercial use).

```bash
earthengine authenticate
```

Then initialize in code:

```python
import os
import ee
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.environ["EE_PROJECT"])
```

## 6. Check that everything works

```bash
python -c "import xarray, rasterio, geopandas, xclim, sklearn, ee, pydantic, farm_analog; print('ok')"
```

You should see `ok`. Then run the lint and tests, the same checks CI runs on every pull request:

```bash
ruff check . && pytest
```

---

## Project layout

```
farm-analog/
├── environment.yml      # the shared environment (edit this to add packages)
├── .env.example         # secrets template (copy to .env)
├── SETUP.md             # this file
├── README.md            # project overview
├── notebooks/           # exploration: analog tests, Earth Engine exports
├── src/farm_analog/    # reusable code: analogs.py, indicators.py, data.py
├── app/                 # Streamlit app: app.py
└── data/                # local data only, gitignored
```

---

## Day-to-day workflow

### Adding a package

1. Add it to `environment.yml` (under `dependencies`, or under `pip:` if it isn't on conda-forge).
2. Update your environment and commit the file:

```bash
conda env update -f environment.yml --prune
git add environment.yml
git commit -m "Add <package>"
```

3. Tell the team. Everyone else runs:

```bash
conda env update -f environment.yml --prune
```

### Branches and pull requests

- One branch per workstream: `data`, `analog`, `app`, `story`.
- Merge into `main` through pull requests only; `main` is protected.
- Pull often to avoid big merge conflicts:

```bash
git pull origin main
```

### Data

- **Never commit data files** (`.tif`, `.nc`, `.parquet` are gitignored).
- Earth Engine exports go to the team's shared **Google Drive folder or Cloud Storage bucket**.
- Write the download location of each dataset in `README.md` so anyone can reproduce `data/`.

---

## Reference files

If any of these are missing from the repo, create them with the contents below.

### `environment.yml`

The real file is [`environment.yml`](environment.yml) in the repo root. It isn't copied here so the two can't drift apart.

### `.env.example`

```
ANTHROPIC_API_KEY=
EE_PROJECT=
```

### Additions to `.gitignore`

Add these below GitHub's standard Python template:

```gitignore
# secrets
.env

# data: never commit rasters or large exports
data/
*.tif
*.nc
*.parquet

# notebooks
.ipynb_checkpoints/
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `conda: command not found` | Run `conda init zsh` (or `conda init bash`), then restart the terminal |
| Environment creation is very slow | Make sure you installed **Miniforge** (it uses the fast solver and conda-forge by default) |
| `ee.Initialize` fails with a project error | Check `EE_PROJECT` in `.env` and that the project has Earth Engine enabled and you have access |
| `ModuleNotFoundError` after pulling | Someone added a package: run `conda env update -f environment.yml --prune` |
| Jupyter can't find packages | Pick the **farm-analog** kernel in Jupyter (step 3) |
| `anthropic` authentication error | Check `ANTHROPIC_API_KEY` in `.env` and that `load_dotenv()` runs before creating the client |

---

## Optional extras

- **GitHub Codespaces:** add `.devcontainer/devcontainer.json` that installs conda and runs `conda env create -f environment.yml` on start, so anyone can code in the browser without local setup.
- **CI check:** a GitHub Actions workflow using `mamba-org/setup-micromamba` with `environment-file: environment.yml` that runs the import check from step 6 on every pull request.
