# 🚗 Commuting Emissions Calculator

> **Quantify, visualize, and reduce your organization's commuting CO₂ footprint using Google Maps API, Python, and BigQuery.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Google Maps API](https://img.shields.io/badge/Google%20Maps-API-green)](https://developers.google.com/maps)
[![BigQuery](https://img.shields.io/badge/BigQuery-GCP-orange)](https://cloud.google.com/bigquery)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What it does

This pipeline helps HR, Sustainability, and Estates teams measure and reduce **Scope 3 commuting emissions** by:

1. **Fetching real distances** from employee homes to the workplace via Google Maps Distance Matrix API
2. **Estimating CO₂ emissions** per employee using Monte Carlo simulation over European vehicle fleet emission factors
3. **Classifying commutes** as short / medium / long to identify high-impact telework candidates
4. **Uploading results to BigQuery** for historical tracking and dashboard integration
5. **Generating an interactive map** showing emissions by employee and commute type

---

## Research background

This tool is grounded in peer-reviewed research on urban decarbonisation and teleworking efficiency.

Key finding from the underlying study (under review, Urban Climate):

> Employees with long commutes (≥14.3 km) achieve **13.6× greater CO₂ savings** per teleworking day than short-distance commuters — making distance the primary driver of telework policy effectiveness.

The distance thresholds (short: ≤6 km, medium: 6–14.3 km, long: ≥14.3 km) are derived from tercile analysis of commuting patterns in a Mediterranean metropolitan area (Valencia, Spain, n=298).

---

## Quick start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your API keys
```bash
export GOOGLE_MAPS_API_KEY="your_key_here"
export GCP_PROJECT_ID="your_gcp_project"
```

### 3. Prepare your employee CSV
See `data/employees_sample.csv` for the expected format:

| employee_id | name | home_address | transport_mode | telework_days_per_week |
|-------------|------|--------------|----------------|------------------------|
| E001 | Ana García | Calle Mayor 10 Valencia Spain | car | 2 |

`transport_mode` accepts: `car`, `transit`, `bicycle`

### 4. Run the pipeline
```bash
# Calculate emissions
python src/emissions_calculator.py \
  --input data/employees_sample.csv \
  --workplace "Universitat de València, Av. Blasco Ibáñez 13, Valencia, Spain"

# Upload to BigQuery
python src/bigquery_upload.py \
  --results results/commuting_emissions.csv \
  --project YOUR_GCP_PROJECT

# Generate interactive map
python src/map_visualizer.py \
  --results results/commuting_emissions.csv \
  --workplace "Universitat de València, Av. Blasco Ibáñez 13, Valencia, Spain"
```

---

## Output

### `results/commuting_emissions.csv`
Per-employee table with:
- `distance_km` — real road distance from home to workplace
- `duration_min` — estimated commute time
- `commute_type` — short / medium / long
- `co2_weekly_mean_g` — mean weekly emissions (Monte Carlo)
- `co2_weekly_p5_g`, `co2_weekly_p95_g` — 90% confidence interval
- `co2_annual_kg_mean` — annual emissions in kg
- `savings_1day_g` — weekly savings from adding 1 telework day
- `savings_2days_g` — weekly savings from adding 2 telework days

### `dashboard/emissions_map.html`
Interactive map with employee markers color-coded by commute type, with CO₂ data in popups.

---

## Emission factors

| Mode | Mean (gCO₂/km) | Std |
|------|---------------|-----|
| Car | 158.0 | 32.0 |
| Transit | 68.0 | 12.0 |
| Bicycle | 0.0 | — |

Sources: European Environment Agency (EEA) 2023 · Spanish DGT vehicle fleet data

---

## Use cases

- 📋 **Carbon Reduction Plans** (UK GGC, EU CSRD)
- 🏢 **Hybrid work policy design** — identify employees who benefit most from telework
- 📊 **ESG Scope 3 reporting**
- 🗺 **Estate rationalisation** — understand where your workforce lives

---

## Project structure

```
commuting-emissions-calculator/
├── data/
│   └── employees_sample.csv      # Sample input (15 employees, Valencia)
├── src/
│   ├── emissions_calculator.py   # Main pipeline
│   ├── bigquery_upload.py        # GCP upload
│   └── map_visualizer.py         # Interactive map
├── dashboard/
│   └── emissions_map.html        # Generated map output
├── results/                      # Generated CSV outputs
├── requirements.txt
└── README.md
```

---

## License

MIT — free to use, adapt, and build upon.

---

## Author

**Rafael Mesa-Manzano, PhD**  
Geography & Spatial Data Science  
University of Valencia, Spain  

*Published researcher in urban decarbonisation and teleworking emissions. Available for consulting on commuting analysis, ESG reporting, and geospatial data projects.*
```
