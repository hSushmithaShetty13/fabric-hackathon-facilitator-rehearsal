# Fabric notebook: Station Operations medallion build
#
# Lakehouse: lh_station_ops
# Expected files: upload all CSVs to Files/Raw in the attached Lakehouse.
# Output tables:
# - Bronze: bronze_*
# - Silver: silver_*
# - Gold: fact_station_day, fact_assistance_request, fact_asset_workorder,
#         dim_station, dim_region, dim_calendar, dim_tariff

from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window


RAW_PATH = "Files/Raw"

CSV_FILES = {
    "calendar": "calendar.csv",
    "regions": "regions.csv",
    "stations": "stations.csv",
    "tariffs": "tariffs.csv",
    "station_daily": "station_daily.csv",
    "assistance_requests": "assistance_requests.csv",
    "asset_workorders": "asset_workorders.csv",
}


def read_raw_csv(file_name: str):
    return (
        spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .csv(f"{RAW_PATH}/{file_name}")
    )


def overwrite_table(df, table_name: str):
    (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )


def clean_string(column_name: str):
    return F.trim(F.col(column_name))


def title_case(column_name: str):
    return F.initcap(F.lower(F.trim(F.col(column_name))))


# COMMAND ----------

# Bronze layer: raw CSVs as landed

for table_name, file_name in CSV_FILES.items():
    bronze_df = (
        read_raw_csv(file_name)
        .withColumn("_source_file", F.lit(file_name))
        .withColumn("_ingested_at_utc", F.current_timestamp())
    )
    overwrite_table(bronze_df, f"bronze_{table_name}")


# COMMAND ----------

# Silver layer: cleaned, typed tables

silver_calendar = (
    spark.table("bronze_calendar")
    .select(
        F.to_date("Date").alias("Date"),
        F.col("Year").cast(T.IntegerType()).alias("Year"),
        F.col("Month").cast(T.IntegerType()).alias("Month"),
        clean_string("MonthName").alias("MonthName"),
        F.to_date("WeekStartDate").alias("WeekStartDate"),
        clean_string("DayName").alias("DayName"),
        F.col("IsWeekend").cast(T.BooleanType()).alias("IsWeekend"),
    )
)
overwrite_table(silver_calendar, "silver_calendar")

silver_regions = (
    spark.table("bronze_regions")
    .select(
        clean_string("RegionID").alias("RegionID"),
        clean_string("RegionName").alias("RegionName"),
        clean_string("OperationsDirector").alias("OperationsDirector"),
    )
)
overwrite_table(silver_regions, "silver_regions")

silver_stations = (
    spark.table("bronze_stations")
    .select(
        clean_string("StationID").alias("StationID"),
        title_case("StationName").alias("StationName"),
        clean_string("RegionID").alias("RegionID"),
        title_case("StationType").alias("StationType"),
        clean_string("AccessibilityTier").alias("AccessibilityTier"),
        clean_string("ManagedBy").alias("ManagedBy"),
    )
)
overwrite_table(silver_stations, "silver_stations")

silver_tariffs = (
    spark.table("bronze_tariffs")
    .select(
        clean_string("TariffBand").alias("TariffBand"),
        F.col("RatePerKwh").cast(T.DoubleType()).alias("RatePerKwh"),
        F.col("StandingChargePerDay").cast(T.DoubleType()).alias("StandingChargePerDay"),
        clean_string("AppliesTo").alias("AppliesTo"),
    )
)
overwrite_table(silver_tariffs, "silver_tariffs")

silver_station_daily = (
    spark.table("bronze_station_daily")
    .select(
        F.to_date("Date").alias("Date"),
        clean_string("StationID").alias("StationID"),
        F.col("PassengerCount").cast(T.IntegerType()).alias("PassengerCount"),
        F.col("EnergyKwh").cast(T.DoubleType()).alias("EnergyKwh"),
        title_case("WeatherDescription").alias("WeatherDescription"),
        F.col("TemperatureC").cast(T.DoubleType()).alias("TemperatureC"),
        clean_string("TariffBand").alias("TariffBand"),
        clean_string("MeterReadQuality").alias("MeterReadQuality"),
    )
    .withColumn("IsNegativePassengerCount", F.col("PassengerCount") < 0)
    .withColumn("IsInvalidEnergy", F.col("EnergyKwh") <= 0)
    .withColumn(
        "WeatherBand",
        F.when(F.lower(F.col("WeatherDescription")).contains("rain"), F.lit("Rain"))
        .when(F.lower(F.col("WeatherDescription")).contains("hot"), F.lit("Hot"))
        .when(F.lower(F.col("WeatherDescription")).contains("cold"), F.lit("Cold"))
        .otherwise(F.col("WeatherDescription")),
    )
)
overwrite_table(silver_station_daily, "silver_station_daily")

