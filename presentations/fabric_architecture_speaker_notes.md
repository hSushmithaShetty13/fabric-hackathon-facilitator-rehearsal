# Speaker Notes: Three Ways to Build the Same Fabric Data Product

Companion to `fabric_architecture_three_solutions.pptx`.

**Suggested duration:** 10–12 minutes  
**Short version:** Use only the paragraphs marked **Core message** for a 5-minute presentation.

## Opening Context

The purpose of this presentation is not to identify one universally correct architecture. It is to show how the same business outcome can be delivered in Microsoft Fabric at three different levels of engineering maturity.

The example is a synthetic station-operations scenario. It combines energy usage, passenger volumes, passenger-assistance performance, and asset maintenance. The data is deliberately imperfect so that the solution must address both operational questions and confidence in the data.

The final business question is:

> Which three stations should operations intervene at first, and why?

The answer should explain whether each station is ranked because of high energy cost, poor energy efficiency, high assistance demand, low SLA fulfilment, open or overdue work orders, or data-quality concerns.

## The Data

There are seven source files:

| File | Grain | Role |
| --- | --- | --- |
| `calendar.csv` | One row per day | Shared date dimension |
| `regions.csv` | One row per region | Regional grouping |
| `stations.csv` | One row per station | Station name, type, region, and accessibility |
| `tariffs.csv` | One row per tariff band | Energy rate lookup |
| `station_daily.csv` | One row per station per day | Passengers, energy, weather, and meter quality |
| `assistance_requests.csv` | Station, day, and request type | Demand and SLA fulfilment |
| `asset_workorders.csv` | One row per work order | Repairs, dates, status, and estimated cost |

Important relationships:

- The three fact datasets join to `stations` through `StationID`.
- Stations join to `regions` through `RegionID`.
- Daily station activity joins to `tariffs` through `TariffBand`.
- Dates connect activity to the shared calendar.

Intentional data issues include inconsistent casing and whitespace, a missing station reference, a negative passenger count, an impossible SLA count, open assistance requests, open work orders, and reversed timestamps. These are included to demonstrate that a pipeline completing successfully does not necessarily mean the data is trustworthy.

## End Goal

The final Power BI product should contain:

1. An executive KPI overview.
2. A ranked list of the top three stations requiring intervention.
3. A clear reason for each ranking.
4. Diagnostics for data-quality and operational issues.
5. Station-level detail for investigation.

Useful measures include total energy, energy per 1,000 passengers, estimated energy cost, assistance requests, SLA fulfilment, open requests, open work orders, and overdue work orders.

The expected top three are:

1. **Leeds City** – open asset work, high assistance demand, and high energy intensity.
2. **Manchester Central** – highest assistance demand and high total energy cost.
3. **Brighton Junction** – high assistance demand and high energy intensity.

---

## Slide 1 – Three Ways to Build the Same Data Product

**Core message:** We are solving one business problem in three different ways. The difference is not the final report; the difference is how much automation, reuse, isolation, governance, and monitoring we build around it.

Start by describing the progression:

- The Simple approach prioritises speed and learning.
- Solution 2 introduces metadata-driven, incremental ingestion.
- Solution 3 separates Bronze, Silver, and Gold and uses a different Fabric engine at each stage.

Emphasise that all three approaches are valid in the right context. A short-lived prototype should not be burdened with unnecessary production controls, while a repeatable operational process should not depend on manual uploads.

**Transition:** Before looking at the technical diagrams, let us clarify what changes as we move across the three solutions.

## Slide 2 – One Outcome, Three Levels of Engineering

**Core message:** The architecture should match the risk and expected lifetime of the use case.

Explain the spectrum:

- **Simple** optimises time to first insight. It is ideal for a workshop, rehearsal, proof of concept, or one-off analysis.
- **Solution 2** optimises repeatability. A control file defines what to load, how to load it, and which keys and watermarks to use.
- **Solution 3** optimises governance and operational evidence. Storage and transformation responsibilities are separated, and every load produces audit, reconciliation, and quality results.

The important point is that engineering maturity is added deliberately. We are not adding components merely because Fabric provides them.

**Audience prompt:** Ask, “Is your current priority speed, repeatability, or operational assurance?”

**Transition:** Let us begin with the shortest path from source data to the business answer.

## Slide 3 – Simple: Quickest Route from CSV to Insight

**Core message:** Upload the files, transform them in a notebook or Dataflow, create report-ready tables, and build the Power BI model.

Walk from left to right:

