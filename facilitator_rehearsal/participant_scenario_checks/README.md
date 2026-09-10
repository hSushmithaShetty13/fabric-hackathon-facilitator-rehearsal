# Facilitator scenario checks

This section is for facilitators only. It gives quick demo-build guidance and expected KPI answers for the four participant scenarios in the original hackathon repository.

Use these folders to confirm that ingestion, transformation, relationships, and measures are working before the event. Do not share the answer keys with participants.

## Folders

| Folder | Scenario | Demo outcome |
|---|---|---|
| `01_rail_performance` | Rail Performance | Identify the worst routes/operators and main delay causes |
| `02_safety_incidents` | Safety Incidents | Identify safety hotspots and corrective-action performance |
| `03_track_possessions` | Track Possessions | Identify possession overrun patterns and service impacts |
| `04_fleet_operations` | Fleet Operations | Identify availability, downtime, and maintenance issues |

## How to use

1. Build the participant scenario in Fabric using Bronze, Silver, and Gold layers.
2. Add only the Gold fact and dimension tables to the semantic model.
3. Create the KPI measures listed in the folder.
4. Compare your report numbers with the facilitator answer key.

Small differences can happen if you intentionally choose a different business definition, such as "on time within 0 minutes" instead of "on time within 5 minutes". If the numbers are very different, check date parsing, joins, null handling, and many-to-one relationships first.
