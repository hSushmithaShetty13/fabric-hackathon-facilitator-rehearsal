# Data dictionary

## Dataset: Station Energy and Passenger Assistance

This is a synthetic facilitator-only dataset for rehearsing a Microsoft Fabric hackathon build. It is designed to be realistic enough to test ingestion, transformation, modelling, reporting, and Copilot prompts without revealing or duplicating the participant scenarios.

## Files

| File | Grain | Description |
|---|---|---|
| `calendar.csv` | One row per day | Shared date table for the rehearsal period |
| `regions.csv` | One row per region | Region dimension |
| `stations.csv` | One row per station | Station dimension with region, station type, and accessibility attributes |
| `energy_daily.csv` | One row per station per day | Daily electricity consumption by station |
| `footfall_daily.csv` | One row per station per day | Daily passenger entries and exits |
| `assistance_requests.csv` | One row per station, day, and request type | Passenger assistance demand and SLA fulfilment |
| `weather_daily.csv` | One row per station per day | Synthetic weather context for explaining energy and assistance demand |

## Intentional data quirks

- `stations.csv` contains inconsistent station-name casing and leading/trailing whitespace.
- `energy_daily.csv` has one station reference that does not exist in `stations.csv`.
- `footfall_daily.csv` has one negative passenger count that should be flagged.
- `assistance_requests.csv` has blank `ClosedTimestamp` values for open requests.
- `assistance_requests.csv` has one row where `FulfilledWithinSla` is greater than `RequestCount`.
- `weather_daily.csv` uses mixed weather descriptions that should be normalised for reporting.

## Suggested star schema

| Table | Type | Notes |
|---|---|---|
| `dim_calendar` | Dimension | Use `calendar.csv`; mark as the date table |
| `dim_station` | Dimension | Clean names, join to regions |
| `dim_region` | Dimension | Region lookup |
| `fact_energy_daily` | Fact | Daily station energy consumption |
| `fact_footfall_daily` | Fact | Daily passenger counts |
| `fact_assistance_requests` | Fact | Daily request count and SLA performance |
| `fact_weather_daily` | Fact/context | Can be joined by station and date or merged into a station-day gold table |

## Suggested quality checks

| Check | Expected issue |
|---|---|
| Distinct station IDs in fact tables not found in `stations.csv` | One bad station ID |
| Negative passenger counts | One bad row |
| `FulfilledWithinSla > RequestCount` | One bad row |
| Blank `ClosedTimestamp` | Open requests, not necessarily bad data |
| Energy per passenger outliers | A few station-days should stand out |

## Suggested gold table

Create a station-day gold table by joining:

- `energy_daily`
- `footfall_daily`
- `weather_daily`
- `stations`
- `regions`
- `calendar`

Useful derived columns:

- `EnergyPerPassenger`
- `EnergyPerThousandPassengers`
- `IsWeekend`
- `WeatherBand`
- `IsEnergyOutlier`
- `StationNameClean`
- `StationTypeClean`

Keep assistance requests as a separate fact table unless you aggregate them to station-day grain first.
