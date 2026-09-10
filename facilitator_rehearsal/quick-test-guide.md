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

Use the **Gold** tables in the semantic model. Do not add the Bronze or Silver tables unless you want a separate diagnostics-only model.

Recommended relationships:

| From | To | Relationship |
|---|---|---|
| `fact_station_day[StationID]` | `dim_station[StationID]` | Many-to-one, single direction |
| `fact_assistance_request[StationID]` | `dim_station[StationID]` | Many-to-one, single direction |
| `fact_asset_workorder[StationID]` | `dim_station[StationID]` | Many-to-one, single direction |
| `dim_station[RegionID]` | `dim_region[RegionID]` | Many-to-one, single direction |
| `fact_station_day[TariffBand]` | `dim_tariff[TariffBand]` | Many-to-one, single direction |
| `fact_station_day[Date]` | `dim_calendar[Date]` | Many-to-one, single direction |
| `fact_assistance_request[Date]` | `dim_calendar[Date]` | Many-to-one, single direction |
| `fact_asset_workorder[OpenedDate]` | `dim_calendar[Date]` | Many-to-one, single direction; keep inactive if you also add `TargetDate` or `CompletedDate` |

Optional report-ready table:

| From | To | Relationship |
|---|---|---|
| `gold_station_intervention_score[StationID]` | `dim_station[StationID]` | Many-to-one, single direction |

Useful starter measures:

```DAX
Total Energy kWh = SUM(fact_station_day[EnergyKwh])
Total Passengers = SUM(fact_station_day[PassengerCount])
Energy per 1k Passengers = DIVIDE([Total Energy kWh], [Total Passengers]) * 1000
Estimated Energy Cost = SUM(fact_station_day[EstimatedEnergyCost])
Assistance Requests = SUM(fact_assistance_request[RequestCount])
SLA Fulfilment % = DIVIDE(SUM(fact_assistance_request[FulfilledWithinSla]), [Assistance Requests])
Open Requests = COUNTROWS(FILTER(fact_assistance_request, ISBLANK(fact_assistance_request[ClosedTimestamp])))
Open Work Orders = COUNTROWS(FILTER(fact_asset_workorder, ISBLANK(fact_asset_workorder[CompletedDate])))
```

### 4. Report

Build three pages:

| Page | Purpose | Visuals |
|---|---|---|
| KPI overview | One-page executive summary | Cards for cost, energy per 1k passengers, requests, SLA %, open work orders |
| Intervention ranking | Decide the top three stations | Ranked table, reason codes, cost vs SLA scatter, station slicers |
| Diagnostics | Find data or operational issues | Matrix by station and date, quality flags, orphan station references |
| Station detail | Drill-through story | Daily trend, request type breakdown, work order list, weather context |

### 5. Optional publish step: Fabric Org App

This is **not required** for the 5-minute demo. It is useful if you want to test the full stakeholder-consumption path after the report is built.

Use it when:

- You want to validate report permissions before the hackathon.
- You want to show how a finished report would be packaged for consumers.
- You have enough time after the core report is working.

Skip it when:

- You are still fixing ingestion, modelling, or measures.
- The demo is only a workspace walkthrough.
- You do not want to spend time on app audience/access settings.

Suggested quick test:

1. Create the Power BI report from the Gold semantic model.
2. Save the report in the Fabric workspace.
3. Create or update a Fabric Org App.
4. Add the report to the app.
5. Set the audience to only yourself or the facilitator group.
6. Publish the app and open it from the app link.
7. Confirm slicers, drill-through, and top-three station ranking still work.

### 6. Quick pass criteria

The rehearsal is successful if you can:

- Rerun ingest and transform without manual fixes.
- Explain every join and one data-quality issue.
- Produce a ranked top-three station intervention list.
- Demo the result in five minutes.
- Optionally publish the report as a Fabric Org App and open it as a consumer.

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
