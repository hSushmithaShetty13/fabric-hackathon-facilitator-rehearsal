# Microsoft Fabric Facilitator Rehearsal Pack

This repository contains a facilitator-only rehearsal dataset for testing the hackathon flow before participants use the main scenarios.

The scenario is intentionally separate from the participant datasets: it focuses on station energy usage and passenger assistance demand, not rail performance, safety incidents, track possessions, or fleet operations.

## Contents

- `facilitator_rehearsal\datasets\calendar.csv` - shared calendar
- `facilitator_rehearsal\datasets\station_energy_assistance\` - six synthetic scenario CSVs
- `facilitator_rehearsal\quick-test-guide.md` - fastest way to validate the end-to-end Fabric build
- `facilitator_rehearsal\data-dictionary.md` - table descriptions, joins, quirks, and suggested measures
- `facilitator_rehearsal\participant_scenario_checks\` - facilitator-only answer keys for the four original participant scenarios
- `multi-engine-demo\` - isolated Pipeline-to-Lakehouse, Dataflow-to-Lakehouse, and stored-procedure-to-Warehouse teaching solution with audit and data-quality monitoring
- `tools\generate_station_energy_assistance.py` - deterministic dataset generator

## Clear goal

Build a Fabric report that identifies the **three stations where operations should intervene first** because they combine high energy cost, high passenger volume, poor assistance SLA fulfilment, or unresolved asset work orders.

The desired end result is a stakeholder-ready Power BI report with:

- A ranked station intervention list.
- The reason each station is ranked highly.
- Recommended actions, such as investigate metering, review staffing, or prioritise asset repairs.

## Rehearsal flow

Build a small but complete Fabric solution:

1. Land the raw CSV files in a Lakehouse.
2. Transform them into clean tables.
3. Create a semantic model with relationships and a few measures.
4. Build a Power BI report with KPI, diagnostics, and detail pages.
5. Optionally use Copilot in a notebook or Power BI to accelerate part of the workflow.

The data is synthetic and deliberately imperfect, so it is safe for rehearsal and useful for testing cleaning, modelling, and reporting choices.
