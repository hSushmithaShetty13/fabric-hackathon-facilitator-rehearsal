# Quick test guide

## Scenario

You are helping station operations decide where to intervene first across a small network of stations.

## End result

Create a Power BI report that ranks the **top three stations needing operational attention** and explains why each station appears on the list.

The ranking should combine:

- Energy cost and energy per passenger.
- Passenger assistance demand and SLA fulfilment.
- Open or overdue asset work orders.
- Data-quality issues that may affect confidence in the answer.

## Business questions

1. Which three stations should operations focus on first?
2. Is each station on the list because of cost, demand, SLA risk, asset issues, or data-quality concerns?
3. Which stations have unusually high energy per passenger?
4. Are passenger assistance requests being fulfilled within SLA?

## Fastest end-to-end path in Fabric

### 1. Land the data

Create a Lakehouse and upload all CSV files from:

`facilitator_rehearsal\datasets\calendar.csv`

and all six CSV files from:

`facilitator_rehearsal\datasets\station_energy_assistance\`

Use the simple Lakehouse file upload first. If you want to test a more realistic facilitator pattern, repeat the ingest with a Data Factory pipeline copy activity.

### 2. Clean and transform

Use a notebook or Dataflow Gen2. For the quickest test, use a notebook because it is easier to rerun and inspect.

Minimum cleaning:

- Trim and normalise station names before joining.
- Cast all date columns to date and all timestamp columns to datetime.
- Convert `EnergyKwh`, `PassengerCount`, `TemperatureC`, `RatePerKwh`, `RequestCount`, `FulfilledWithinSla`, and `EstimatedCost` to numeric types.
- Treat blank `ClosedTimestamp` values as open assistance requests.
- Treat blank `CompletedDate` values as open asset work orders.
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
| Gold | `fact_station_day`, `fact_assistance_request`, `fact_asset_workorder`, `dim_station`, `dim_region`, `dim_calendar`, `dim_tariff` |

### 3. Model

Recommended relationships:

| From | To | Relationship |
|---|---|---|
| `station_daily[StationID]` | `stations[StationID]` | Many-to-one |
| `assistance_requests[StationID]` | `stations[StationID]` | Many-to-one |
| `asset_workorders[StationID]` | `stations[StationID]` | Many-to-one |
| `stations[RegionID]` | `regions[RegionID]` | Many-to-one |
| `station_daily[TariffBand]` | `tariffs[TariffBand]` | Many-to-one |
| All fact date columns | `calendar[Date]` | Many-to-one |

Useful starter measures:

```DAX
Total Energy kWh = SUM(station_daily[EnergyKwh])
Total Passengers = SUM(station_daily[PassengerCount])
Energy per 1k Passengers = DIVIDE([Total Energy kWh], [Total Passengers]) * 1000
Estimated Energy Cost = SUMX(station_daily, station_daily[EnergyKwh] * RELATED(tariffs[RatePerKwh]))
Assistance Requests = SUM(assistance_requests[RequestCount])
SLA Fulfilment % = DIVIDE(SUM(assistance_requests[FulfilledWithinSla]), [Assistance Requests])
Open Requests = COUNTROWS(FILTER(assistance_requests, ISBLANK(assistance_requests[ClosedTimestamp])))
Open Work Orders = COUNTROWS(FILTER(asset_workorders, ISBLANK(asset_workorders[CompletedDate])))
```

### 4. Report

Build three pages:

| Page | Purpose | Visuals |
|---|---|---|
| KPI overview | One-page executive summary | Cards for cost, energy per 1k passengers, requests, SLA %, open work orders |
| Intervention ranking | Decide the top three stations | Ranked table, reason codes, cost vs SLA scatter, station slicers |
| Diagnostics | Find data or operational issues | Matrix by station and date, quality flags, orphan station references |
| Station detail | Drill-through story | Daily trend, request type breakdown, work order list, weather context |

### 5. Quick pass criteria

The rehearsal is successful if you can:

- Rerun ingest and transform without manual fixes.
- Explain every join and one data-quality issue.
- Produce a ranked top-three station intervention list.
- Demo the result in five minutes.

## Suggested Copilot prompts

Use these only after the raw data is loaded.

```text
Generate PySpark code to load these CSV files from a Fabric Lakehouse Files folder, infer schema carefully, trim string columns, cast date and timestamp columns, flag quality issues, and write cleaned Delta tables.
```

```text
Create DAX measures for estimated energy cost, total passengers, energy per 1,000 passengers, assistance requests, SLA fulfilment percentage, open work orders, and a station intervention score.
```

```text
Suggest a Power BI report page that ranks stations requiring intervention based on high energy cost, low SLA fulfilment, assistance demand, and open asset work orders.
```
