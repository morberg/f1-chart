# F1 Standings Chart Generator

Vibe coded with GitHub Copilot and GPT-4.1. This is the only line I've written myself in the repo, the rest has been generated.

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

### 3. Force update season cache (fetch latest sessions)

```sh
uv run main.py --year 2025 --force-update
```

### 4. View the chart

Open `f1_standings.html` in your browser.

## Caching

- All API data is cached in the `.cache` directory for efficiency and offline use.
- Use `--force-update` to refresh the season cache if new sessions are added.

## Customization

- The code is in `main.py` and is easy to modify for further customization (e.g., cache expiry, more chart options).

## License

MIT
