# Fabric notebook: Track Possessions medallion build
#
# Upload track_possessions CSVs plus shared calendar.csv to Files/Raw.
# Use Gold tables in the semantic model.

from pyspark.sql import functions as F
from pyspark.sql import types as T


RAW_PATH = "Files/Raw"
CSV_FILES = {
    "calendar": "calendar.csv",
    "possessions": "possessions.csv",
    "impacts": "impacts.csv",
    "contractors": "contractors.csv",
    "locations": "locations.csv",
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
    spark.table("bronze_contractors").select(
        clean("ContractorID").alias("ContractorID"),
        clean("ContractorName").alias("ContractorName"),
    ),
    "silver_contractors",
)

save_table(
    spark.table("bronze_locations").select(
        clean("LocationID").alias("LocationID"),
        clean("LocationName").alias("LocationName"),
        clean("RegionID").alias("RegionID"),
    ),
    "silver_locations",
)

silver_possessions = (
    spark.table("bronze_possessions")
    .select(
        clean("PossessionID").alias("PossessionID"),
        clean("LocationID").alias("LocationID"),
        clean("Type").alias("PossessionType"),
        F.to_timestamp("PlannedStart").alias("PlannedStart"),
        F.to_timestamp("PlannedEnd").alias("PlannedEnd"),
        F.to_timestamp("ActualStart").alias("ActualStart"),
        F.to_timestamp("ActualEnd").alias("ActualEnd"),
        clean("ContractorID").alias("ContractorID"),
        clean("Reason").alias("Reason"),
        clean("RegionID").alias("RegionRouteHint"),
    )
    .withColumn("PlannedStartDate", F.to_date("PlannedStart"))
    .withColumn("PlannedDurationMinutes", (F.unix_timestamp("PlannedEnd") - F.unix_timestamp("PlannedStart")) / 60)
    .withColumn("ActualDurationMinutes", (F.unix_timestamp("ActualEnd") - F.unix_timestamp("ActualStart")) / 60)
    .withColumn("OverrunMinutes", F.col("ActualDurationMinutes") - F.col("PlannedDurationMinutes"))
    .withColumn("IsOverrun", F.col("OverrunMinutes") > 0)
)
save_table(silver_possessions, "silver_possessions")

save_table(
    spark.table("bronze_impacts").select(
        clean("PossessionID").alias("PossessionID"),
        F.col("ServicesImpacted").cast(T.IntegerType()).alias("ServicesImpacted"),
        F.col("DelayMinutes").cast(T.IntegerType()).alias("DelayMinutes"),
        F.col("Cancellations").cast(T.IntegerType()).alias("Cancellations"),
    ),
    "silver_impacts",
)


# COMMAND ----------

# Gold: dimensions and facts

save_table(spark.table("silver_calendar"), "dim_calendar")
save_table(spark.table("silver_regions"), "dim_region")
save_table(spark.table("silver_contractors"), "dim_contractor")

dim_location = (
    spark.table("silver_locations").alias("l")
    .join(spark.table("silver_regions").alias("r"), "RegionID", "left")
    .select("l.LocationID", "l.LocationName", "l.RegionID", "r.RegionName")
)
save_table(dim_location, "dim_location")

fact_possession = (
    spark.table("silver_possessions").alias("p")
    .join(spark.table("silver_locations").select("LocationID", F.col("RegionID").alias("LocationRegionID")), "LocationID", "left")
    .withColumn("RegionHintMismatch", F.col("RegionRouteHint") != F.col("LocationRegionID"))
    .drop("LocationRegionID")
)
save_table(fact_possession, "fact_possession")
save_table(spark.table("silver_impacts"), "fact_impact")


# COMMAND ----------

# Facilitator validation KPIs

track_kpis = fact_possession.agg(
    F.count("*").alias("TotalPossessions"),
    F.sum(F.col("IsOverrun").cast("int")).alias("OverrunningPossessions"),
    F.round(F.avg(F.col("IsOverrun").cast("double")) * 100, 1).alias("OverrunRatePct"),
    F.round(F.avg("OverrunMinutes"), 1).alias("AvgOverrunMinutes"),
)

impact_kpis = spark.table("fact_impact").agg(
    F.sum("ServicesImpacted").alias("ServicesImpacted"),
    F.sum("DelayMinutes").alias("DelayMinutes"),
    F.sum("Cancellations").alias("Cancellations"),
)

display(track_kpis.crossJoin(impact_kpis))

display(
    fact_possession
    .groupBy("PossessionType")
    .agg(F.round(F.avg("OverrunMinutes"), 1).alias("AvgOverrunMinutes"), F.sum(F.col("IsOverrun").cast("int")).alias("Overruns"))
    .orderBy(F.desc("AvgOverrunMinutes"))
)
