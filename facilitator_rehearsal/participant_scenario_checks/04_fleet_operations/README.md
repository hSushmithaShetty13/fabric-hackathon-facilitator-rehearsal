# Facilitator check: Fleet Operations

## Clear goal

Build a report that explains fleet availability, downtime drivers, repeated failures, and maintenance turnaround.

## End result to prove

The demo has worked if you can show:

- Availability percentage and average hours in service.
- Best and worst depots and fleet types.
- Failure count, downtime hours, delay minutes, and top failure type.
- Maintenance work order count, CM/PM split, and average turnaround hours.

## Suggested Gold model

| Table | Type |
|---|---|
| `fact_availability_snapshot` | Daily fleet availability fact table |
| `fact_failure` | Failure fact table |
| `fact_maintenance_workorder` | Maintenance work order fact table |
| `dim_fleet_unit` | Fleet unit dimension |
| `dim_depot` | Depot dimension |
| `dim_region` | Region dimension |
| `dim_calendar` | Date dimension |

## Relationships

| From | To | Notes |
|---|---|---|
| `fact_availability_snapshot[FleetID]` | `dim_fleet_unit[FleetID]` | Many-to-one |
| `fact_failure[FleetID]` | `dim_fleet_unit[FleetID]` | Many-to-one |
| `fact_maintenance_workorder[FleetID]` | `dim_fleet_unit[FleetID]` | Many-to-one |
| `dim_fleet_unit[DepotID]` | `dim_depot[DepotID]` | Many-to-one |
| `dim_depot[RegionID]` | `dim_region[RegionID]` | Many-to-one |
| `fact_availability_snapshot[Date]` | `dim_calendar[Date]` | Many-to-one |
| `fact_failure[FailureDate]` | `dim_calendar[Date]` | Many-to-one |
| `fact_maintenance_workorder[StartDate]` | `dim_calendar[Date]` | Many-to-one |

## KPI answer key

Assumptions: availability percentage is the share of snapshots where `Status = "In service"`.

| KPI | Expected answer |
|---|---:|
| Availability snapshots | 10,120 |
| Availability percentage | 81.9% |
| Average hours in service | 13.1 hours |
| Hours-in-service quality issues | 442 rows outside 0-24 |
| Best depot by availability | Depot East, 83.0% |
| Worst depot by availability | Depot North, 81.1% |
| Best fleet type by availability | Freight, 82.5% |
| Worst fleet type by availability | Maintenance, 81.1% |
| Failures | 248 |
| Failure downtime | 3,019.3 hours |
| Failure delay minutes | 11,300 |
| Top failure type | Brake, 55 failures |
| Most repeated failure unit | FL00067, 7 failures |
| Maintenance work orders | 357 |
| Corrective maintenance work orders | 164 |
| Preventive maintenance work orders | 193 |
| Average maintenance turnaround | 18.5 hours |

## Business question answers

| Question | Expected answer |
|---|---|
| Which depot has the best availability? | Depot East |
| Which depot has the weakest availability? | Depot North |
| What is driving downtime? | Failures account for 3,019.3 downtime hours; Brake is the most frequent failure type |
| Are there repeated-problem units? | Yes. FL00067 has 7 failure records |
| Is there a data-quality issue to catch? | Yes. 442 availability rows have hours outside the expected 0-24 range |

## Useful measures

```DAX
Availability Snapshots = COUNTROWS(fact_availability_snapshot)
In Service Snapshots = CALCULATE(COUNTROWS(fact_availability_snapshot), fact_availability_snapshot[Status] = "In service")
Availability % = DIVIDE([In Service Snapshots], [Availability Snapshots])
Average Hours In Service = AVERAGE(fact_availability_snapshot[HoursInService])
Failure Downtime Hours = SUM(fact_failure[DowntimeHours])
Failure Delay Minutes = SUM(fact_failure[DelayMinutes])
Maintenance Work Orders = COUNTROWS(fact_maintenance_workorder)
Average Maintenance Turnaround Hours = AVERAGE(fact_maintenance_workorder[TurnaroundHours])
```
