# Participant scenario medallion notebooks

These facilitator-only notebook scripts build Bronze, Silver, and Gold tables for the four participant scenarios from the original hackathon dataset.

Use one notebook per scenario. In the Fabric Lakehouse, upload that scenario's CSV files plus the shared `calendar.csv` to `Files/Raw`, then paste the matching script into a Fabric notebook attached to the Lakehouse.

| Notebook | Scenario | Final Gold tables |
|---|---|---|
| `01_rail_performance_medallion_notebook.py` | Rail Performance | `fact_service`, `fact_delay_event`, `fact_cancellation`, `dim_route`, `dim_operator`, `dim_region`, `dim_calendar` |
| `02_safety_incidents_medallion_notebook.py` | Safety Incidents | `fact_incident`, `fact_corrective_action`, `fact_hours_worked`, `dim_location`, `dim_department`, `dim_region`, `dim_calendar` |
| `03_track_possessions_medallion_notebook.py` | Track Possessions | `fact_possession`, `fact_impact`, `dim_location`, `dim_contractor`, `dim_region`, `dim_calendar` |
| `04_fleet_operations_medallion_notebook.py` | Fleet Operations | `fact_availability_snapshot`, `fact_failure`, `fact_maintenance_workorder`, `dim_fleet_unit`, `dim_depot`, `dim_region`, `dim_calendar` |

Bronze and Silver tables are created for transparency and troubleshooting. Use the Gold tables in the Power BI semantic model.
