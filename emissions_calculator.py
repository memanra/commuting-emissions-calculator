"""
Commuting Emissions Calculator
================================
Calculates CO2 emissions from employee commuting using Google Maps Distance Matrix API.
Supports car, public transit, and bicycle modes.

Author: Rafael Mesa-Manzano, PhD
Research background: Urban decarbonisation & teleworking emissions analysis
"""

import os
import time
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# ── Emission factors (gCO2/km) ────────────────────────────────────────────────
# Sources: European Environment Agency (EEA) 2023, Spanish DGT vehicle fleet data
EMISSION_FACTORS = {
    "car": {
        "mean": 158.0,   # gCO2/km — average Spanish passenger car fleet
        "std":   32.0,   # standard deviation across vehicle classes
    },
    "transit": {
        "mean":  68.0,   # gCO2/km per passenger (urban bus + metro mix)
        "std":   12.0,
    },
    "bicycle": {
        "mean":   0.0,
        "std":    0.0,
    },
}

WORKING_DAYS_PER_YEAR = 220
WEEKS_PER_YEAR = 44  # working weeks


def get_distance_matrix(origins: list[str], destination: str, api_key: str, mode: str = "driving") -> dict:
    """
    Call Google Maps Distance Matrix API for a list of origins.
    mode: 'driving' | 'transit' | 'bicycling'
    Returns raw API response dict.
    """
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": "|".join(origins),
        "destinations": destination,
        "mode": mode,
        "units": "metric",
        "key": api_key,
    }
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def parse_distance_matrix(api_response: dict, employee_ids: list[str]) -> pd.DataFrame:
    """Extract distance (km) and duration (min) from API response into a DataFrame."""
    rows = []
    for i, row in enumerate(api_response.get("rows", [])):
        element = row["elements"][0]
        if element["status"] == "OK":
            distance_km = element["distance"]["value"] / 1000
            duration_min = element["duration"]["value"] / 60
        else:
            distance_km = None
            duration_min = None
        rows.append({
            "employee_id": employee_ids[i],
            "distance_km": distance_km,
            "duration_min": duration_min,
            "api_status": element["status"],
        })
    return pd.DataFrame(rows)


def calculate_emissions(df: pd.DataFrame, n_simulations: int = 1000, seed: int = 42) -> pd.DataFrame:
    """
    Estimate weekly and annual CO2 emissions per employee using Monte Carlo simulation
    over emission factor uncertainty.

    Returns df with added columns:
        co2_weekly_mean_g, co2_weekly_p5_g, co2_weekly_p95_g,
        co2_annual_kg_mean, savings_1day_g, savings_2days_g
    """
    rng = np.random.default_rng(seed)
    results = []

    for _, row in df.iterrows():
        mode = row["transport_mode"]
        dist = row["distance_km"]
        telework = row["telework_days_per_week"]

        if pd.isna(dist) or mode not in EMISSION_FACTORS:
            results.append({
                "co2_weekly_mean_g": None,
                "co2_weekly_p5_g": None,
                "co2_weekly_p95_g": None,
                "co2_annual_kg_mean": None,
                "savings_1day_g": None,
                "savings_2days_g": None,
            })
            continue

        ef = EMISSION_FACTORS[mode]
        # Monte Carlo over emission factor
        ef_samples = rng.normal(ef["mean"], ef["std"], n_simulations)
        ef_samples = np.clip(ef_samples, 0, None)

        # Round trip × office days per week
        office_days = 5 - telework
        weekly_km = dist * 2 * office_days  # round trip
        weekly_co2 = ef_samples * weekly_km  # gCO2

        # Savings if teleworking 1 or 2 more days
        savings_1day = ef_samples * dist * 2 * 1
        savings_2days = ef_samples * dist * 2 * 2

        results.append({
            "co2_weekly_mean_g": weekly_co2.mean(),
            "co2_weekly_p5_g": np.percentile(weekly_co2, 5),
            "co2_weekly_p95_g": np.percentile(weekly_co2, 95),
            "co2_annual_kg_mean": weekly_co2.mean() * WEEKS_PER_YEAR / 1000,
            "savings_1day_g": savings_1day.mean(),
            "savings_2days_g": savings_2days.mean(),
        })

    return pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)


