import requests
import pandas as pd
import plotly.express as px
import pycountry
import argparse
from datetime import datetime
import os
import json
import time

OPENF1_API_BASE = "https://api.openf1.org/v1"

# Cache file patterns
DRIVER_CACHE_FILE = "driver_name_cache.json"
SEASON_CACHE_PATTERN = "season_{year}_races.json"
RACE_RESULT_CACHE_PATTERN = "race_result_{session_key}.json"

CACHE_DIR = ".cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def load_cache(filename):
    path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def save_cache(filename, data):
    path = os.path.join(CACHE_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f)


def get_races(year, force_update=False, update_cache=False, max_retries=3):
    cache_file = SEASON_CACHE_PATTERN.format(year=year)
    sessions = None
    existing_sessions = None
    
    if force_update:
        # Force update: ignore existing cache completely
        sessions = None
    elif update_cache:
        # Update cache: load existing cache and merge with new data
        existing_sessions = load_cache(cache_file)
        if existing_sessions:
            print(f"Found {len(existing_sessions)} races in cache, checking for new races...")
    else:
        # Normal mode: use cache if available
        sessions = load_cache(cache_file)
    
    if sessions is None or update_cache:
        url = f"{OPENF1_API_BASE}/sessions?year={year}&session_name=Race"
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                new_sessions = resp.json()
                
                if update_cache and existing_sessions:
                    # Merge new sessions with existing ones
                    existing_keys = {s.get("session_key") for s in existing_sessions}
                    new_races = [s for s in new_sessions if s.get("session_key") not in existing_keys]
                    if new_races:
                        print(f"Found {len(new_races)} new races to add to cache")
                        sessions = existing_sessions + new_races
                    else:
                        print("No new races found")
                        sessions = existing_sessions
                else:
                    sessions = new_sessions
                
                save_cache(cache_file, sessions)
                break
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
            ) as e:
                print(f"API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to fetch races after {max_retries} attempts")
                    if update_cache and existing_sessions:
                        print("Using existing cached data")
                        sessions = existing_sessions
                    else:
                        raise
    filtered_sessions = [s for s in sessions if "date_start" in s]
    if len(filtered_sessions) != len(sessions):
        print(
            f"Warning: {len(sessions) - len(filtered_sessions)} sessions missing 'date_start' key. Example: {sessions[:2]}"
        )
    sessions = sorted(filtered_sessions, key=lambda x: x["date_start"])
    return sessions


def get_race_results(session_key, max_retries=3):
    cache_file = RACE_RESULT_CACHE_PATTERN.format(session_key=session_key)
    data = load_cache(cache_file)
    if data is not None:
        return data
    url = f"{OPENF1_API_BASE}/session_result?session_key={session_key}"
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            save_cache(cache_file, data)
            return data
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
        ) as e:
            print(
                f"API request failed for session {session_key} (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(
                    f"Failed to fetch race results for session {session_key} after {max_retries} attempts"
                )
                return []  # Return empty list instead of raising exception


def get_driver_map(driver_session_pairs, max_retries=5):
    cache = load_cache(DRIVER_CACHE_FILE) or {}
    driver_map = {}
    updated = False
    for driver_number, session_key in driver_session_pairs:
        key = f"{driver_number}:{session_key}"
        if key in cache:
            name = cache[key]
        else:
            url = f"{OPENF1_API_BASE}/drivers?driver_number={driver_number}&session_key={session_key}"
            print(f"Getting driver {driver_number} in session {session_key}")
            success = False
            for attempt in range(max_retries):
                try:
                    resp = requests.get(url, timeout=30)
                    if resp.status_code == 429:
                        wait = 2**attempt
                        print(
                            f"- Rate limited (429). Waiting {wait}s before retrying..."
                        )
                        time.sleep(wait)
                        continue
                    resp.raise_for_status()
                    success = True
                    break
                except (
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.HTTPError,
                ) as e:
                    print(f"- Request error (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt
                        print(f"- Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(
                            f"- Failed after {max_retries} attempts, using driver number as fallback"
                        )

            if success:
                data = resp.json()
                if data:
                    d = data[0]
                    name = (
                        d.get("full_name")
                        or d.get("broadcast_name")
                        or str(driver_number)
                    )
                else:
                    name = str(driver_number)
            else:
                # Fallback when all attempts failed
                name = str(driver_number)

            cache[key] = name
            updated = True
        driver_map[(str(driver_number), str(session_key))] = name
    if updated:
        save_cache(DRIVER_CACHE_FILE, cache)
    return driver_map


# Helper to get flag emoji from country code
def country_code_to_flag(code):
    if not code:
        return ""
    code = code.upper()
    # Manual overrides for non-standard codes
    manual_map = {
        "KSA": "SA",  # Saudi Arabia
        "MON": "MC",  # Monaco
        "UAE": "AE",  # United Arab Emirates
        "RUS": "RU",  # Russia (sometimes used as non-standard)
        "KOR": "KR",  # South Korea
        "USA": "US",  # United States
        "GBR": "GB",  # United Kingdom
        "GER": "DE",  # Germany
        "NED": "NL",  # Netherlands
        "SUI": "CH",  # Switzerland
        # Add more as needed
    }
    if code in manual_map:
        code = manual_map[code]
    if len(code) == 2 and code.isalpha():
        return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)
    # Try to convert 3-letter code to 2-letter code
    if len(code) == 3 and code.isalpha():
        try:
            country = pycountry.countries.get(alpha_3=code)
            if country and hasattr(country, "alpha_2"):
                code2 = country.alpha_2
                return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code2)
        except Exception as e:
            print(e)
            pass
    return ""