1. Upload the seven CSV files into Lakehouse Files.
2. Use a notebook or Dataflow Gen2 to trim strings, cast dates and numbers, join reference data, and flag suspicious rows.
3. Produce a basic star schema with date, station, region, and tariff dimensions plus station-day, assistance, and work-order facts.
4. Build measures and the intervention-ranking report in Power BI.

Why this is useful:

- It exposes the data quickly.
- The transformation logic is easy to inspect and change.
- It keeps the learning focus on the business problem and Fabric fundamentals.

Trade-offs:

- File landing is manual.
- Rerun behaviour depends on the author’s discipline.
- Monitoring is mainly notebook output or visual inspection.
- Adding many more source entities creates repeated code and manual work.

**When to choose it:** Use this when the question is still evolving and the cost of production engineering is greater than the current risk.

**Transition:** Once the process must be rerun reliably across several files, the next improvement is to move behaviour into metadata.

## Slide 4 – Solution 2: Metadata-Driven Incremental Ingestion

**Core message:** Instead of building a separate pipeline for every file, one control table tells a generic pipeline what to do.

Explain `load_control.csv`:

- `enabled` controls participation in the run.
- `source_relative_path` identifies the source file.
- `target_table` selects the Delta target.
- `load_type` chooses truncate or incremental behaviour.
- `key_columns` provides the merge key.
- `watermark_column` optionally limits processing to newer records.

Walk through the flow:

1. A Lookup reads the control file from GitHub.
2. A Filter keeps enabled rows.
3. A sequential ForEach processes each entity.
4. Copy lands the source file under `Files/landing/<entity>`.
5. One parameterised notebook either overwrites the table or performs a Delta merge.
6. The notebook writes an ingestion-audit record with counts, status, timestamps, and the pipeline run ID.

The dimensions use truncate-reload because they are small and deterministic. The larger fact-like datasets use incremental merge:

- `station_daily`: `Date | StationID`
- `assistance_requests`: `Date | StationID | RequestType | OpenedTimestamp`
- `asset_workorders`: `WorkOrderID`

All generated tables are isolated in the `Solution2` schema of `lh_station_ops`. This keeps the demonstration separate from other solutions while reusing one Lakehouse.

**Key benefit:** Adding an eighth entity is mainly a metadata change rather than a new pipeline design.

**Trade-off:** This solution improves ingestion significantly, but cleansing, dimensional modelling, and enterprise-level monitoring are not yet separated into dedicated layers.

**Transition:** Solution 3 keeps the reusable ingestion idea and extends it into a full medallion architecture.

## Slide 5 – Solution 3: Multi-Engine Medallion

**Core message:** Each layer has a distinct purpose, a dedicated storage item, and the Fabric engine best suited to that responsibility.

Explain each stage:

### Source and Bronze

- The same GitHub control manifest drives ingestion.
- A Fabric Pipeline copies the source files.
- A parameterised Spark notebook writes raw Bronze Delta tables.
- Source values remain as text where possible, and lineage columns record the batch, file, and ingestion timestamp.
- Bronze is stored in the dedicated `lh_git_bronze` Lakehouse.

### Silver

- Dataflow Gen2 reads the Bronze tables.
- Power Query trims whitespace and control characters, standardises casing, performs safe type conversion, and creates `dq_is_valid` flags.
- Invalid records remain visible for diagnosis instead of disappearing silently.
- Silver is stored separately in `lh_dataflow_silver`.

### Gold

- The Warehouse stored procedure `etl.usp_load_gold` reads valid Silver rows.
- It builds the dimensional model in `wh_storedproc_gold`.
- The load is transactional, so errors can roll back the business tables while preserving failure evidence.

### Operations plane

- `audit.pipeline_run` records overall status and timing.
- `audit.pipeline_step` records source, target, and rejected counts.
- `audit.row_reconciliation` proves source equals target plus rejected rows.
- `audit.data_quality_result` records each rule, severity, evaluated rows, failures, and status.

This solution demonstrates that Fabric workloads are complementary. Pipeline, Spark, Dataflow Gen2, Warehouse T-SQL, and Power BI each perform the work they are strongest at.

**Trade-off:** It has more items, connections, deployment concerns, and operational overhead. Use that complexity only when the transparency and control are valuable.

**Transition:** The comparison table makes those trade-offs explicit.

## Slide 6 – Choosing the Engineering Level

**Core message:** Choose based on the operating model, not only on technical preference.

Use each row to frame a decision:

