# Fabric notebook: Fleet Operations medallion build
#
# Upload fleet_operations CSVs plus shared calendar.csv to Files/Raw.
# Use Gold tables in the semantic model.

from pyspark.sql import functions as F
from pyspark.sql import types as T


RAW_PATH = "Files/Raw"
CSV_FILES = {
    "calendar": "calendar.csv",
    "availability_snapshots": "availability_snapshots.csv",
    "failures": "failures.csv",
    "maintenance_workorders": "maintenance_workorders.csv",
    "fleet_units": "fleet_units.csv",
    "depots": "depots.csv",
    "regions": "regions.csv",
}


def read_csv(file_name: str):
    return spark.read.option("header", "true").option("inferSchema", "false").csv(f"{RAW_PATH}/{file_name}")


def save_table(df, table_name: str):
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)


def clean(column_name: str):
    return F.trim(F.col(column_name))


# COMMAND ----------

# Bronze: raw CSVs as landed

for table_name, file_name in CSV_FILES.items():
    save_table(
        read_csv(file_name)
        .withColumn("_source_file", F.lit(file_name))
        .withColumn("_ingested_at_utc", F.current_timestamp()),
        f"bronze_{table_name}",
    )


# COMMAND ----------

# Silver: cleaned and typed tables

save_table(
    spark.table("bronze_calendar").select(
        F.to_date("Date").alias("Date"),
        F.col("Year").cast(T.IntegerType()).alias("Year"),
        F.col("Month").cast(T.IntegerType()).alias("Month"),
        clean("MonthName").alias("MonthName"),
        F.to_date("WeekStartDate").alias("WeekStartDate"),
        clean("DayName").alias("DayName"),
        F.col("IsWeekend").cast(T.BooleanType()).alias("IsWeekend"),
    ),
    "silver_calendar",
)

save_table(
    spark.table("bronze_regions").select(
        clean("RegionID").alias("RegionID"),
        clean("Region").alias("RegionName"),
    ),
    "silver_regions",
)

save_table(
    spark.table("bronze_depots").select(
        clean("DepotID").alias("DepotID"),
        clean("DepotName").alias("DepotName"),
        clean("RegionID").alias("RegionID"),
    ),
    "silver_depots",
)

save_table(
    spark.table("bronze_fleet_units").select(
        clean("FleetID").alias("FleetID"),
        clean("FleetType").alias("FleetType"),
        clean("DepotID").alias("DepotID"),
    ),
    "silver_fleet_units",
)

silver_availability = (
    spark.table("bronze_availability_snapshots")
    .select(
        clean("FleetID").alias("FleetID"),
        F.to_date("Date").alias("Date"),
        clean("Status").alias("Status"),
        F.col("HoursInService").cast(T.DoubleType()).alias("HoursInService"),
    )
    .withColumn("IsInService", F.col("Status") == F.lit("In service"))
    .withColumn("IsInvalidHoursInService", (F.col("HoursInService") < 0) | (F.col("HoursInService") > 24))
)
save_table(silver_availability, "silver_availability_snapshots")

save_table(
    spark.table("bronze_failures").select(
        clean("FleetID").alias("FleetID"),
        F.to_date("FailureDate").alias("FailureDate"),
        clean("FailureType").alias("FailureType"),
        F.col("DowntimeHours").cast(T.DoubleType()).alias("DowntimeHours"),
        F.col("DelayMinutes").cast(T.IntegerType()).alias("DelayMinutes"),
    ),
    "silver_failures",
)

silver_workorders = (
    spark.table("bronze_maintenance_workorders")
    .select(
        clean("WOID").alias("WOID"),
        clean("FleetID").alias("FleetID"),
        clean("Type").alias("WorkOrderTypeCode"),
        F.to_timestamp("Start").alias("StartTimestamp"),
        F.to_timestamp("End").alias("EndTimestamp"),
        clean("CauseCode").alias("CauseCode"),
    )
    .withColumn("StartDate", F.to_date("StartTimestamp"))
    .withColumn("EndDate", F.to_date("EndTimestamp"))
    .withColumn(
        "WorkOrderType",
        F.when(F.col("WorkOrderTypeCode") == "CM", F.lit("Corrective Maintenance"))
        .when(F.col("WorkOrderTypeCode") == "PM", F.lit("Preventive Maintenance"))
        .otherwise(F.col("WorkOrderTypeCode")),
    )
    .withColumn("TurnaroundHours", (F.unix_timestamp("EndTimestamp") - F.unix_timestamp("StartTimestamp")) / 3600)
)
save_table(silver_workorders, "silver_maintenance_workorders")


# COMMAND ----------

# Gold: dimensions and facts

save_table(spark.table("silver_calendar"), "dim_calendar")
save_table(spark.table("silver_regions"), "dim_region")

dim_depot = (
    spark.table("silver_depots").alias("d")
    .join(spark.table("silver_regions").alias("r"), "RegionID", "left")
    .select("d.DepotID", "d.DepotName", "d.RegionID", "r.RegionName")
)
save_table(dim_depot, "dim_depot")

dim_fleet_unit = (
    spark.table("silver_fleet_units").alias("f")
    .join(spark.table("silver_depots").alias("d"), "DepotID", "left")
    .select("f.FleetID", "f.FleetType", "f.DepotID", "d.DepotName", "d.RegionID")
)
save_table(dim_fleet_unit, "dim_fleet_unit")

save_table(spark.table("silver_availability_snapshots"), "fact_availability_snapshot")
save_table(spark.table("silver_failures"), "fact_failure")
save_table(spark.table("silver_maintenance_workorders"), "fact_maintenance_workorder")


# COMMAND ----------

# Facilitator validation KPIs

availability_kpis = spark.table("fact_availability_snapshot").agg(
    F.count("*").alias("AvailabilitySnapshots"),
    F.round(F.avg(F.col("IsInService").cast("double")) * 100, 1).alias("AvailabilityPct"),
    F.round(F.avg("HoursInService"), 1).alias("AvgHoursInService"),
    F.sum(F.col("IsInvalidHoursInService").cast("int")).alias("InvalidHoursRows"),
)

failure_kpis = spark.table("fact_failure").agg(
    F.count("*").alias("Failures"),
    F.round(F.sum("DowntimeHours"), 1).alias("FailureDowntimeHours"),
    F.sum("DelayMinutes").alias("FailureDelayMinutes"),
)

workorder_kpis = spark.table("fact_maintenance_workorder").agg(
    F.count("*").alias("MaintenanceWorkOrders"),
    F.sum((F.col("WorkOrderTypeCode") == "CM").cast("int")).alias("CorrectiveMaintenance"),
    F.sum((F.col("WorkOrderTypeCode") == "PM").cast("int")).alias("PreventiveMaintenance"),
    F.round(F.avg("TurnaroundHours"), 1).alias("AvgMaintenanceTurnaroundHours"),
)

display(availability_kpis.crossJoin(failure_kpis).crossJoin(workorder_kpis))

display(
    spark.table("fact_failure")
    .groupBy("FailureType")
    .agg(F.count("*").alias("Failures"), F.round(F.sum("DowntimeHours"), 1).alias("DowntimeHours"))
    .orderBy(F.desc("Failures"))
)
