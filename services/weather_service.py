import json
from datetime import date, datetime, timedelta

import requests

from models import WeatherCache, db

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
CACHE_TTL = timedelta(minutes=5)
REQUEST_TIMEOUT = 15

WMO_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherServiceError(Exception):
    pass


def _cache_get(cache_key):
    cache_entry = WeatherCache.query.filter_by(location_key=cache_key).first()
    if not cache_entry:
        return None

    if datetime.utcnow() - cache_entry.timestamp >= CACHE_TTL:
        return None

    return json.loads(cache_entry.data)


def _cache_set(cache_key, payload):
    serialized = json.dumps(payload)
    cache_entry = WeatherCache.query.filter_by(location_key=cache_key).first()

    if cache_entry:
        cache_entry.data = serialized
        cache_entry.timestamp = datetime.utcnow()
    else:
        cache_entry = WeatherCache(
            location_key=cache_key,
            data=serialized,
            timestamp=datetime.utcnow(),
        )
        db.session.add(cache_entry)

    db.session.commit()


def _request_json(url, params):
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()

    if payload.get("error"):
        raise WeatherServiceError(payload.get("reason", "Weather API request failed."))

    return payload


def _build_location_name_parts(location_data):
    return [
        location_data.get("name"),
        location_data.get("admin1"),
        location_data.get("country"),
    ]


def geocode_location(query):
    normalized = query.strip()
    if len(normalized) < 2:
        raise WeatherServiceError("Enter at least 2 characters to search.")

    cache_key = f"geocode:{normalized.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = _request_json(
        GEOCODE_URL,
        {
            "name": normalized,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )

    results = payload.get("results", [])
    if not results:
        raise WeatherServiceError("Location not found.")

    result = results[0]
    result["display_name"] = ", ".join([part for part in _build_location_name_parts(result) if part])
    _cache_set(cache_key, result)
    return result


def build_location_name(location_data=None, fallback_name=None, fallback_lat=None, fallback_lon=None):
    if location_data:
        display_name = location_data.get("display_name")
        if display_name:
            return display_name

        parts = _build_location_name_parts(location_data)
        filtered = [part for part in parts if part]
        if filtered:
            return ", ".join(filtered)

    if fallback_name:
        return fallback_name

    if fallback_lat is not None and fallback_lon is not None:
        return f"{float(fallback_lat):.2f}, {float(fallback_lon):.2f}"

    return "Selected location"


def _normalize_date(target_date):
    if isinstance(target_date, str):
        return datetime.strptime(target_date, "%Y-%m-%d").date()
    return target_date


def classify_date(target_date):
    normalized_date = _normalize_date(target_date)
    today = date.today()

    if normalized_date < today:
        return "past"
    if normalized_date > today:
        return "future"
    return "today"


def _weather_description(code):
    return WMO_DESCRIPTIONS.get(code, "Unknown conditions")


def _normalize_current_payload(payload):
    current = payload["current"]
    daily = payload["daily"]
    daily_rows = []

    for index, dt_value in enumerate(daily["time"]):
        daily_rows.append(
            {
                "dt": int(datetime.strptime(dt_value, "%Y-%m-%d").timestamp()),
                "temp": {
                    "max": daily["temperature_2m_max"][index],
                    "min": daily["temperature_2m_min"][index],
                },
                "weather": [
                    {
                        "description": _weather_description(daily["weather_code"][index]).lower(),
                    }
                ],
            }
        )

    return {
        "current": {
            "temp": current["temperature_2m"],
            "feels_like": current["apparent_temperature"],
            "humidity": current["relative_humidity_2m"],
            "wind_speed": round(current["wind_speed_10m"] / 3.6, 1),
            "uvi": 0,
            "weather": [{"description": _weather_description(current["weather_code"]).lower()}],
        },
        "daily": daily_rows,
    }


def _normalize_day_payload(payload):
    daily = payload["daily"]
    return {
        "temperature": {
            "morning": daily["temperature_2m_mean"][0],
            "afternoon": daily["temperature_2m_max"][0],
            "evening": daily["apparent_temperature_mean"][0],
            "night": daily["temperature_2m_min"][0],
            "min": daily["temperature_2m_min"][0],
            "max": daily["temperature_2m_max"][0],
        },
        "humidity": {
            "afternoon": daily["relative_humidity_2m_mean"][0],
        },
        "wind": {
            "max": {"speed": round(daily["wind_speed_10m_max"][0] / 3.6, 1)},
        },
        "precipitation": {
            "total": daily["precipitation_sum"][0],
        },
        "cloud_cover": {
            "afternoon": daily["cloud_cover_mean"][0],
        },
        "weather": [{"description": _weather_description(daily["weather_code"][0]).lower()}],
    }


def get_current_weather(lat, lon):
    cache_key = f"current:{round(float(lat), 4)}:{round(float(lon), 4)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = _request_json(
        FORECAST_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "timezone": "auto",
            "forecast_days": 8,
            "current": ",".join(
                [
                    "temperature_2m",
                    "apparent_temperature",
                    "relative_humidity_2m",
                    "wind_speed_10m",
                    "weather_code",
                ]
            ),
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                ]
            ),
        },
    )

    normalized = _normalize_current_payload(payload)
    _cache_set(cache_key, normalized)
    return normalized


def get_weather_for_date(lat, lon, target_date):
    normalized_date = _normalize_date(target_date)
    mode = classify_date(normalized_date)
    cache_key = f"day:{round(float(lat), 4)}:{round(float(lon), 4)}:{normalized_date.isoformat()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    base_url = FORECAST_URL if mode in ("today", "future") else ARCHIVE_URL
    payload = _request_json(
        base_url,
        {
            "latitude": lat,
            "longitude": lon,
            "timezone": "auto",
            "start_date": normalized_date.isoformat(),
            "end_date": normalized_date.isoformat(),
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_mean",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "apparent_temperature_mean",
                    "precipitation_sum",
                    "cloud_cover_mean",
                    "relative_humidity_2m_mean",
                    "wind_speed_10m_max",
                ]
            ),
        },
    )

    normalized = _normalize_day_payload(payload)
    _cache_set(cache_key, normalized)
    return normalized
