# Facilitator check: Safety Incidents

## Clear goal

Build a report that identifies safety hotspots, normalises incidents by hours worked, and shows whether corrective actions are being completed on time.

## End result to prove

The demo has worked if you can show:

- Total incidents, open incidents, average days to close, and corrective-action on-time percentage.
- Incident hotspots by location, location type, incident type, and department.
- Incident rate by department using worked hours as the denominator.
- Corrective-action closure performance.

## Suggested Gold model

| Table | Type |
|---|---|
| `fact_incident` | Incident fact table |
| `fact_corrective_action` | Corrective-action fact table |
| `fact_hours_worked` | Monthly hours-worked fact table |
| `dim_location` | Location dimension |
| `dim_region` | Region dimension |
| `dim_calendar` | Date dimension |
| `dim_department` | Optional department dimension |

## Relationships

| From | To | Notes |
|---|---|---|
| `fact_incident[LocationID]` | `dim_location[LocationID]` | Many-to-one |
| `dim_location[RegionID]` | `dim_region[RegionID]` | Many-to-one |
| `fact_incident[Date]` | `dim_calendar[Date]` | Many-to-one |
| `fact_corrective_action[IncidentID]` | `fact_incident[IncidentID]` | Many-to-one |
| `fact_hours_worked[Department]` | `dim_department[Department]` | Many-to-one, if using department dimension |
| `fact_incident[Department]` | `dim_department[Department]` | Many-to-one, if using department dimension |

## KPI answer key

Assumptions: incident rate is incidents per 100,000 worked hours; average days to close excludes open incidents.

| KPI | Expected answer |
|---|---:|
| Total incidents | 420 |
| Open incidents | 110 |
| Average days to close | 28.5 days |
| Corrective actions | 368 |
| Completed corrective actions | 261 |
| Corrective-action on-time rate | 14.6% |
| Top incident location | Location 22, 24 incidents |
| Top incident type | TRIP, 63 incidents |
| Top department by raw incident count | Customer Service, 89 incidents |
| Highest incident rate department | Security, 265.3 per 100k hours |

## Business question answers

| Question | Expected answer |
|---|---|
| Where is the main hotspot? | Location 22, a Station location, with 24 incidents |
| Which incident type appears most often? | TRIP |
| Does normalising by hours worked change the story? | Yes. Customer Service has the highest raw count, but Security has the highest incident rate |
| Are corrective actions healthy? | No. Only about 14.6% of completed actions are completed on or before due date |

## Useful measures

```DAX
Total Incidents = COUNTROWS(fact_incident)
Open Incidents = COUNTROWS(FILTER(fact_incident, ISBLANK(fact_incident[ClosedDate])))
Average Days to Close = AVERAGEX(FILTER(fact_incident, NOT ISBLANK(fact_incident[ClosedDate])), fact_incident[DaysToClose])
Worked Hours = SUM(fact_hours_worked[WorkedHours])
Incident Rate per 100k Hours = DIVIDE([Total Incidents], [Worked Hours]) * 100000
Corrective Action On Time % = DIVIDE([Actions Completed On Time], [Completed Corrective Actions])
```
