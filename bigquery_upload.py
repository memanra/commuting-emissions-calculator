"""
BigQuery Uploader
=================
Uploads commuting emissions results to Google BigQuery for historical tracking
and dashboard integration.

Usage:
    python src/bigquery_upload.py --results results/commuting_emissions.csv \
        --project YOUR_GCP_PROJECT --dataset commuting_emissions
"""

import argparse
import os
from datetime import datetime

import pandas as pd
from google.cloud import bigquery


SCHEMA = [
    bigquery.SchemaField("run_date", "DATE"),
    bigquery.SchemaField("employee_id", "STRING"),
    bigquery.SchemaField("name", "STRING"),
    bigquery.SchemaField("transport_mode", "STRING"),
    bigquery.SchemaField("telework_days_per_week", "INTEGER"),
    bigquery.SchemaField("distance_km", "FLOAT"),
    bigquery.SchemaField("duration_min", "FLOAT"),
    bigquery.SchemaField("commute_type", "STRING"),
    bigquery.SchemaField("co2_weekly_mean_g", "FLOAT"),
    bigquery.SchemaField("co2_weekly_p5_g", "FLOAT"),
    bigquery.SchemaField("co2_weekly_p95_g", "FLOAT"),
    bigquery.SchemaField("co2_annual_kg_mean", "FLOAT"),
    bigquery.SchemaField("savings_1day_g", "FLOAT"),
    bigquery.SchemaField("savings_2days_g", "FLOAT"),
]


def upload_to_bigquery(
    results_csv: str,
    project_id: str,
    dataset_id: str,
    table_id: str = "emissions_by_employee",
) -> None:
    """
    Upload emissions results CSV to BigQuery.
    Creates dataset and table if they don't exist.
    Appends data with a run_date column for historical tracking.
    """
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    # Load and tag with run date
    df = pd.read_csv(results_csv)
    df["run_date"] = datetime.today().date().isoformat()

    # Create dataset if needed
    dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
    dataset.location = "EU"
    client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset {dataset_id} ready.")

    # Upload
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()

    table = client.get_table(table_ref)
    print(f"Uploaded {len(df)} rows to {table_ref} (total rows: {table.num_rows})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload emissions results to BigQuery")
    parser.add_argument("--results", default="results/commuting_emissions.csv")
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID"), required=True)
    parser.add_argument("--dataset", default="commuting_emissions")
    parser.add_argument("--table", default="emissions_by_employee")
    args = parser.parse_args()

    upload_to_bigquery(args.results, args.project, args.dataset, args.table)
