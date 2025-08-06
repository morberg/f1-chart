# F1 Standings Chart Generator

## About (manual edit)

Vibe coded with GitHub Copilot and GPT-4.1. This is the only section I've
written myself in the repo, the rest has been generated.

[f1_standings.html](https://htmlpreview.github.io/?https://github.com/morberg/f1-chart/blob/main/f1_standings.html)
in this repo is an example of what the year 2023 looks like.

Five minutes after checking in this code I found out about [Formula 1
points](https://www.formula1points.com/) which does all of this and much more in
a more appealing way. Oh well. I had fun doing this at least.

## About

This Python program fetches Formula 1 race data from [openf1.org](https://openf1.org), generates a chart of driver standings after each race for a given season, and displays driver names with country flags. The chart is interactive, visually appealing, and exportable as a standalone HTML file for easy sharing.

## Features

- Fetches F1 race sessions and results for any season year
- Robust local caching for all API data (season, race results, driver names)
- Displays driver names (not just numbers) and country flags
- Legend sorted by current (final) standings
- High-contrast, modern, and legible chart using Plotly Express
- Export chart as standalone HTML (`f1_standings.html`)
- Command-line options for year selection and cache control

## Usage

### 1. Install dependencies with [uv](https://github.com/astral-sh/uv)

If you don't have `uv` installed:

```sh
pipx install uv
```

Then install all dependencies:

```sh
uv sync
```

### 2. Run the program

```sh
uv run main.py --year 2025
```
- Replace `2025` with any season year you want to chart.
- If you omit `--year`, it defaults to the current year (2025).

### 3. Force update all cached data (complete refresh)

```sh
uv run main.py --year 2025 --force-update
```

### 4. Add new races to cache (incremental update)

```sh
uv run main.py --year 2025 --update-cache
```
- This adds new races to the existing cache without replacing cached data
- More efficient for ongoing seasons where you want to add new races as they become available

### 5. View the chart

Open `f1_standings.html` in your browser.

## Caching

- All API data is cached in the `.cache` directory for efficiency and offline use.
- Use `--force-update` to refresh the season cache completely (replaces all cached data).
- Use `--update-cache` to add new races to existing cache without replacing cached data (more efficient for ongoing seasons).

## Customization

- The code is in `main.py` and is easy to modify for further customization (e.g., cache expiry, more chart options).

## Development & Automation

This project includes a `Makefile` for common tasks:

- **Run all tests:**
  ```sh
  make test
  ```
- **Check code coverage:**
  ```sh
  make coverage
  ```
- **Generate the chart for the current year:**
  ```sh
  make chart
  ```
- **Generate the chart for a specific year:**
  ```sh
  make chart-year YEAR=2025
  ```
- **Force update season cache and generate chart:**
  ```sh
  make chart-update YEAR=2025
  ```
- **Add new races to cache and generate chart (incremental):**
  ```sh
  make chart-add-races YEAR=2025
  ```
- **Run pytest tests:**
  ```sh
  make pytest
  ```
- **Run pytest with coverage:**
  ```sh
  make pytest-coverage
  ```

## .gitignore

The repository includes a `.gitignore` that excludes Python cache files, build artifacts, the `.cache` directory, coverage files, and virtual environments:

```
__pycache__/
*.py[oc]
build/
dist/
wheels/
*.egg-info
.cache/
.coverage
.venv
```

## License

MIT
