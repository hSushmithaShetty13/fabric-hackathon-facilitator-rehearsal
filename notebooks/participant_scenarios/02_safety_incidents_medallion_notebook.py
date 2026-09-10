# Fabric notebook: Safety Incidents medallion build
#
# Upload safety_incidents CSVs plus shared calendar.csv to Files/Raw.
# Use Gold tables in the semantic model.

from pyspark.sql import functions as F
from pyspark.sql import types as T


RAW_PATH = "Files/Raw"
CSV_FILES = {
    "calendar": "calendar.csv",
    "incidents": "incidents.csv",
    "corrective_actions": "corrective_actions.csv",
    "locations": "locations.csv",
    "hours_worked": "hours_worked.csv",
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
    spark.table("bronze_locations").select(
        clean("LocationID").alias("LocationID"),
        clean("LocationName").alias("LocationName"),
        clean("LocationType").alias("LocationType"),
        clean("RegionID").alias("RegionID"),
    ),
    "silver_locations",
)

silver_incidents = (
    spark.table("bronze_incidents")
    .select(
        clean("IncidentID").alias("IncidentID"),
        F.to_date("Date").alias("Date"),
        clean("Time").alias("Time"),
        clean("LocationID").alias("LocationID"),
        clean("IncidentType").alias("IncidentType"),
        clean("Severity").alias("Severity"),
        clean("Department").alias("Department"),
        clean("Cause").alias("Cause"),
        F.to_date("ClosedDate").alias("ClosedDate"),
    )
    .withColumn("IncidentTimestamp", F.to_timestamp(F.concat_ws(" ", F.col("Date").cast("string"), F.col("Time"))))
    .withColumn("IsOpenIncident", F.col("ClosedDate").isNull())
    .withColumn("DaysToClose", F.when(F.col("ClosedDate").isNotNull(), F.datediff("ClosedDate", "Date")))
)
save_table(silver_incidents, "silver_incidents")

silver_corrective_actions = (
    spark.table("bronze_corrective_actions")
    .select(
        clean("ActionID").alias("ActionID"),
        clean("IncidentID").alias("IncidentID"),
        clean("ActionType").alias("ActionType"),
        clean("Owner").alias("Owner"),
        F.to_date("DueDate").alias("DueDate"),
        F.to_date("CompletedDate").alias("CompletedDate"),
    )
    .withColumn("IsCompleted", F.col("CompletedDate").isNotNull())
    .withColumn("CompletedOnTime", F.col("CompletedDate").isNotNull() & (F.col("CompletedDate") <= F.col("DueDate")))
    .withColumn("DaysLate", F.when(F.col("CompletedDate").isNotNull(), F.datediff("CompletedDate", "DueDate")))
)
save_table(silver_corrective_actions, "silver_corrective_actions")

save_table(
    spark.table("bronze_hours_worked").select(
        clean("Month").alias("Month"),
        F.to_date(F.concat(clean("Month"), F.lit("-01"))).alias("MonthStartDate"),
        clean("Department").alias("Department"),
        F.col("WorkedHours").cast(T.DoubleType()).alias("WorkedHours"),
    ),
    "silver_hours_worked",
)


# COMMAND ----------

# Gold: dimensions and facts

save_table(spark.table("silver_calendar"), "dim_calendar")
save_table(spark.table("silver_regions"), "dim_region")

dim_location = (
    spark.table("silver_locations").alias("l")
    .join(spark.table("silver_regions").alias("r"), "RegionID", "left")
    .select("l.LocationID", "l.LocationName", "l.LocationType", "l.RegionID", "r.RegionName")
)
save_table(dim_location, "dim_location")

dim_department = (
    spark.table("silver_incidents").select("Department")
    .unionByName(spark.table("silver_hours_worked").select("Department"))
    .distinct()
)
save_table(dim_department, "dim_department")

save_table(spark.table("silver_incidents"), "fact_incident")
save_table(spark.table("silver_corrective_actions"), "fact_corrective_action")
save_table(spark.table("silver_hours_worked"), "fact_hours_worked")


# COMMAND ----------

# Facilitator validation KPIs

safety_kpis = spark.table("fact_incident").agg(
    F.count("*").alias("TotalIncidents"),
    F.sum(F.col("IsOpenIncident").cast("int")).alias("OpenIncidents"),
    F.round(F.avg("DaysToClose"), 1).alias("AvgDaysToClose"),
)

action_kpis = spark.table("fact_corrective_action").agg(
    F.count("*").alias("CorrectiveActions"),
    F.sum(F.col("IsCompleted").cast("int")).alias("CompletedCorrectiveActions"),
    F.round(F.avg(F.when(F.col("IsCompleted"), F.col("CompletedOnTime").cast("double"))) * 100, 1).alias("CorrectiveActionOnTimePct"),
)

display(safety_kpis.crossJoin(action_kpis))

display(
    spark.table("fact_incident")
    .groupBy("Department")
    .agg(F.count("*").alias("Incidents"))
    .orderBy(F.desc("Incidents"))
)