silver_assistance_requests = (
    spark.table("bronze_assistance_requests")
    .select(
        F.to_date("Date").alias("Date"),
        clean_string("StationID").alias("StationID"),
        clean_string("RequestType").alias("RequestType"),
        F.col("RequestCount").cast(T.IntegerType()).alias("RequestCount"),
        F.col("FulfilledWithinSla").cast(T.IntegerType()).alias("FulfilledWithinSla"),
        F.to_timestamp("OpenedTimestamp").alias("OpenedTimestamp"),
        F.to_timestamp("ClosedTimestamp").alias("ClosedTimestamp"),
        F.col("SlaMinutes").cast(T.IntegerType()).alias("SlaMinutes"),
    )
    .withColumn("IsOpenRequest", F.col("ClosedTimestamp").isNull())
    .withColumn("IsImpossibleSlaCount", F.col("FulfilledWithinSla") > F.col("RequestCount"))
    .withColumn(
        "SlaFulfilmentRate",
        F.when(F.col("RequestCount") > 0, F.col("FulfilledWithinSla") / F.col("RequestCount")),
    )
)
overwrite_table(silver_assistance_requests, "silver_assistance_requests")

silver_asset_workorders = (
    spark.table("bronze_asset_workorders")
    .select(
        clean_string("WorkOrderID").alias("WorkOrderID"),
        clean_string("StationID").alias("StationID"),
        clean_string("AssetType").alias("AssetType"),
        clean_string("Priority").alias("Priority"),
        F.to_date("OpenedDate").alias("OpenedDate"),
        F.to_date("TargetDate").alias("TargetDate"),
        F.to_date("CompletedDate").alias("CompletedDate"),
        F.col("EstimatedCost").cast(T.DoubleType()).alias("EstimatedCost"),
    )
    .withColumn("IsOpenWorkOrder", F.col("CompletedDate").isNull())
    .withColumn(
        "IsOverdue",
        F.col("CompletedDate").isNull() & (F.col("TargetDate") < F.current_date()),
    )
    .withColumn(
        "DaysToComplete",
        F.when(
            F.col("CompletedDate").isNotNull(),
            F.datediff(F.col("CompletedDate"), F.col("OpenedDate")),
        ),
    )
)
overwrite_table(silver_asset_workorders, "silver_asset_workorders")


# COMMAND ----------

# Data quality checks

valid_station_ids = silver_stations.select("StationID").distinct()

station_daily_quality = (
    silver_station_daily
    .join(valid_station_ids.withColumn("ValidStationID", F.col("StationID")), "StationID", "left")
    .withColumn("IsUnknownStation", F.col("ValidStationID").isNull())
    .drop("ValidStationID")
)
overwrite_table(station_daily_quality, "silver_station_daily_quality")

quality_summary = (
    station_daily_quality
    .agg(
        F.count("*").alias("StationDailyRows"),
        F.sum(F.col("IsUnknownStation").cast("int")).alias("UnknownStationRows"),
        F.sum(F.col("IsNegativePassengerCount").cast("int")).alias("NegativePassengerRows"),
        F.sum(F.col("IsInvalidEnergy").cast("int")).alias("InvalidEnergyRows"),
    )
    .crossJoin(
        silver_assistance_requests.agg(
            F.count("*").alias("AssistanceRows"),
            F.sum(F.col("IsImpossibleSlaCount").cast("int")).alias("ImpossibleSlaRows"),
            F.sum(F.col("IsOpenRequest").cast("int")).alias("OpenAssistanceRows"),
        )
    )
    .crossJoin(
        silver_asset_workorders.agg(
            F.count("*").alias("WorkOrderRows"),
            F.sum(F.col("IsOpenWorkOrder").cast("int")).alias("OpenWorkOrders"),
            F.sum(F.col("IsOverdue").cast("int")).alias("OverdueWorkOrders"),
        )
    )
)
overwrite_table(quality_summary, "data_quality_summary")