def season_to_chart(cli_year=None):
    if cli_year is not None:
        return cli_year
    year = datetime.now().year
    return year


def calculate_standings(races, driver_map):
    driver_points = {}
    standings_progression = []
    for race in races:
        print(f"Fetching results for race: {race}")  # Debug: print race info
        results = get_race_results(race["session_key"])
        print(f"Results: {results}")  # Debug: print race results
        # Sort by finishing position, treating None as a large number
        results = sorted(
            results,
            key=lambda x: x["position"] if isinstance(x.get("position"), int) else 9999,
        )
        for result in results:
            driver_num = result.get("driver_number", "Unknown")
            name = driver_map.get(str(driver_num), str(driver_num))  # Use map
            driver_points.setdefault(name, 0)
            # Use API-provided points if available, else fallback to 0
            points = result.get("points", 0)
            driver_points[name] += points
        # Save a snapshot after this race
        standings_progression.append(driver_points.copy())

    def get_race_name(r):
        return (
            r.get("meeting_name")
            or r.get("location")
            or r.get("circuit_short_name")
            or r.get("date_start", "Unknown")
        )

    print(f"Driver names: {list(driver_points.keys())}")  # Debug: print driver names
    return (
        standings_progression,
        [get_race_name(r) for r in races],
        list(driver_points.keys()),
    )


def plot_standings(standings_progression, race_names, driver_names):
    df = pd.DataFrame(standings_progression, columns=driver_names)
    df = df.ffill().fillna(0)
    df["Race"] = race_names
    df_melted = df.melt(id_vars=["Race"], var_name="Driver", value_name="Points")
    fig = px.line(
        df_melted,
        x="Race",
        y="Points",
        color="Driver",
        markers=True,
        title="F1 Driver Standings Progression",
        labels={"Points": "Points", "Race": "Race"},
        color_discrete_sequence=px.colors.qualitative.Dark24,
    )
    fig.update_layout(
        legend_title_text="Driver",
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01),
        margin=dict(l=40, r=40, t=60, b=40),
        width=1100,
        height=700,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Arial", size=14, color="#222"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#e5e5ef")
    fig.write_html("f1_standings.html")


def main():
    parser = argparse.ArgumentParser(description="F1 Standings Chart Generator")
    parser.add_argument(
        "--year", type=int, help="Year of the F1 season to chart (e.g. 2024)"
    )
    parser.add_argument(
        "--force-update", action="store_true", help="Force update season cache from API"
    )
    parser.add_argument(
        "--update-cache", action="store_true", help="Add new races to cache without replacing existing ones"
    )
    args = parser.parse_args()
    year = season_to_chart(args.year)
    print(f"Fetching F1 {year} season data...")
    races = get_races(year, force_update=args.force_update, update_cache=args.update_cache)
    if not races:
        print("No races found for this season.")
        return
    # Gather all (driver_number, session_key) pairs from all race results
    driver_session_pairs = set()
    all_race_results = []
    for race in races:
        results = get_race_results(race["session_key"])
        if results:  # Only include races with results
            all_race_results.append((race, results))
            for result in results:
                driver_num = result.get("driver_number")
                if driver_num is not None:
                    driver_session_pairs.add((driver_num, race["session_key"]))
        else:
            print(
                f"Skipping race {race.get('meeting_name', 'Unknown')} - no results available"
            )

    if not all_race_results:
        print("No race results available for this season.")
        return
    # Fetch driver map using the correct endpoint
    driver_map_full = get_driver_map(driver_session_pairs)
    # Build a mapping from driver_number to the most recent name (for charting)
    driver_number_to_name = {}
    for (driver_num, session_key), name in driver_map_full.items():
        driver_number_to_name[str(driver_num)] = name

    # Now recalculate standings using the correct names
    def calculate_standings_with_names(races, all_race_results, driver_number_to_name):
        points_table = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
        driver_points = {}
        standings_progression = []
        for race, results in all_race_results:
            # Sort by finishing position, treating None as a large number
            results = sorted(
                results,
                key=lambda x: x["position"]
                if isinstance(x.get("position"), int)
                else 9999,
            )
            for i, result in enumerate(results):
                if i < len(points_table):
                    points = points_table[i]
                else:
                    points = 0
                driver_num = result.get("driver_number", "Unknown")
                name = driver_number_to_name.get(str(driver_num), str(driver_num))
                driver_points.setdefault(name, 0)
                driver_points[name] += points
            standings_progression.append(driver_points.copy())

        def get_race_name(r):
            # Try to get country code for flag
            country_code = r.get("country_code") or r.get("country_alpha2")
            flag = country_code_to_flag(country_code) if country_code else ""
            base = (
                r.get("meeting_name")
                or r.get("location")
                or r.get("circuit_short_name")
                or r.get("date_start", "Unknown")
            )
            return f"{flag} {base}" if flag else f"{country_code}: {base}"

        # Sort driver_names by final points (descending) before passing to plot_standings
        if standings_progression:
            final_points = standings_progression[-1]
            sorted_driver_names = sorted(
                final_points, key=lambda n: final_points[n], reverse=True
            )
        else:
            sorted_driver_names = list(driver_points.keys())
        return (
            standings_progression,
            [get_race_name(race) for (race, _) in all_race_results],
            sorted_driver_names,
        )

    standings_progression, race_names, driver_names = calculate_standings_with_names(
        races, all_race_results, driver_number_to_name
    )
    plot_standings(standings_progression, race_names, driver_names)


if __name__ == "__main__":
    main()