- If landing is occasional and manual, Simple may be sufficient.
- If many similar files must be loaded repeatedly, Solution 2 removes duplication.
- If teams need clear layer ownership, controlled promotion, reconciliation, and durable monitoring, Solution 3 is the stronger pattern.

Highlight that incrementality is not automatically applied to every layer:

- Solution 2 uses key-based Delta merge and optional watermarking.
- Solution 3 supports incremental behaviour in Bronze, while Silver and Gold are deterministic replacements for this small demonstration dataset.
- At larger scale, those Silver and Gold patterns could also become incremental, but only when the additional state management is justified.

The storage-isolation progression is also important:

- Simple uses whichever Lakehouse is chosen for the exercise.
- Solution 2 isolates tables through a schema.
- Solution 3 isolates responsibilities through dedicated Lakehouses and a Warehouse.

**Transition:** The final architecture was not only designed; it was executed and checked end to end.

## Slide 7 – Runtime Evidence

**Core message:** Success is demonstrated by business-table outcomes and operational evidence, not only by a green pipeline status.

The validated master run completed all three stages:

- Seven pipeline steps completed.
- Seven source-to-target reconciliations balanced.
- There was no unexplained row difference.
- 169 rows were intentionally rejected from Gold by the quality rules.

Explain the findings:

- 166 assistance rows have a close timestamp before the open timestamp.
- One assistance row has more fulfilled requests than total requests.
- One station-day row has a negative passenger count.
- One station-day row references a station that does not exist.

These rows remain visible in Silver for investigation and are excluded from the trusted Gold model. This is preferable to silently dropping them or allowing them to distort the report.

Also distinguish business state from bad data:

- Blank assistance close timestamps represent open requests.
- Blank work-order completion dates represent open work.
- They are operational conditions, not necessarily data errors.

**Transition:** The right solution therefore depends on how quickly we need the answer and how much assurance we need around it.

## Slide 8 – Decision Guide and Close

**Core message:** Start with the smallest architecture that safely answers the question, then add controls as repeatability and risk increase.

Close with three recommendations:

1. Choose **Simple** when learning, exploring, or proving the business value.
2. Choose **Solution 2** when the same ingestion pattern must support multiple entities and incremental reruns.
3. Choose **Solution 3** when data products need separate layers, multiple engineering personas, quality gates, reconciliation, and operational traceability.

The three solutions can also form a learning journey:

- First understand the data and business measures.
- Then remove repeated ingestion work through metadata.
- Finally introduce separation of concerns, governance, and monitoring.

End by returning to the business outcome:

> Regardless of architecture, the goal is to give operations a trusted, explainable list of the stations requiring action first.

## Optional Five-Minute Talk Track

Use this condensed sequence when time is limited:

1. **Data and goal:** Seven station-operations files feed a report that ranks the three stations requiring intervention based on energy, passenger assistance, asset work, and data quality.
2. **Simple:** Manually upload, transform in a notebook or Dataflow, and build Power BI. Fastest, but least automated.
3. **Solution 2:** Put source paths, load modes, keys, and watermarks in a control file. One generic pipeline and notebook load every entity and support incremental merge.
4. **Solution 3:** Separate Bronze, Silver, and Gold. Use Pipeline and Spark for landing, Dataflow Gen2 for cleansing, and a Warehouse stored procedure for trusted dimensional tables, audit, reconciliation, and DQ.
5. **Close:** The business answer is the same; the correct architecture depends on the required speed, repeatability, and assurance.

## Useful Questions for the Audience

- How often will this process run?
- How many additional entities are likely to be added?
- Must failed and rejected rows be explainable to another team?
- Is schema-level isolation enough, or do teams need separate storage items and permissions?
- Is the current bottleneck obtaining the first insight or operating the solution reliably?
- Which quality issues should block Gold, and which should only create warnings?

## Presenter Reference: Expected Business Results

| Metric | Expected result |
| --- | ---: |
| Station daily rows | 224 |
| Total estimated energy cost | 100,351.7 |
| Total passengers | 3,892,181 |
| Assistance requests | 2,798 |
| SLA fulfilment | 78.4% |
| Open assistance rows | 30 |
| Asset work orders | 46 |
| Open work orders | 8 |
| Overdue work orders | 8 |
| Bad station references | 1 |
| Negative passenger rows | 1 |
| Impossible SLA rows | 1 |

These values are useful for demonstrating that the data product is producing the intended business result, independently of which architecture was used to build it.