display(quality_summary)


# COMMAND ----------

# Gold layer: dimensions

dim_calendar = spark.table("silver_calendar")
overwrite_table(dim_calendar, "dim_calendar")

dim_region = spark.table("silver_regions")
overwrite_table(dim_region, "dim_region")

dim_tariff = spark.table("silver_tariffs")
overwrite_table(dim_tariff, "dim_tariff")

dim_station = (
    spark.table("silver_stations").alias("s")
    .join(spark.table("silver_regions").alias("r"), "RegionID", "left")
    .select(
        "s.StationID",
        "s.StationName",
        "s.RegionID",
        "r.RegionName",
        "r.OperationsDirector",
        "s.StationType",
        "s.AccessibilityTier",
        "s.ManagedBy",
    )
)
overwrite_table(dim_station, "dim_station")


# COMMAND ----------

# Gold layer: facts

fact_station_day = (
    spark.table("silver_station_daily_quality").alias("d")
    .join(spark.table("silver_tariffs").alias("t"), "TariffBand", "left")
    .select(
        "d.Date",
        "d.StationID",
        "d.PassengerCount",
        "d.EnergyKwh",
        "d.WeatherDescription",
        "d.WeatherBand",
        "d.TemperatureC",
        "d.TariffBand",
        "d.MeterReadQuality",
        "d.IsUnknownStation",
        "d.IsNegativePassengerCount",
        "d.IsInvalidEnergy",
        "t.RatePerKwh",
        "t.StandingChargePerDay",
    )
    .withColumn("EstimatedEnergyCost", F.col("EnergyKwh") * F.col("RatePerKwh"))
    .withColumn(
        "EnergyPerThousandPassengers",
        F.when(F.col("PassengerCount") > 0, F.col("EnergyKwh") / F.col("PassengerCount") * 1000),
    )
    .withColumn(
        "HasDataQualityIssue",
        F.col("IsUnknownStation") | F.col("IsNegativePassengerCount") | F.col("IsInvalidEnergy"),
    )
)
overwrite_table(fact_station_day, "fact_station_day")

fact_assistance_request = spark.table("silver_assistance_requests")
overwrite_table(fact_assistance_request, "fact_assistance_request")

fact_asset_workorder = spark.table("silver_asset_workorders")
overwrite_table(fact_asset_workorder, "fact_asset_workorder")


# COMMAND ----------

# Gold layer: intervention score for the final report

station_energy = (
    fact_station_day
    .groupBy("StationID")
    .agg(
        F.sum("EstimatedEnergyCost").alias("TotalEnergyCost"),
        F.sum("EnergyKwh").alias("TotalEnergyKwh"),
        F.sum("PassengerCount").alias("TotalPassengers"),
        F.avg("EnergyPerThousandPassengers").alias("AvgEnergyPerThousandPassengers"),
        F.sum(F.col("HasDataQualityIssue").cast("int")).alias("DataQualityIssueRows"),
    )
)

station_assistance = (
    fact_assistance_request
    .groupBy("StationID")
    .agg(
        F.sum("RequestCount").alias("AssistanceRequests"),
        F.sum("FulfilledWithinSla").alias("FulfilledWithinSla"),
        F.sum(F.col("IsOpenRequest").cast("int")).alias("OpenRequests"),
        F.sum(F.col("IsImpossibleSlaCount").cast("int")).alias("ImpossibleSlaRows"),
    )
    .withColumn(
        "SlaFulfilmentRate",
        F.when(F.col("AssistanceRequests") > 0, F.col("FulfilledWithinSla") / F.col("AssistanceRequests")),
    )
)

station_workorders = (
    fact_asset_workorder
    .groupBy("StationID")
    .agg(
        F.count("*").alias("WorkOrders"),
        F.sum(F.col("IsOpenWorkOrder").cast("int")).alias("OpenWorkOrders"),
        F.sum(F.col("IsOverdue").cast("int")).alias("OverdueWorkOrders"),
        F.sum("EstimatedCost").alias("EstimatedWorkOrderCost"),
    )
)

