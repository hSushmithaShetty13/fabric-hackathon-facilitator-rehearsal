# Fabric notebook: Rail Performance medallion build
#
# Upload rail_performance CSVs plus shared calendar.csv to Files/Raw.
# Use Gold tables in the semantic model.

from pyspark.sql import functions as F
from pyspark.sql import types as T


RAW_PATH = "Files/Raw"
CSV_FILES = {
    "calendar": "calendar.csv",
    "services": "services.csv",
    "delay_events": "delay_events.csv",
    "cancellations": "cancellations.csv",
    "routes": "routes.csv",
    "operators": "operators.csv",
    "regions": "regions.csv",
}


def read_csv(file_name: str):
    return spark.read.option("header", "true").option("inferSchema", "false").csv(f"{RAW_PATH}/{file_name}")


def save_table(df, table_name: str):
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)


def clean(column_name: str):
    return F.trim(F.col(column_name))


def title_case(column_name: str):
    return F.initcap(F.lower(F.trim(F.col(column_name))))


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
    spark.table("bronze_routes").select(
        clean("RouteID").alias("RouteID"),
        clean("RouteName").alias("RouteName"),
        clean("RegionID").alias("RegionID"),
    ),
    "silver_routes",
)

save_table(
    spark.table("bronze_operators").select(
        clean("OperatorID").alias("OperatorID"),
        title_case("Operator").alias("OperatorName"),
    ),
    "silver_operators",
)

silver_services = (
    spark.table("bronze_services")
    .select(
        clean("ServiceID").alias("ServiceID"),
        clean("RouteID").alias("RouteID"),
        clean("OperatorID").alias("OperatorID"),
        F.to_timestamp("ScheduledDeparture").alias("ScheduledDeparture"),
        F.to_timestamp("ActualDeparture").alias("ActualDeparture"),
        F.to_timestamp("ScheduledArrival").alias("ScheduledArrival"),
        F.to_timestamp("ActualArrival").alias("ActualArrival"),
        F.to_date("Date").alias("Date"),
        clean("RegionRouteHint").alias("RegionRouteHint"),
        F.col("IsCancelled").cast(T.BooleanType()).alias("IsCancelled"),
    )
    .withColumn("ArrivalDelayMinutes", (F.unix_timestamp("ActualArrival") - F.unix_timestamp("ScheduledArrival")) / 60)
    .withColumn("DepartureDelayMinutes", (F.unix_timestamp("ActualDeparture") - F.unix_timestamp("ScheduledDeparture")) / 60)
    .withColumn("OnTimeWithin5Minutes", (~F.col("IsCancelled")) & (F.col("ArrivalDelayMinutes") <= 5))
)
save_table(silver_services, "silver_services")

save_table(
    spark.table("bronze_delay_events").select(
        clean("EventID").alias("EventID"),
        clean("ServiceID").alias("ServiceID"),
        clean("Reason").alias("Reason"),
        clean("ReasonGroup").alias("ReasonGroup"),
        F.col("DelayMinutes").cast(T.IntegerType()).alias("DelayMinutes"),
    ),
    "silver_delay_events",
)

save_table(
    spark.table("bronze_cancellations").select(
        clean("ServiceID").alias("ServiceID"),
        clean("CancelType").alias("CancelType"),
        clean("CancelReason").alias("CancelReason"),
    ),
    "silver_cancellations",
)


# COMMAND ----------

# Gold: dimensions and facts

save_table(spark.table("silver_calendar"), "dim_calendar")
save_table(spark.table("silver_regions"), "dim_region")
save_table(spark.table("silver_operators"), "dim_operator")

dim_route = (
    spark.table("silver_routes").alias("r")
    .join(spark.table("silver_regions").alias("g"), "RegionID", "left")
    .select("r.RouteID", "r.RouteName", "r.RegionID", "g.RegionName")
)
save_table(dim_route, "dim_route")

fact_service = (
    spark.table("silver_services").alias("s")
    .join(spark.table("silver_routes").select("RouteID", F.col("RegionID").alias("RouteRegionID")), "RouteID", "left")
    .withColumn("RegionHintMismatch", F.col("RegionRouteHint") != F.col("RouteRegionID"))
    .drop("RouteRegionID")
)
save_table(fact_service, "fact_service")
save_table(spark.table("silver_delay_events"), "fact_delay_event")
save_table(spark.table("silver_cancellations"), "fact_cancellation")


# COMMAND ----------

# Facilitator validation KPIs

rail_kpis = fact_service.agg(
    F.count("*").alias("TotalServices"),
    F.sum(F.col("IsCancelled").cast("int")).alias("CancelledServices"),
    F.round(F.avg(F.when(~F.col("IsCancelled"), F.col("OnTimeWithin5Minutes").cast("double"))) * 100, 1).alias("OnTimePct"),
    F.round(F.avg(F.when(~F.col("IsCancelled"), F.col("ArrivalDelayMinutes"))), 1).alias("AvgArrivalDelayMinutes"),
    F.sum(F.col("RegionHintMismatch").cast("int")).alias("RegionHintMismatchRows"),
)

delay_kpis = spark.table("fact_delay_event").agg(
    F.count("*").alias("DelayEvents"),
    F.sum("DelayMinutes").alias("TotalDelayMinutes"),
)

display(rail_kpis.crossJoin(delay_kpis))

display(
    spark.table("fact_delay_event")
    .groupBy("ReasonGroup")
    .agg(F.sum("DelayMinutes").alias("DelayMinutes"))
    .orderBy(F.desc("DelayMinutes"))
)
