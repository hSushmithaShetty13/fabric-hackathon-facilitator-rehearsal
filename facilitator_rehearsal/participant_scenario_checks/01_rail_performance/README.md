# Facilitator check: Rail Performance

## Clear goal

Build a report that shows which routes and operators have the weakest punctuality, what causes most delay minutes, and where cancellations are concentrated.

## End result to prove

The demo has worked if you can show:

- Total services, cancellation count, cancellation rate, and on-time percentage.
- Worst routes and operators by on-time performance.
- Top delay reason group and delay reason by total delay minutes.
- A route/operator detail page that explains why a service group is performing badly.

## Suggested Gold model

| Table | Type |
|---|---|
| `fact_service` | Service-level fact table |
| `fact_delay_event` | Delay-event fact table |
| `fact_cancellation` | Cancellation fact table |
| `dim_route` | Route dimension |
| `dim_operator` | Operator dimension |
| `dim_region` | Region dimension |
| `dim_calendar` | Date dimension |

## Relationships

| From | To | Notes |
|---|---|---|
| `fact_service[RouteID]` | `dim_route[RouteID]` | Many-to-one |
| `fact_service[OperatorID]` | `dim_operator[OperatorID]` | Many-to-one |
| `dim_route[RegionID]` | `dim_region[RegionID]` | Many-to-one |
| `fact_service[Date]` | `dim_calendar[Date]` | Many-to-one |
| `fact_delay_event[ServiceID]` | `fact_service[ServiceID]` | Many-to-one, use carefully |
| `fact_cancellation[ServiceID]` | `fact_service[ServiceID]` | One-to-one or many-to-one |

## KPI answer key

Assumptions: cancelled services are excluded from the on-time percentage; a service is on time if `ActualArrival <= ScheduledArrival + 5 minutes`.

| KPI | Expected answer |
|---|---:|
| Total services | 1,200 |
| Cancelled services | 104 |
| Cancellation rate | 8.7% |
| Delay events | 1,572 |
| On-time percentage | 21.9% |
| Average arrival delay | 20.0 minutes |
| Top delay reason group | Infrastructure, 8,516 minutes |
| Top delay reason | Points failure, 3,213 minutes |

## Business question answers

| Question | Expected answer |
|---|---|
| Worst routes by on-time performance | Leeds - York, Manchester - Liverpool, Birmingham - Leicester |
| Worst operators by on-time performance | Anglia Express, CityConnect, NorthRail |
| Main cause of delay | Infrastructure, especially Points failure |
| Minimum viable story | Poor punctuality is route/operator specific, and infrastructure faults are the biggest delay-minute driver |

## Useful measures

```DAX
Total Services = COUNTROWS(fact_service)
Cancelled Services = CALCULATE(COUNTROWS(fact_service), fact_service[IsCancelled] = TRUE())
Cancellation Rate = DIVIDE([Cancelled Services], [Total Services])
Delay Minutes = SUM(fact_delay_event[DelayMinutes])
On Time Services = CALCULATE(COUNTROWS(fact_service), fact_service[IsCancelled] = FALSE(), fact_service[ArrivalDelayMinutes] <= 5)
On Time % = DIVIDE([On Time Services], CALCULATE(COUNTROWS(fact_service), fact_service[IsCancelled] = FALSE()))
```
