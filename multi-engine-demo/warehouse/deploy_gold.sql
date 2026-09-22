IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'gold') EXEC('CREATE SCHEMA gold');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'audit') EXEC('CREATE SCHEMA audit');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'etl') EXEC('CREATE SCHEMA etl');
GO

IF OBJECT_ID('gold.dim_date', 'U') IS NULL
CREATE TABLE gold.dim_date (
    calendar_date date NOT NULL,
    calendar_year int NULL,
    calendar_month int NULL,
    month_name varchar(20) NULL,
    week_start_date date NULL,
    day_name varchar(20) NULL,
    is_weekend bit NULL
);

IF OBJECT_ID('gold.dim_region', 'U') IS NULL
CREATE TABLE gold.dim_region (
    region_id varchar(20) NOT NULL,
    region_name varchar(100) NULL,
    operations_director varchar(100) NULL
);

IF OBJECT_ID('gold.dim_station', 'U') IS NULL
CREATE TABLE gold.dim_station (
    station_id varchar(20) NOT NULL,
    station_name varchar(150) NULL,
    region_id varchar(20) NULL,
    station_type varchar(50) NULL,
    accessibility_tier varchar(20) NULL,
    managed_by varchar(100) NULL
);

IF OBJECT_ID('gold.dim_tariff', 'U') IS NULL
CREATE TABLE gold.dim_tariff (
    tariff_band varchar(30) NOT NULL,
    rate_per_kwh decimal(18,4) NULL,
    standing_charge_per_day decimal(18,4) NULL,
    applies_to varchar(250) NULL
);

IF OBJECT_ID('gold.fact_station_daily', 'U') IS NULL
CREATE TABLE gold.fact_station_daily (
    activity_date date NOT NULL,
    station_id varchar(20) NOT NULL,
    passenger_count bigint NULL,
    energy_kwh decimal(18,3) NULL,
    weather_description varchar(100) NULL,
    temperature_c decimal(10,2) NULL,
    tariff_band varchar(30) NULL,
    meter_read_quality varchar(30) NULL,
    source_batch_id varchar(64) NULL,
    loaded_at_utc datetime2(6) NOT NULL
);

IF OBJECT_ID('gold.fact_assistance_request', 'U') IS NULL
CREATE TABLE gold.fact_assistance_request (
    activity_date date NOT NULL,
    station_id varchar(20) NOT NULL,
    request_type varchar(100) NULL,
    request_count bigint NULL,
    fulfilled_within_sla bigint NULL,
    opened_timestamp datetime2(6) NULL,
    closed_timestamp datetime2(6) NULL,
    sla_minutes int NULL,
    source_batch_id varchar(64) NULL,
    loaded_at_utc datetime2(6) NOT NULL
);

IF OBJECT_ID('gold.fact_asset_workorder', 'U') IS NULL
CREATE TABLE gold.fact_asset_workorder (
    workorder_id varchar(30) NOT NULL,
    station_id varchar(20) NOT NULL,
    asset_type varchar(100) NULL,
    priority varchar(30) NULL,
    opened_date date NULL,
    target_date date NULL,
    completed_date date NULL,
    estimated_cost decimal(18,2) NULL,
    source_batch_id varchar(64) NULL,
    loaded_at_utc datetime2(6) NOT NULL
);

IF OBJECT_ID('audit.pipeline_run', 'U') IS NULL
CREATE TABLE audit.pipeline_run (
    run_id varchar(64) NOT NULL,
    pipeline_name varchar(100) NOT NULL,
    status varchar(20) NOT NULL,
    started_at_utc datetime2(6) NOT NULL,
    completed_at_utc datetime2(6) NULL,
    error_message varchar(4000) NULL
);

IF OBJECT_ID('audit.pipeline_step', 'U') IS NULL
CREATE TABLE audit.pipeline_step (
    run_id varchar(64) NOT NULL,
    step_name varchar(100) NOT NULL,
    status varchar(20) NOT NULL,
    source_rows bigint NULL,
    target_rows bigint NULL,
    rejected_rows bigint NULL,
    recorded_at_utc datetime2(6) NOT NULL,
    error_message varchar(4000) NULL
);