score_base = (
    dim_station
    .join(station_energy, "StationID", "left")
    .join(station_assistance, "StationID", "left")
    .join(station_workorders, "StationID", "left")
    .fillna(
        {
            "TotalEnergyCost": 0.0,
            "TotalEnergyKwh": 0.0,
            "TotalPassengers": 0,
            "AvgEnergyPerThousandPassengers": 0.0,
            "DataQualityIssueRows": 0,
            "AssistanceRequests": 0,
            "FulfilledWithinSla": 0,
            "OpenRequests": 0,
            "ImpossibleSlaRows": 0,
            "SlaFulfilmentRate": 1.0,
            "WorkOrders": 0,
            "OpenWorkOrders": 0,
            "OverdueWorkOrders": 0,
            "EstimatedWorkOrderCost": 0.0,
        }
    )
)

max_values = score_base.agg(
    F.max("TotalEnergyCost").alias("MaxEnergyCost"),
    F.max("AvgEnergyPerThousandPassengers").alias("MaxEnergyPerThousandPassengers"),
    F.max("AssistanceRequests").alias("MaxAssistanceRequests"),
    F.max("OpenWorkOrders").alias("MaxOpenWorkOrders"),
).collect()[0]

max_energy_cost = max_values["MaxEnergyCost"] or 1
max_energy_intensity = max_values["MaxEnergyPerThousandPassengers"] or 1
max_assistance = max_values["MaxAssistanceRequests"] or 1
max_open_workorders = max_values["MaxOpenWorkOrders"] or 1

gold_station_intervention_score = (
    score_base
    .withColumn("EnergyCostScore", F.col("TotalEnergyCost") / F.lit(max_energy_cost))
    .withColumn("EnergyIntensityScore", F.col("AvgEnergyPerThousandPassengers") / F.lit(max_energy_intensity))
    .withColumn("AssistanceDemandScore", F.col("AssistanceRequests") / F.lit(max_assistance))
    .withColumn("SlaRiskScore", 1 - F.col("SlaFulfilmentRate"))
    .withColumn("WorkOrderRiskScore", F.col("OpenWorkOrders") / F.lit(max_open_workorders))
    .withColumn("DataQualityScore", F.when(F.col("DataQualityIssueRows") > 0, F.lit(0.15)).otherwise(F.lit(0.0)))
    .withColumn(
        "InterventionScore",
        F.round(
            100
            * (
                F.col("EnergyCostScore") * 0.20
                + F.col("EnergyIntensityScore") * 0.20
                + F.col("AssistanceDemandScore") * 0.20
                + F.col("SlaRiskScore") * 0.20
                + F.col("WorkOrderRiskScore") * 0.15
                + F.col("DataQualityScore") * 0.05
            ),
            1,
        ),
    )
    .withColumn(
        "PrimaryReason",
        F.when(F.col("EnergyIntensityScore") >= 0.85, F.lit("High energy per passenger"))
        .when(F.col("SlaRiskScore") >= 0.20, F.lit("Low assistance SLA fulfilment"))
        .when(F.col("WorkOrderRiskScore") >= 0.50, F.lit("Open asset work orders"))
        .when(F.col("AssistanceDemandScore") >= 0.75, F.lit("High assistance demand"))
        .when(F.col("DataQualityIssueRows") > 0, F.lit("Data quality concern"))
        .otherwise(F.lit("Balanced operational pressure")),
    )
    .withColumn("Rank", F.dense_rank().over(Window.orderBy(F.desc("InterventionScore"))))
)

overwrite_table(gold_station_intervention_score, "gold_station_intervention_score")

display(
    gold_station_intervention_score
    .orderBy(F.desc("InterventionScore"))
    .select(
        "Rank",
        "StationName",
        "RegionName",
        "InterventionScore",
        "PrimaryReason",
        "TotalEnergyCost",
        "AvgEnergyPerThousandPassengers",
        "SlaFulfilmentRate",
        "OpenWorkOrders",
        "DataQualityIssueRows",
    )
)


# COMMAND ----------

# Final expected demo output: top three stations to investigate first

top_three_stations = (
    spark.table("gold_station_intervention_score")
    .where(F.col("Rank") <= 3)
    .orderBy("Rank")
    .select(
        "Rank",
        "StationName",
        "RegionName",
        "InterventionScore",
        "PrimaryReason",
        "TotalEnergyCost",
        "AssistanceRequests",
        "SlaFulfilmentRate",
        "OpenWorkOrders",
    )
)

display(top_three_stations)
