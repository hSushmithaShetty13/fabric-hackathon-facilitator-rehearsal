section Section1;

BronzeTable = (tableName as text) as table => let
    Source = Lakehouse.Contents([HierarchicalNavigation = null, CreateNavigationProperties = false]),
    Workspace = Source{[workspaceId = "df61bd00-cbeb-40f7-933a-44f944f4f9a4"]}[Data],
    Lakehouse = Workspace{[lakehouseId = "3f5f38ac-8b47-480b-b6a8-588b2b340733"]}[Data],
    Result = Lakehouse{[Id = tableName, ItemKind = "Table"]}[Data]
in
    Result;

CleanText = (value as any) as nullable text =>
    if value is null then null else Text.Trim(Text.Clean(Text.From(value)));

ProperText = (value as any) as nullable text => let
    Cleaned = CleanText(value)
in
    if Cleaned is null then null else Text.Proper(Cleaned);

[DataDestinations = {[
  Definition = [Kind = "Reference", QueryName = "silver_calendar_DataDestination", IsNewTarget = true],
  Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]
]}]
shared silver_calendar = let
    Source = BronzeTable("bronze_calendar"),
    Cleaned = Table.TransformColumns(Source, {
        {"Date", each try Date.FromText(CleanText(_)) otherwise null, type nullable date},
        {"Year", each try Int64.From(Number.FromText(CleanText(_))) otherwise null, Int64.Type},
        {"Month", each try Int64.From(Number.FromText(CleanText(_))) otherwise null, Int64.Type},
        {"MonthName", each ProperText(_), type nullable text},
        {"WeekStartDate", each try Date.FromText(CleanText(_)) otherwise null, type nullable date},
        {"DayName", each ProperText(_), type nullable text},
        {"IsWeekend", each try Logical.FromText(CleanText(_)) otherwise null, type nullable logical}
    }),
    TypedMetadata = Table.TransformColumnTypes(Cleaned, {{"_batch_id", type text}, {"_source_file", type text}, {"_ingested_at_utc", type datetime}}),
    Quality = Table.AddColumn(TypedMetadata, "dq_is_valid", each [Date] <> null and [Year] <> null and [Month] <> null, type logical)
in
    Quality;

[DataDestinations = {[
  Definition = [Kind = "Reference", QueryName = "silver_regions_DataDestination", IsNewTarget = true],
  Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]
]}]
shared silver_regions = let
    Source = BronzeTable("bronze_regions"),
    Cleaned = Table.TransformColumns(Source, {
        {"RegionID", each Text.Upper(CleanText(_)), type nullable text},
        {"RegionName", each ProperText(_), type nullable text},
        {"OperationsDirector", each CleanText(_), type nullable text}
    }),
    TypedMetadata = Table.TransformColumnTypes(Cleaned, {{"_batch_id", type text}, {"_source_file", type text}, {"_ingested_at_utc", type datetime}}),
    Quality = Table.AddColumn(TypedMetadata, "dq_is_valid", each [RegionID] <> null and Text.StartsWith([RegionID], "R"), type logical)
in
    Quality;

[DataDestinations = {[
  Definition = [Kind = "Reference", QueryName = "silver_stations_DataDestination", IsNewTarget = true],
  Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]
]}]
shared silver_stations = let
    Source = BronzeTable("bronze_stations"),
    Cleaned = Table.TransformColumns(Source, {
        {"StationID", each Text.Upper(CleanText(_)), type nullable text},
        {"StationName", each ProperText(_), type nullable text},
        {"RegionID", each Text.Upper(CleanText(_)), type nullable text},
        {"StationType", each ProperText(_), type nullable text},
        {"AccessibilityTier", each Text.Upper(CleanText(_)), type nullable text},
        {"ManagedBy", each ProperText(_), type nullable text}
    }),
    TypedMetadata = Table.TransformColumnTypes(Cleaned, {{"_batch_id", type text}, {"_source_file", type text}, {"_ingested_at_utc", type datetime}}),
    Quality = Table.AddColumn(TypedMetadata, "dq_is_valid", each [StationID] <> null and Text.StartsWith([StationID], "ST") and Text.Length([StationID]) = 5 and [StationName] <> null, type logical)
in
    Quality;

[DataDestinations = {[
  Definition = [Kind = "Reference", QueryName = "silver_tariffs_DataDestination", IsNewTarget = true],
  Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]
]}]
shared silver_tariffs = let
    Source = BronzeTable("bronze_tariffs"),
    Cleaned = Table.TransformColumns(Source, {
        {"TariffBand", each ProperText(_), type nullable text},
        {"RatePerKwh", each try Number.FromText(CleanText(_), "en-US") otherwise null, type nullable number},
        {"StandingChargePerDay", each try Number.FromText(CleanText(_), "en-US") otherwise null, type nullable number},
        {"AppliesTo", each ProperText(_), type nullable text}
    }),
    TypedMetadata = Table.TransformColumnTypes(Cleaned, {{"_batch_id", type text}, {"_source_file", type text}, {"_ingested_at_utc", type datetime}}),
    Quality = Table.AddColumn(TypedMetadata, "dq_is_valid", each List.Contains({"Standard", "Peak", "Green"}, [TariffBand]) and [RatePerKwh] <> null and [RatePerKwh] >= 0, type logical)
