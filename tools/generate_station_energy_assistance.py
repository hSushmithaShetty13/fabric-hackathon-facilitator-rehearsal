from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "facilitator_rehearsal" / "datasets" / "station_energy_assistance"
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
    {"RegionID": "R01", "RegionName": "North West", "Directorate": "Operations North"},
    {"RegionID": "R02", "RegionName": "Eastern", "Directorate": "Operations East"},
    {"RegionID": "R03", "RegionName": "Wales and Western", "Directorate": "Operations West"},
    {"RegionID": "R04", "RegionName": "Southern", "Directorate": "Operations South"},
]

stations = [
    {"StationID": "ST001", "StationName": "  Manchester Central ", "RegionID": "R01", "StationType": "Major", "HasStepFreeAccess": "True", "ManagedBy": "Network Rail"},
    {"StationID": "ST002", "StationName": "liverpool exchange", "RegionID": "R01", "StationType": "Regional", "HasStepFreeAccess": "True", "ManagedBy": "Partner"},
    {"StationID": "ST003", "StationName": "Leeds City", "RegionID": "R02", "StationType": "Major", "HasStepFreeAccess": "True", "ManagedBy": "Network Rail"},
    {"StationID": "ST004", "StationName": "Norwich Victoria", "RegionID": "R02", "StationType": "Regional", "HasStepFreeAccess": "False", "ManagedBy": "Partner"},
    {"StationID": "ST005", "StationName": "Cardiff Riverside", "RegionID": "R03", "StationType": "Major", "HasStepFreeAccess": "True", "ManagedBy": "Network Rail"},
    {"StationID": "ST006", "StationName": "Bristol Parkway", "RegionID": "R03", "StationType": "Regional", "HasStepFreeAccess": "True", "ManagedBy": "Partner"},
    {"StationID": "ST007", "StationName": "Brighton Junction", "RegionID": "R04", "StationType": "Major", "HasStepFreeAccess": "True", "ManagedBy": "Network Rail"},
    {"StationID": "ST008", "StationName": "Reading Westgate", "RegionID": "R04", "StationType": "Regional", "HasStepFreeAccess": "False", "ManagedBy": "Partner"},
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

energy_rows = []
footfall_rows = []
weather_rows = []
assistance_rows = []
request_types = ["Mobility assistance", "Visual impairment", "Hearing impairment", "Luggage support"]
weather_types = ["Clear", "Cloudy", "Rain", "Heavy rain", "Hot", "hot", " COLD "]

for offset in range(DAYS):
    day = START + timedelta(days=offset)
    is_weekend = day.weekday() >= 5
    for index, station in enumerate(stations):
        station_id = station["StationID"]
        major = station["StationType"] == "Major"
        base_passengers = 28000 if major else 9500
        passenger_count = int(base_passengers * (0.72 if is_weekend else 1.0) * random.uniform(0.86, 1.18))
        if station_id == "ST006" and offset == 11:
            passenger_count = -240

        temperature = round(random.uniform(9, 27), 1)
        weather = random.choice(weather_types)
        weather_factor = 1.18 if "rain" in weather.lower() else 1.0
        temperature_factor = 1.12 if temperature > 23 or temperature < 12 else 1.0
        energy_kwh = round((2200 if major else 860) * weather_factor * temperature_factor * random.uniform(0.9, 1.16), 1)
        if station_id == "ST003" and offset in (8, 9):
            energy_kwh = round(energy_kwh * 1.75, 1)

        energy_rows.append(
            {
                "Date": day.isoformat(),
                "StationID": "ST999" if station_id == "ST008" and offset == 20 else station_id,
                "EnergyKwh": energy_kwh,
                "MeterReadQuality": random.choice(["Actual", "Actual", "Actual", "Estimated"]),
                "TariffBand": random.choice(["Standard", "Standard", "Peak"]),
            }
        )
        footfall_rows.append(
            {
                "Date": day.isoformat(),
                "StationID": station_id,
                "PassengerCount": passenger_count,
                "Entries": int(passenger_count * random.uniform(0.47, 0.53)) if passenger_count >= 0 else passenger_count,
                "Exits": int(passenger_count * random.uniform(0.47, 0.53)) if passenger_count >= 0 else 0,
            }
        )
        weather_rows.append(
            {
                "Date": day.isoformat(),
                "StationID": station_id,
                "WeatherDescription": weather,
                "TemperatureC": temperature,
                "RainfallMm": round(random.uniform(0, 18) if "rain" in weather.lower() else random.uniform(0, 2), 1),
            }
        )

        for request_type in request_types:
            if random.random() < (0.62 if major else 0.35):
                request_count = random.randint(1, 14 if major else 6)
                fulfilled = max(0, request_count - random.randint(0, 3))
                opened = iso_dt(day, random.randint(6, 21), random.choice([0, 15, 30, 45]))
                closed = "" if random.random() < 0.08 else iso_dt(day, random.randint(7, 23), random.choice([0, 15, 30, 45]))
                if station_id == "ST004" and offset == 13 and request_type == "Mobility assistance":
                    fulfilled = request_count + 2
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

write_csv(OUT / "calendar.csv", calendar_rows)
write_csv(OUT / "regions.csv", regions)
write_csv(OUT / "stations.csv", stations)
write_csv(OUT / "energy_daily.csv", energy_rows)
write_csv(OUT / "footfall_daily.csv", footfall_rows)
write_csv(OUT / "weather_daily.csv", weather_rows)
write_csv(OUT / "assistance_requests.csv", assistance_rows)

print(f"Wrote rehearsal dataset to {OUT}")