IF OBJECT_ID('audit.row_reconciliation', 'U') IS NULL
CREATE TABLE audit.row_reconciliation (
    run_id varchar(64) NOT NULL,
    entity_name varchar(100) NOT NULL,
    source_rows bigint NOT NULL,
    target_rows bigint NOT NULL,
    rejected_rows bigint NOT NULL,
    row_difference bigint NOT NULL,
    status varchar(20) NOT NULL,
    recorded_at_utc datetime2(6) NOT NULL
);

IF OBJECT_ID('audit.data_quality_result', 'U') IS NULL
CREATE TABLE audit.data_quality_result (
    run_id varchar(64) NOT NULL,
    entity_name varchar(100) NOT NULL,
    rule_name varchar(150) NOT NULL,
    severity varchar(20) NOT NULL,
    evaluated_rows bigint NOT NULL,
    failed_rows bigint NOT NULL,
    status varchar(20) NOT NULL,
    recorded_at_utc datetime2(6) NOT NULL
);
GO

CREATE OR ALTER PROCEDURE etl.usp_load_gold
    @run_id varchar(64)
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO audit.pipeline_run
        (run_id, pipeline_name, status, started_at_utc, completed_at_utc, error_message)
    VALUES
        (@run_id, 'pl_demo_end_to_end', 'RUNNING', SYSUTCDATETIME(), NULL, NULL);

    BEGIN TRY
        BEGIN TRANSACTION;

        TRUNCATE TABLE gold.fact_station_daily;
        TRUNCATE TABLE gold.fact_assistance_request;
        TRUNCATE TABLE gold.fact_asset_workorder;
        TRUNCATE TABLE gold.dim_station;
        TRUNCATE TABLE gold.dim_region;
        TRUNCATE TABLE gold.dim_tariff;
        TRUNCATE TABLE gold.dim_date;

        INSERT INTO gold.dim_date
            (calendar_date, calendar_year, calendar_month, month_name, week_start_date, day_name, is_weekend)
        SELECT [Date], [Year], [Month], MonthName, WeekStartDate, DayName, IsWeekend
        FROM [lh_dataflow_silver].[dbo].[silver_calendar]
        WHERE dq_is_valid = 1;

        INSERT INTO gold.dim_region (region_id, region_name, operations_director)
        SELECT RegionID, RegionName, OperationsDirector
        FROM [lh_dataflow_silver].[dbo].[silver_regions]
        WHERE dq_is_valid = 1;

        INSERT INTO gold.dim_station
            (station_id, station_name, region_id, station_type, accessibility_tier, managed_by)
        SELECT StationID, StationName, RegionID, StationType, AccessibilityTier, ManagedBy
        FROM [lh_dataflow_silver].[dbo].[silver_stations]
        WHERE dq_is_valid = 1;

        INSERT INTO gold.dim_tariff
            (tariff_band, rate_per_kwh, standing_charge_per_day, applies_to)
        SELECT TariffBand, RatePerKwh, StandingChargePerDay, AppliesTo
        FROM [lh_dataflow_silver].[dbo].[silver_tariffs]
        WHERE dq_is_valid = 1;

        INSERT INTO gold.fact_station_daily
            (activity_date, station_id, passenger_count, energy_kwh, weather_description,
             temperature_c, tariff_band, meter_read_quality, source_batch_id, loaded_at_utc)
        SELECT d.[Date], d.StationID, d.PassengerCount, d.EnergyKwh, d.WeatherDescription,
               d.TemperatureC, d.TariffBand, d.MeterReadQuality, d._batch_id, SYSUTCDATETIME()
        FROM [lh_dataflow_silver].[dbo].[silver_station_daily] d
        WHERE d.dq_is_valid = 1
          AND EXISTS (SELECT 1 FROM gold.dim_station s WHERE s.station_id = d.StationID)
          AND EXISTS (SELECT 1 FROM gold.dim_tariff t WHERE t.tariff_band = d.TariffBand);

        INSERT INTO gold.fact_assistance_request
            (activity_date, station_id, request_type, request_count, fulfilled_within_sla,
             opened_timestamp, closed_timestamp, sla_minutes, source_batch_id, loaded_at_utc)
        SELECT a.[Date], a.StationID, a.RequestType, a.RequestCount, a.FulfilledWithinSla,
               a.OpenedTimestamp, a.ClosedTimestamp, a.SlaMinutes, a._batch_id, SYSUTCDATETIME()
        FROM [lh_dataflow_silver].[dbo].[silver_assistance_requests] a
        WHERE a.dq_is_valid = 1
          AND EXISTS (SELECT 1 FROM gold.dim_station s WHERE s.station_id = a.StationID);

        INSERT INTO gold.fact_asset_workorder
            (workorder_id, station_id, asset_type, priority, opened_date, target_date,
             completed_date, estimated_cost, source_batch_id, loaded_at_utc)
        SELECT w.WorkOrderID, w.StationID, w.AssetType, w.Priority, w.OpenedDate, w.TargetDate,
               w.CompletedDate, w.EstimatedCost, w._batch_id, SYSUTCDATETIME()
        FROM [lh_dataflow_silver].[dbo].[silver_asset_workorders] w
        WHERE w.dq_is_valid = 1
          AND EXISTS (SELECT 1 FROM gold.dim_station s WHERE s.station_id = w.StationID);

        DELETE FROM audit.pipeline_step WHERE run_id = @run_id;
        DELETE FROM audit.row_reconciliation WHERE run_id = @run_id;
        DELETE FROM audit.data_quality_result WHERE run_id = @run_id;

        INSERT INTO audit.pipeline_step
            (run_id, step_name, status, source_rows, target_rows, rejected_rows, recorded_at_utc, error_message)
        SELECT @run_id, entity_name, 'COMPLETED', source_rows, target_rows,
               source_rows - target_rows, SYSUTCDATETIME(), NULL
        FROM (
            SELECT 'calendar' entity_name,
                (SELECT COUNT_BIG(*) FROM [lh_dataflow_silver].[dbo].[silver_calendar]) source_rows,
                (SELECT COUNT_BIG(*) FROM gold.dim_date) target_rows
            UNION ALL SELECT 'regions',
                (SELECT COUNT_BIG(*) FROM [lh_dataflow_silver].[dbo].[silver_regions]),
                (SELECT COUNT_BIG(*) FROM gold.dim_region)
            UNION ALL SELECT 'stations',
                (SELECT COUNT_BIG(*) FROM [lh_dataflow_silver].[dbo].[silver_stations]),
                (SELECT COUNT_BIG(*) FROM gold.dim_station)
            UNION ALL SELECT 'tariffs',
                (SELECT COUNT_BIG(*) FROM [lh_dataflow_silver].[dbo].[silver_tariffs]),
                (SELECT COUNT_BIG(*) FROM gold.dim_tariff)
            UNION ALL SELECT 'station_daily',
                (SELECT COUNT_BIG(*) FROM [lh_dataflow_silver].[dbo].[silver_station_daily]),
                (SELECT COUNT_BIG(*) FROM gold.fact_station_daily)
            UNION ALL SELECT 'assistance_requests',
                (SELECT COUNT_BIG(*) FROM [lh_dataflow_silver].[dbo].[silver_assistance_requests]),
                (SELECT COUNT_BIG(*) FROM gold.fact_assistance_request)
            UNION ALL SELECT 'asset_workorders',
                (SELECT COUNT_BIG(*) FROM [lh_dataflow_silver].[dbo].[silver_asset_workorders]),
                (SELECT COUNT_BIG(*) FROM gold.fact_asset_workorder)
        ) counts;

        INSERT INTO audit.row_reconciliation
            (run_id, entity_name, source_rows, target_rows, rejected_rows, row_difference, status, recorded_at_utc)
        SELECT run_id, step_name, source_rows, target_rows, rejected_rows,
               source_rows - target_rows - rejected_rows,
               CASE WHEN source_rows = target_rows + rejected_rows THEN 'BALANCED' ELSE 'MISMATCH' END,
               SYSUTCDATETIME()
        FROM audit.pipeline_step
        WHERE run_id = @run_id;

        INSERT INTO audit.data_quality_result
            (run_id, entity_name, rule_name, severity, evaluated_rows, failed_rows, status, recorded_at_utc)
        SELECT @run_id, entity_name, rule_name, severity, evaluated_rows, failed_rows,
               CASE WHEN failed_rows = 0 THEN 'PASS' ELSE 'FAIL' END, SYSUTCDATETIME()
        FROM (
            SELECT 'stations' entity_name, 'Station row is structurally valid' rule_name, 'ERROR' severity,
                COUNT_BIG(*) evaluated_rows, COALESCE(SUM(CASE WHEN dq_is_valid = 0 THEN 1 ELSE 0 END), 0) failed_rows
            FROM [lh_dataflow_silver].[dbo].[silver_stations]
            UNION ALL SELECT 'station_daily', 'Passenger count is nonnegative', 'ERROR', COUNT_BIG(*),
                COALESCE(SUM(CASE WHEN PassengerCount IS NULL OR PassengerCount < 0 THEN 1 ELSE 0 END), 0)
            FROM [lh_dataflow_silver].[dbo].[silver_station_daily]
            UNION ALL SELECT 'station_daily', 'Tariff band is recognized', 'ERROR', COUNT_BIG(*),
                COALESCE(SUM(CASE WHEN TariffBand NOT IN ('Standard', 'Peak', 'Green') OR TariffBand IS NULL THEN 1 ELSE 0 END), 0)
            FROM [lh_dataflow_silver].[dbo].[silver_station_daily]
            UNION ALL SELECT 'station_daily', 'Station exists in station dimension', 'ERROR', COUNT_BIG(*),
                COALESCE(SUM(CASE WHEN s.station_id IS NULL THEN 1 ELSE 0 END), 0)
            FROM [lh_dataflow_silver].[dbo].[silver_station_daily] d
            LEFT JOIN gold.dim_station s ON s.station_id = d.StationID
            UNION ALL SELECT 'assistance_requests', 'Fulfilled count is within request count', 'ERROR', COUNT_BIG(*),
                COALESCE(SUM(CASE WHEN FulfilledWithinSla IS NULL OR RequestCount IS NULL OR FulfilledWithinSla < 0 OR FulfilledWithinSla > RequestCount THEN 1 ELSE 0 END), 0)
            FROM [lh_dataflow_silver].[dbo].[silver_assistance_requests]
            UNION ALL SELECT 'assistance_requests', 'Close timestamp is not before open', 'WARNING', COUNT_BIG(*),
                COALESCE(SUM(CASE WHEN ClosedTimestamp IS NOT NULL AND (OpenedTimestamp IS NULL OR ClosedTimestamp < OpenedTimestamp) THEN 1 ELSE 0 END), 0)
            FROM [lh_dataflow_silver].[dbo].[silver_assistance_requests]
            UNION ALL SELECT 'asset_workorders', 'Target date is not before opened date', 'ERROR', COUNT_BIG(*),
                COALESCE(SUM(CASE WHEN TargetDate IS NULL OR OpenedDate IS NULL OR TargetDate < OpenedDate THEN 1 ELSE 0 END), 0)
            FROM [lh_dataflow_silver].[dbo].[silver_asset_workorders]
            UNION ALL SELECT 'asset_workorders', 'Station exists in station dimension', 'ERROR', COUNT_BIG(*),
                COALESCE(SUM(CASE WHEN s.station_id IS NULL THEN 1 ELSE 0 END), 0)
            FROM [lh_dataflow_silver].[dbo].[silver_asset_workorders] w
            LEFT JOIN gold.dim_station s ON s.station_id = w.StationID
        ) rules;

        COMMIT TRANSACTION;

        UPDATE audit.pipeline_run
        SET status = 'COMPLETED', completed_at_utc = SYSUTCDATETIME()
        WHERE run_id = @run_id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        UPDATE audit.pipeline_run
        SET status = 'FAILED', completed_at_utc = SYSUTCDATETIME(), error_message = ERROR_MESSAGE()
        WHERE run_id = @run_id;

        INSERT INTO audit.pipeline_step
            (run_id, step_name, status, source_rows, target_rows, rejected_rows, recorded_at_utc, error_message)
        VALUES
            (@run_id, 'Warehouse Gold load', 'FAILED', NULL, NULL, NULL, SYSUTCDATETIME(), ERROR_MESSAGE());

        THROW;
    END CATCH;
END;
GO