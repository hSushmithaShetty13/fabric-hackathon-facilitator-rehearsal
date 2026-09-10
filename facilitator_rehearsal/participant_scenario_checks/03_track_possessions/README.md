# Facilitator check: Track Possessions

## Clear goal

Build a report that shows which possession types, reasons, and contractors overrun most often, and how overruns affect services.

## End result to prove

The demo has worked if you can show:

- Possession count, overrun count, overrun rate, and average overrun minutes.
- Worst possession type, reason, and contractor by average overrun.
- Total services impacted, delay minutes, and cancellations.
- A drill-through view from contractor or possession type to possession detail.

## Suggested Gold model

| Table | Type |
|---|---|
| `fact_possession` | Possession fact table |
| `fact_impact` | Service impact fact table |
| `dim_location` | Location dimension |
| `dim_contractor` | Contractor dimension |
| `dim_region` | Region dimension |
| `dim_calendar` | Date dimension |

## Relationships

| From | To | Notes |
|---|---|---|
| `fact_possession[LocationID]` | `dim_location[LocationID]` | Many-to-one |
| `fact_possession[ContractorID]` | `dim_contractor[ContractorID]` | Many-to-one |
| `dim_location[RegionID]` | `dim_region[RegionID]` | Many-to-one |
| `fact_possession[PlannedStartDate]` | `dim_calendar[Date]` | Many-to-one |
| `fact_impact[PossessionID]` | `fact_possession[PossessionID]` | One-to-one or many-to-one |

## KPI answer key

Assumptions: overrun minutes = actual duration minus planned duration; negative values mean finished early.

| KPI | Expected answer |
|---|---:|
| Total possessions | 240 |
| Overrunning possessions | 177 |
| Overrun rate | 73.8% |
| Average overrun | 25.4 minutes |
| Total services impacted | 6,237 |
| Total delay minutes | 48,529 |
| Total cancellations | 1,266 |
| Worst possession type by average overrun | Emergency, 60.7 minutes |
| Worst reason by average overrun | Fault repair, 35.3 minutes |
| Worst contractor by average overrun | Contractor Alpha, 31.4 minutes |

## Business question answers

| Question | Expected answer |
|---|---|
| Which possession type overruns most? | Emergency possessions |
| Which reason is most associated with overrun? | Fault repair |
| Which contractor needs most attention? | Contractor Alpha |
| What is the operational impact? | 48,529 delay minutes and 1,266 cancellations across the dataset |

## Useful measures

```DAX
Total Possessions = COUNTROWS(fact_possession)
Overrunning Possessions = COUNTROWS(FILTER(fact_possession, fact_possession[OverrunMinutes] > 0))
Overrun Rate = DIVIDE([Overrunning Possessions], [Total Possessions])
Average Overrun Minutes = AVERAGE(fact_possession[OverrunMinutes])
Services Impacted = SUM(fact_impact[ServicesImpacted])
Delay Minutes = SUM(fact_impact[DelayMinutes])
Cancellations = SUM(fact_impact[Cancellations])
```
