"""
Commuting Emissions Map
=======================
Generates an interactive HTML map visualizing commuting emissions by employee.
Color-codes employees by commute type (short/medium/long) and shows CO2 savings potential.

Requires: folium, pandas, googlemaps
"""

import argparse
import os
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import requests


COMMUTE_COLORS = {
    "short": "#2ecc71",   # green
    "medium": "#f39c12",  # orange
    "long": "#e74c3c",    # red
    "unknown": "#95a1ac", # grey
}

MODE_ICONS = {
    "car": "car",
    "transit": "bus",
    "bicycle": "bicycle",
}


def geocode_address(address: str, api_key: str) -> tuple[float, float] | None:
    """Geocode a single address using Google Maps Geocoding API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}
    resp = requests.get(url, params=params, timeout=10).json()
    if resp["status"] == "OK":
        loc = resp["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None


def build_map(
    results_csv: str,
    workplace_address: str,
    api_key: str,
    output_html: str = "dashboard/emissions_map.html",
) -> None:
    """
    Build an interactive folium map with:
    - Workplace marker
    - Employee markers colored by commute type
    - Popups with CO2 data and savings potential
    - Legend
    """
    df = pd.read_csv(results_csv)

    # Geocode workplace
    print("Geocoding workplace...")
    workplace_coords = geocode_address(workplace_address, api_key)
    if not workplace_coords:
        raise ValueError(f"Could not geocode workplace: {workplace_address}")

    # Base map centered on workplace
    m = folium.Map(location=workplace_coords, zoom_start=12, tiles="CartoDB positron")

    # Workplace marker
    folium.Marker(
        location=workplace_coords,
        popup=folium.Popup(f"<b>Workplace</b><br>{workplace_address}", max_width=200),
        icon=folium.Icon(color="blue", icon="building", prefix="fa"),
        tooltip="Workplace",
    ).add_to(m)

    # Employee cluster
    cluster = MarkerCluster(name="Employees").add_to(m)

    print("Geocoding employee addresses...")
    geocoded = 0
    for _, row in df.iterrows():
        coords = geocode_address(row["home_address"], api_key)
        if not coords:
            continue
        geocoded += 1

        commute = row.get("commute_type", "unknown")
        color = COMMUTE_COLORS.get(commute, "#95a1ac")
        mode = row.get("transport_mode", "car")
        icon_name = MODE_ICONS.get(mode, "user")

        weekly_co2 = row.get("co2_weekly_mean_g", 0)
        annual_co2 = row.get("co2_annual_kg_mean", 0)
        savings_1d = row.get("savings_1day_g", 0)

        popup_html = f"""
        <div style='font-family:sans-serif; font-size:13px; min-width:180px'>
            <b>{row['name']}</b><br>
            <hr style='margin:4px 0'>
            🚗 Mode: <b>{mode}</b><br>
            📍 Distance: <b>{row.get('distance_km', 'N/A'):.1f} km</b><br>
            ⏱ Duration: <b>{row.get('duration_min', 'N/A'):.0f} min</b><br>
            🏷 Commute type: <b>{commute}</b><br>
            <hr style='margin:4px 0'>
            💨 Weekly CO₂: <b>{weekly_co2:,.0f} g</b><br>
            📅 Annual CO₂: <b>{annual_co2:.1f} kg</b><br>
            💚 Saving 1 telework day: <b>{savings_1d:,.0f} g/week</b>
        </div>
        """

        folium.CircleMarker(
            location=coords,
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{row['name']} — {commute} commute",
        ).add_to(cluster)

    # Legend
    legend_html = """
    <div style='position:fixed; bottom:30px; left:30px; z-index:1000;
                background:white; padding:12px 16px; border-radius:8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-family:sans-serif; font-size:13px'>
        <b>Commute type</b><br>
        <span style='color:#2ecc71'>●</span> Short (&lt;6 km)<br>
        <span style='color:#f39c12'>●</span> Medium (6–14.3 km)<br>
        <span style='color:#e74c3c'>●</span> Long (&gt;14.3 km)<br>
        <span style='color:#3498db'>■</span> Workplace
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    m.save(output_html)
    print(f"Map saved to {output_html} ({geocoded} employees mapped)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate commuting emissions map")
    parser.add_argument("--results", default="results/commuting_emissions.csv")
    parser.add_argument("--workplace", required=True)
    parser.add_argument("--api-key", default=os.environ.get("GOOGLE_MAPS_API_KEY"))
    parser.add_argument("--output", default="dashboard/emissions_map.html")
    args = parser.parse_args()

    build_map(args.results, args.workplace, args.api_key, args.output)
