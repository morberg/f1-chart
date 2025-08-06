# Makefile for f1-chart project

.PHONY: test coverage chart pytest pytest-coverage

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

# Force update season cache and generate chart (usage: make chart-update YEAR=2025, or just make chart-update for current year)
chart-update:
	uv run python main.py --year $(or $(YEAR),$(shell date +%Y)) --force-update

# Add new races to cache without replacing existing ones (usage: make chart-add-races YEAR=2025, or just make chart-add-races for current year)
chart-add-races:
	uv run python main.py --year $(or $(YEAR),$(shell date +%Y)) --update-cache

pytest-coverage:
	pytest --cov=main --cov-report=term-missing test_main_pytest.py

pytest:
	pytest test_main_pytest.py
