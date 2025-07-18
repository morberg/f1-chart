# Makefile for f1-chart project

.PHONY: test coverage chart

# Run all unit tests

test:
	uv run python -m unittest test_main.py

# Run tests and show coverage report
coverage:
	uv run coverage run -m unittest test_main.py && uv run coverage report -m

# Generate the F1 standings chart (default: current year)
chart:
	uv run python main.py

# Generate chart for a specific year (usage: make chart YEAR=2025)
chart-year:
	uv run python main.py --year $(YEAR)

# Force update season cache and generate chart (usage: make chart-update YEAR=2025)
chart-update:
	uv run python main.py --year $(YEAR) --force-update