def classify_commute(distance_km: float) -> str:
    """Classify commute as short / medium / long based on tercile thresholds."""
    if pd.isna(distance_km):
        return "unknown"
    if distance_km <= 6.0:
        return "short"
    elif distance_km <= 14.3:
        return "medium"
    else:
        return "long"


def run_pipeline(
    input_csv: str,
    workplace_address: str,
    api_key: str,
    output_csv: str = "results/commuting_emissions.csv",
    batch_size: int = 25,
) -> pd.DataFrame:
    """
    Full pipeline:
    1. Load employee CSV
    2. Call Google Maps Distance Matrix API (batched)
    3. Calculate emissions with Monte Carlo
    4. Save results

    Args:
        input_csv: Path to employee CSV (see data/employees_sample.csv)
        workplace_address: Full address of the workplace
        api_key: Google Maps API key
        output_csv: Where to save results
        batch_size: Max origins per API call (Google limit = 25)
    """
    print(f"[{datetime.now():%H:%M:%S}] Loading employee data...")
    employees = pd.read_csv(input_csv)
    print(f"  → {len(employees)} employees loaded")

    # ── Step 1: Get distances from Google Maps ────────────────────────────────
    print(f"[{datetime.now():%H:%M:%S}] Fetching distances from Google Maps API...")
    distance_rows = []

    for i in range(0, len(employees), batch_size):
        batch = employees.iloc[i : i + batch_size]
        origins = batch["home_address"].tolist()
        emp_ids = batch["employee_id"].tolist()

        # Use driving for car employees, transit otherwise
        # Simplified: use driving for all (distance), mode affects emission factor
        api_resp = get_distance_matrix(origins, workplace_address, api_key, mode="driving")
        batch_df = parse_distance_matrix(api_resp, emp_ids)
        distance_rows.append(batch_df)

        if i + batch_size < len(employees):
            time.sleep(0.5)  # Respect API rate limits

    distances = pd.concat(distance_rows, ignore_index=True)

    # ── Step 2: Merge with employee data ──────────────────────────────────────
    merged = employees.merge(distances, on="employee_id", how="left")
    merged["commute_type"] = merged["distance_km"].apply(classify_commute)

    # ── Step 3: Calculate emissions ───────────────────────────────────────────
    print(f"[{datetime.now():%H:%M:%S}] Running Monte Carlo emission estimates...")
    results = calculate_emissions(merged)

    # ── Step 4: Summary stats ─────────────────────────────────────────────────
    print("\n── SUMMARY ──────────────────────────────────────────────────────")
    summary = results.groupby("commute_type").agg(
        n_employees=("employee_id", "count"),
        avg_distance_km=("distance_km", "mean"),
        avg_weekly_co2_g=("co2_weekly_mean_g", "mean"),
        avg_annual_co2_kg=("co2_annual_kg_mean", "mean"),
        avg_savings_1day_g=("savings_1day_g", "mean"),
    ).round(1)
    print(summary.to_string())

    total_annual = results["co2_annual_kg_mean"].sum()
    print(f"\nTotal fleet annual emissions: {total_annual:.1f} kg CO2")
    print(f"Equivalent to {total_annual/1000:.2f} tonnes CO2")

    # ── Step 5: Save ──────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    results.to_csv(output_csv, index=False)
    print(f"\n[{datetime.now():%H:%M:%S}] Results saved to {output_csv}")

    return results


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Commuting Emissions Calculator")
    parser.add_argument("--input", default="data/employees_sample.csv", help="Employee CSV path")
    parser.add_argument("--workplace", required=True, help="Workplace address")
    parser.add_argument("--api-key", default=os.environ.get("GOOGLE_MAPS_API_KEY"), help="Google Maps API key")
    parser.add_argument("--output", default="results/commuting_emissions.csv", help="Output CSV path")
    args = parser.parse_args()

    if not args.api_key:
        raise ValueError("Google Maps API key required. Set GOOGLE_MAPS_API_KEY env var or use --api-key")

    run_pipeline(
        input_csv=args.input,
        workplace_address=args.workplace,
        api_key=args.api_key,
        output_csv=args.output,
    )