in
    Quality;

[DataDestinations = {[
  Definition = [Kind = "Reference", QueryName = "silver_station_daily_DataDestination", IsNewTarget = true],
  Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]
]}]
shared silver_station_daily = let
    Source = BronzeTable("bronze_station_daily"),
    Cleaned = Table.TransformColumns(Source, {
        {"Date", each try Date.FromText(CleanText(_)) otherwise null, type nullable date},
        {"StationID", each Text.Upper(CleanText(_)), type nullable text},
        {"PassengerCount", each try Int64.From(Number.FromText(CleanText(_), "en-US")) otherwise null, Int64.Type},
        {"EnergyKwh", each try Number.FromText(CleanText(_), "en-US") otherwise null, type nullable number},
        {"WeatherDescription", each ProperText(_), type nullable text},
        {"TemperatureC", each try Number.FromText(CleanText(_), "en-US") otherwise null, type nullable number},
        {"TariffBand", each ProperText(_), type nullable text},
        {"MeterReadQuality", each ProperText(_), type nullable text}
    }),
    TypedMetadata = Table.TransformColumnTypes(Cleaned, {{"_batch_id", type text}, {"_source_file", type text}, {"_ingested_at_utc", type datetime}}),
    Quality = Table.AddColumn(TypedMetadata, "dq_is_valid", each [Date] <> null and [StationID] <> null and Text.StartsWith([StationID], "ST") and Text.Length([StationID]) = 5 and [PassengerCount] <> null and [PassengerCount] >= 0 and [EnergyKwh] <> null and [EnergyKwh] >= 0 and List.Contains({"Standard", "Peak", "Green"}, [TariffBand]), type logical)
in
    Quality;

[DataDestinations = {[
  Definition = [Kind = "Reference", QueryName = "silver_assistance_requests_DataDestination", IsNewTarget = true],
  Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]
]}]
shared silver_assistance_requests = let
    Source = BronzeTable("bronze_assistance_requests"),
    Cleaned = Table.TransformColumns(Source, {
        {"Date", each try Date.FromText(CleanText(_)) otherwise null, type nullable date},
        {"StationID", each Text.Upper(CleanText(_)), type nullable text},
        {"RequestType", each ProperText(_), type nullable text},
        {"RequestCount", each try Int64.From(Number.FromText(CleanText(_), "en-US")) otherwise null, Int64.Type},
        {"FulfilledWithinSla", each try Int64.From(Number.FromText(CleanText(_), "en-US")) otherwise null, Int64.Type},
        {"OpenedTimestamp", each try DateTime.FromText(CleanText(_)) otherwise null, type nullable datetime},
        {"ClosedTimestamp", each try DateTime.FromText(CleanText(_)) otherwise null, type nullable datetime},
        {"SlaMinutes", each try Int64.From(Number.FromText(CleanText(_), "en-US")) otherwise null, Int64.Type}
    }),
    TypedMetadata = Table.TransformColumnTypes(Cleaned, {{"_batch_id", type text}, {"_source_file", type text}, {"_ingested_at_utc", type datetime}}),
    Quality = Table.AddColumn(TypedMetadata, "dq_is_valid", each [Date] <> null and [StationID] <> null and Text.StartsWith([StationID], "ST") and [RequestCount] <> null and [RequestCount] >= 0 and [FulfilledWithinSla] <> null and [FulfilledWithinSla] >= 0 and [FulfilledWithinSla] <= [RequestCount] and [OpenedTimestamp] <> null and ([ClosedTimestamp] = null or [ClosedTimestamp] >= [OpenedTimestamp]), type logical)
in
    Quality;

[DataDestinations = {[
  Definition = [Kind = "Reference", QueryName = "silver_asset_workorders_DataDestination", IsNewTarget = true],
  Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]
]}]
shared silver_asset_workorders = let
    Source = BronzeTable("bronze_asset_workorders"),
    Cleaned = Table.TransformColumns(Source, {
        {"WorkOrderID", each Text.Upper(CleanText(_)), type nullable text},
        {"StationID", each Text.Upper(CleanText(_)), type nullable text},
        {"AssetType", each ProperText(_), type nullable text},
        {"Priority", each ProperText(_), type nullable text},
        {"OpenedDate", each try Date.FromText(CleanText(_)) otherwise null, type nullable date},
        {"TargetDate", each try Date.FromText(CleanText(_)) otherwise null, type nullable date},
        {"CompletedDate", each try Date.FromText(CleanText(_)) otherwise null, type nullable date},
        {"EstimatedCost", each try Number.FromText(CleanText(_), "en-US") otherwise null, type nullable number}
    }),
    TypedMetadata = Table.TransformColumnTypes(Cleaned, {{"_batch_id", type text}, {"_source_file", type text}, {"_ingested_at_utc", type datetime}}),
    Quality = Table.AddColumn(TypedMetadata, "dq_is_valid", each [WorkOrderID] <> null and Text.StartsWith([WorkOrderID], "WO") and [StationID] <> null and Text.StartsWith([StationID], "ST") and [OpenedDate] <> null and [TargetDate] <> null and [TargetDate] >= [OpenedDate] and ([CompletedDate] = null or [CompletedDate] >= [OpenedDate]) and [EstimatedCost] <> null and [EstimatedCost] >= 0, type logical)
