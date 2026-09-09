# Data dictionary

## Dataset: Station Energy and Passenger Assistance

This is a synthetic facilitator-only dataset for rehearsing a Microsoft Fabric hackathon build. It is designed to be realistic enough to test ingestion, transformation, modelling, reporting, and Copilot prompts without revealing or duplicating the participant scenarios.

## Files

| File | Grain | Description |
|---|---|---|
| `calendar.csv` | One row per day | Shared date table at `facilitator_rehearsal\datasets\calendar.csv` |
| `regions.csv` | One row per region | Region dimension |
| `stations.csv` | One row per station | Station dimension with region, station type, and accessibility attributes |
| `tariffs.csv` | One row per tariff band | Energy tariff lookup for estimated cost |
| `station_daily.csv` | One row per station per day | Daily passengers, electricity, weather, and meter quality |
| `assistance_requests.csv` | One row per station, day, and request type | Passenger assistance demand and SLA fulfilment |
| `asset_workorders.csv` | One row per asset work order | Station asset repairs, target dates, completion dates, and estimated cost |

The scenario folder intentionally contains six CSV files, with the shared `calendar.csv` one level above it. This mirrors the main hackathon pattern.

## Intentional data quirks

- `stations.csv` contains inconsistent station-name casing and leading/trailing whitespace.
- `station_daily.csv` has one station reference that does not exist in `stations.csv`.
- `station_daily.csv` has one negative passenger count that should be flagged.
- `assistance_requests.csv` has blank `ClosedTimestamp` values for open requests.
- `assistance_requests.csv` has one row where `FulfilledWithinSla` is greater than `RequestCount`.
- `asset_workorders.csv` has blank `CompletedDate` values for open work.
- Weather descriptions in `station_daily.csv` contain inconsistent casing and whitespace.

## Suggested star schema

| Table | Type | Notes |
|---|---|---|
| `dim_calendar` | Dimension | Use `calendar.csv`; mark as the date table |
| `dim_station` | Dimension | Clean names, join to regions |
| `dim_region` | Dimension | Region lookup |
| `dim_tariff` | Dimension | Energy rates for cost measures |
| `fact_station_daily` | Fact | Daily station energy, passengers, tariff, and weather |
| `fact_assistance_requests` | Fact | Daily request count and SLA performance |
| `fact_asset_workorders` | Fact | Work order status and repair cost |

## Suggested quality checks

| Check | Expected issue |
|---|---|
| Distinct station IDs in fact tables not found in `stations.csv` | One bad station ID in `station_daily.csv` |
| Negative passenger counts | One bad row |
| `FulfilledWithinSla > RequestCount` | One bad row |
| Blank `ClosedTimestamp` | Open requests, not necessarily bad data |
| Blank `CompletedDate` | Open work orders, not necessarily bad data |
| Energy per passenger outliers | A few station-days should stand out |

## Suggested gold table

Create a station-day gold table from `station_daily.csv` by joining:

- `stations`
- `regions`
- `calendar`
- `tariffs`

Useful derived columns:

- `EnergyPerPassenger`
- `EnergyPerThousandPassengers`
- `EstimatedEnergyCost`
- `IsWeekend`
- `WeatherBand`
- `IsEnergyOutlier`
- `StationNameClean`
- `StationTypeClean`

Keep assistance requests and asset work orders as separate fact tables unless you aggregate them to station-day grain first.

## Target output

The final report should include a ranked list of the three stations that need attention first. A simple intervention score can combine:

- High estimated energy cost.
- High energy per 1,000 passengers.
- Low assistance SLA fulfilment.
- High assistance request volume.
- Open or overdue asset work orders.
- Data-quality flags that reduce confidence.
