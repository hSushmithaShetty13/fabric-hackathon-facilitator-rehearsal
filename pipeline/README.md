# Control-driven GitHub CSV ingestion

`pl_github_controlled_csv_load` reads `control/load_control.csv` directly from
the public GitHub repository and loads each enabled CSV into `lh_station_ops`.

## Pipeline flow

1. `Read Load Control` loads all control rows with a Lookup activity.
2. `Filter Enabled Loads` retains rows where `enabled` is `true`.
3. `For Each Enabled Load` processes the rows sequentially.
4. `Copy GitHub CSV to Lakehouse` lands each source under
	`Files/landing/<entity_name>/<entity_name>.csv`.
5. `Load CSV to Delta` passes the control values to
	`nb_github_controlled_load` as notebook parameters.

## Control columns

| Column | Purpose |
| --- | --- |
| `enabled` | Includes or excludes the entity from a run. |
| `entity_name` | Names the landed CSV and audit entity. |
| `source_relative_path` | Locates the CSV below the repository root. |
| `target_table` | Names the Lakehouse Delta table. |
| `load_type` | Selects `TRUNCATE` overwrite or `INCREMENTAL` merge. |
| `key_columns` | Supplies pipe-delimited merge keys. |
| `watermark_column` | Optionally filters rows newer than the target maximum. |

The notebook writes one audit record per entity to `ingestion_audit`, including
the pipeline run ID, source and processed row counts, status, and timestamps.
