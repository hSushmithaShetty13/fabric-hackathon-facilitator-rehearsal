# Quick test guide

## Scenario

You are helping station operations understand whether passenger assistance demand and station energy consumption are creating avoidable cost or service pressure.

## Business questions

1. Which stations have the highest assistance demand, and when does demand peak?
2. Are assistance requests being fulfilled on time, and which request types are most at risk?
3. Which stations consume the most energy per passenger, and are there abnormal days?
4. Do weather and passenger footfall explain energy spikes, or do some stations still stand out?

## Fastest end-to-end path in Fabric

### 1. Land the data

Create a Lakehouse and upload all CSV files from:

`facilitator_rehearsal\datasets\station_energy_assistance\`

Use the simple Lakehouse file upload first. If you want to test a more realistic facilitator pattern, repeat the ingest with a Data Factory pipeline copy activity.

### 2. Clean and transform

Use a notebook or Dataflow Gen2. For the quickest test, use a notebook because it is easier to rerun and inspect.

Minimum cleaning:

- Trim and normalise station names before joining.
- Cast all date columns to date and all timestamp columns to datetime.
- Convert `EnergyKwh`, `PassengerCount`, `TemperatureC`, `RequestCount`, and `FulfilledWithinSla` to numeric types.
- Treat blank `ClosedTimestamp` values as open assistance requests.
- Flag impossible or suspicious values:
  - `PassengerCount < 0`
  - `EnergyKwh <= 0`
  - `FulfilledWithinSla > RequestCount`
  - station IDs in fact tables that do not exist in `stations.csv`

Suggested medallion layers:

| Layer | Output |
|---|---|
| Bronze | Raw CSV tables as landed |
| Silver | Cleaned typed tables |
| Gold | `fact_station_day`, `fact_assistance_request`, `dim_station`, `dim_region`, `dim_calendar`, `dim_weather_band` |

### 3. Model

Recommended relationships:

| From | To | Relationship |
|---|---|---|
| `energy_daily[StationID]` | `stations[StationID]` | Many-to-one |
| `footfall_daily[StationID]` | `stations[StationID]` | Many-to-one |
| `assistance_requests[StationID]` | `stations[StationID]` | Many-to-one |
| `stations[RegionID]` | `regions[RegionID]` | Many-to-one |
| All fact date columns | `calendar[Date]` | Many-to-one |

Useful starter measures:

```DAX
Total Energy kWh = SUM(energy_daily[EnergyKwh])
Total Passengers = SUM(footfall_daily[PassengerCount])
Energy per 1k Passengers = DIVIDE([Total Energy kWh], [Total Passengers]) * 1000
Assistance Requests = SUM(assistance_requests[RequestCount])
SLA Fulfilment % = DIVIDE(SUM(assistance_requests[FulfilledWithinSla]), [Assistance Requests])
Open Requests = COUNTROWS(FILTER(assistance_requests, ISBLANK(assistance_requests[ClosedTimestamp])))
```

### 4. Report

Build three pages:

| Page | Purpose | Visuals |
|---|---|---|
| KPI overview | One-page executive summary | Cards for energy, energy per 1k passengers, requests, SLA %, trend line |
| Diagnostics | Find data or operational issues | Matrix by station and date, quality flags, scatter energy vs passengers |
| Station detail | Drill-through story | Station slicer, daily trend, request type breakdown, weather context |

### 5. Quick pass criteria

The rehearsal is successful if you can:

- Rerun ingest and transform without manual fixes.
- Explain every join and one data-quality issue.
- Build at least one usable measure from each fact area.
- Demo the result in five minutes.

## Suggested Copilot prompts

Use these only after the raw data is loaded.

```text
Generate PySpark code to load these CSV files from a Fabric Lakehouse Files folder, infer schema carefully, trim string columns, cast date and timestamp columns, and write cleaned Delta tables.
```

```text
Create DAX measures for total energy kWh, total passengers, energy per 1,000 passengers, assistance requests, and SLA fulfilment percentage.
```

```text
Suggest a Power BI report page that helps station managers identify high-energy stations after normalising for passenger footfall and weather.
```
