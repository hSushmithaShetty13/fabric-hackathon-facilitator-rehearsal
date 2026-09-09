from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "facilitator_rehearsal" / "datasets"
OUT = DATASETS / "station_energy_assistance"
START = date(2026, 8, 3)
DAYS = 28


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def iso_dt(day: date, hour: int, minute: int = 0) -> str:
    return datetime.combine(day, time(hour, minute)).isoformat(timespec="minutes")


random.seed(42)

regions = [
    {"RegionID": "R01", "RegionName": "North West", "OperationsDirector": "A. Patel"},
    {"RegionID": "R02", "RegionName": "Eastern", "OperationsDirector": "M. Green"},
    {"RegionID": "R03", "RegionName": "Wales and Western", "OperationsDirector": "C. Morgan"},
    {"RegionID": "R04", "RegionName": "Southern", "OperationsDirector": "J. Brown"},
]

stations = [
    {"StationID": "ST001", "StationName": "  Manchester Central ", "RegionID": "R01", "StationType": "Major", "AccessibilityTier": "A", "ManagedBy": "Network Rail"},
    {"StationID": "ST002", "StationName": "liverpool exchange", "RegionID": "R01", "StationType": "Regional", "AccessibilityTier": "B", "ManagedBy": "Partner"},
    {"StationID": "ST003", "StationName": "Leeds City", "RegionID": "R02", "StationType": "Major", "AccessibilityTier": "A", "ManagedBy": "Network Rail"},
    {"StationID": "ST004", "StationName": "Norwich Victoria", "RegionID": "R02", "StationType": "Regional", "AccessibilityTier": "C", "ManagedBy": "Partner"},
    {"StationID": "ST005", "StationName": "Cardiff Riverside", "RegionID": "R03", "StationType": "Major", "AccessibilityTier": "A", "ManagedBy": "Network Rail"},
    {"StationID": "ST006", "StationName": "Bristol Parkway", "RegionID": "R03", "StationType": "Regional", "AccessibilityTier": "B", "ManagedBy": "Partner"},
    {"StationID": "ST007", "StationName": "Brighton Junction", "RegionID": "R04", "StationType": "Major", "AccessibilityTier": "A", "ManagedBy": "Network Rail"},
    {"StationID": "ST008", "StationName": "Reading Westgate", "RegionID": "R04", "StationType": "Regional", "AccessibilityTier": "C", "ManagedBy": "Partner"},
]

tariffs = [
    {"TariffBand": "Standard", "RatePerKwh": 0.24, "StandingChargePerDay": 18.50, "AppliesTo": "All stations"},
    {"TariffBand": "Peak", "RatePerKwh": 0.38, "StandingChargePerDay": 18.50, "AppliesTo": "Weekday peak consumption"},
    {"TariffBand": "Green", "RatePerKwh": 0.21, "StandingChargePerDay": 20.00, "AppliesTo": "Stations with green contract"},
]

calendar_rows = []
for offset in range(DAYS):
    day = START + timedelta(days=offset)
    calendar_rows.append(
        {
            "Date": day.isoformat(),
            "Year": day.year,
            "Month": day.month,
            "MonthName": day.strftime("%B"),
            "WeekStartDate": (day - timedelta(days=day.weekday())).isoformat(),
            "DayName": day.strftime("%A"),
            "IsWeekend": str(day.weekday() >= 5),
        }
    )

station_daily_rows = []
assistance_rows = []
workorder_rows = []
request_types = ["Mobility assistance", "Visual impairment", "Hearing impairment", "Luggage support"]
weather_types = ["Clear", "Cloudy", "Rain", "Heavy rain", "Hot", "hot", " COLD "]
asset_types = ["Lift", "Escalator", "Lighting", "Heating", "Help point"]
workorder_id = 1000