in
    Quality;

shared silver_calendar_DataDestination = let
    Pattern = Lakehouse.Contents([HierarchicalNavigation = null, CreateNavigationProperties = false, EnableFolding = false]),
    Workspace = Pattern{[workspaceId = "df61bd00-cbeb-40f7-933a-44f944f4f9a4"]}[Data],
    Lakehouse = Workspace{[lakehouseId = "6f7334e1-46a1-47af-a47e-ad32ffc66cbd"]}[Data],
    Target = Lakehouse{[Id = "silver_calendar", ItemKind = "Table"]}?[Data]?
in Target;

shared silver_regions_DataDestination = let
    Pattern = Lakehouse.Contents([HierarchicalNavigation = null, CreateNavigationProperties = false, EnableFolding = false]),
    Workspace = Pattern{[workspaceId = "df61bd00-cbeb-40f7-933a-44f944f4f9a4"]}[Data],
    Lakehouse = Workspace{[lakehouseId = "6f7334e1-46a1-47af-a47e-ad32ffc66cbd"]}[Data],
    Target = Lakehouse{[Id = "silver_regions", ItemKind = "Table"]}?[Data]?
in Target;

shared silver_stations_DataDestination = let
    Pattern = Lakehouse.Contents([HierarchicalNavigation = null, CreateNavigationProperties = false, EnableFolding = false]),
    Workspace = Pattern{[workspaceId = "df61bd00-cbeb-40f7-933a-44f944f4f9a4"]}[Data],
    Lakehouse = Workspace{[lakehouseId = "6f7334e1-46a1-47af-a47e-ad32ffc66cbd"]}[Data],
    Target = Lakehouse{[Id = "silver_stations", ItemKind = "Table"]}?[Data]?
in Target;

shared silver_tariffs_DataDestination = let
    Pattern = Lakehouse.Contents([HierarchicalNavigation = null, CreateNavigationProperties = false, EnableFolding = false]),
    Workspace = Pattern{[workspaceId = "df61bd00-cbeb-40f7-933a-44f944f4f9a4"]}[Data],
    Lakehouse = Workspace{[lakehouseId = "6f7334e1-46a1-47af-a47e-ad32ffc66cbd"]}[Data],
    Target = Lakehouse{[Id = "silver_tariffs", ItemKind = "Table"]}?[Data]?
in Target;

shared silver_station_daily_DataDestination = let
    Pattern = Lakehouse.Contents([HierarchicalNavigation = null, CreateNavigationProperties = false, EnableFolding = false]),
    Workspace = Pattern{[workspaceId = "df61bd00-cbeb-40f7-933a-44f944f4f9a4"]}[Data],
    Lakehouse = Workspace{[lakehouseId = "6f7334e1-46a1-47af-a47e-ad32ffc66cbd"]}[Data],
    Target = Lakehouse{[Id = "silver_station_daily", ItemKind = "Table"]}?[Data]?
in Target;

shared silver_assistance_requests_DataDestination = let
    Pattern = Lakehouse.Contents([HierarchicalNavigation = null, CreateNavigationProperties = false, EnableFolding = false]),
    Workspace = Pattern{[workspaceId = "df61bd00-cbeb-40f7-933a-44f944f4f9a4"]}[Data],
    Lakehouse = Workspace{[lakehouseId = "6f7334e1-46a1-47af-a47e-ad32ffc66cbd"]}[Data],
    Target = Lakehouse{[Id = "silver_assistance_requests", ItemKind = "Table"]}?[Data]?
in Target;

shared silver_asset_workorders_DataDestination = let
    Pattern = Lakehouse.Contents([HierarchicalNavigation = null, CreateNavigationProperties = false, EnableFolding = false]),
    Workspace = Pattern{[workspaceId = "df61bd00-cbeb-40f7-933a-44f944f4f9a4"]}[Data],
    Lakehouse = Workspace{[lakehouseId = "6f7334e1-46a1-47af-a47e-ad32ffc66cbd"]}[Data],
    Target = Lakehouse{[Id = "silver_asset_workorders", ItemKind = "Table"]}?[Data]?
in Target;