for offset in range(DAYS):
    day = START + timedelta(days=offset)
    is_weekend = day.weekday() >= 5
    for station in stations:
        station_id = station["StationID"]
        major = station["StationType"] == "Major"
        base_passengers = 28000 if major else 9500
        passenger_count = int(base_passengers * (0.72 if is_weekend else 1.0) * random.uniform(0.86, 1.18))
        if station_id == "ST006" and offset == 11:
            passenger_count = -240

        weather = random.choice(weather_types)
        temperature = round(random.uniform(9, 27), 1)
        weather_factor = 1.18 if "rain" in weather.lower() else 1.0
        temperature_factor = 1.12 if temperature > 23 or temperature < 12 else 1.0
        energy_kwh = round((2200 if major else 860) * weather_factor * temperature_factor * random.uniform(0.9, 1.16), 1)
        if station_id == "ST003" and offset in (8, 9):
            energy_kwh = round(energy_kwh * 1.75, 1)

        tariff_band = "Green" if station_id in {"ST003", "ST007"} else random.choice(["Standard", "Standard", "Peak"])
        station_daily_rows.append(
            {
                "Date": day.isoformat(),
                "StationID": "ST999" if station_id == "ST008" and offset == 20 else station_id,
                "PassengerCount": passenger_count,
                "EnergyKwh": energy_kwh,
                "WeatherDescription": weather,
                "TemperatureC": temperature,
                "TariffBand": tariff_band,
                "MeterReadQuality": random.choice(["Actual", "Actual", "Actual", "Estimated"]),
            }
        )

        for request_type in request_types:
            if random.random() < (0.62 if major else 0.35):
                request_count = random.randint(1, 14 if major else 6)
                fulfilled = max(0, request_count - random.randint(0, 3))
                opened = iso_dt(day, random.randint(6, 21), random.choice([0, 15, 30, 45]))
                closed = "" if random.random() < 0.08 else iso_dt(day, random.randint(7, 23), random.choice([0, 15, 30, 45]))
                assistance_rows.append(
                    {
                        "Date": day.isoformat(),
                        "StationID": station_id,
                        "RequestType": request_type,
                        "RequestCount": request_count,
                        "FulfilledWithinSla": fulfilled,
                        "OpenedTimestamp": opened,
                        "ClosedTimestamp": closed,
                        "SlaMinutes": random.choice([15, 20, 30]),
                    }
                )

        if random.random() < (0.26 if major else 0.15):
            opened = day - timedelta(days=random.randint(0, 6))
            duration = random.randint(1, 9)
            completed = "" if random.random() < 0.18 else (opened + timedelta(days=duration)).isoformat()
            workorder_rows.append(
                {
                    "WorkOrderID": f"WO{workorder_id}",
                    "StationID": station_id,
                    "AssetType": random.choice(asset_types),
                    "Priority": random.choice(["Low", "Medium", "High", "High"]),
                    "OpenedDate": opened.isoformat(),
                    "TargetDate": (opened + timedelta(days=random.randint(2, 5))).isoformat(),
                    "CompletedDate": completed,
                    "EstimatedCost": random.randint(450, 12500),
                }
            )
            workorder_id += 1

assistance_rows.append(
    {
        "Date": (START + timedelta(days=13)).isoformat(),
        "StationID": "ST004",
        "RequestType": "Mobility assistance",
        "RequestCount": 3,
        "FulfilledWithinSla": 5,
        "OpenedTimestamp": iso_dt(START + timedelta(days=13), 9, 30),
        "ClosedTimestamp": iso_dt(START + timedelta(days=13), 10, 15),
        "SlaMinutes": 20,
    }
)

for stale in ["calendar.csv", "energy_daily.csv", "footfall_daily.csv", "weather_daily.csv"]:
    stale_path = OUT / stale
    if stale_path.exists():
        stale_path.unlink()

write_csv(DATASETS / "calendar.csv", calendar_rows)
write_csv(OUT / "regions.csv", regions)
write_csv(OUT / "stations.csv", stations)
write_csv(OUT / "tariffs.csv", tariffs)
write_csv(OUT / "station_daily.csv", station_daily_rows)
write_csv(OUT / "assistance_requests.csv", assistance_rows)
write_csv(OUT / "asset_workorders.csv", workorder_rows)

print(f"Wrote shared calendar to {DATASETS / 'calendar.csv'}")
print(f"Wrote six scenario CSVs to {OUT}")
