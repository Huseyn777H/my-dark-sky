import json
import os
from datetime import date, datetime, timedelta

import requests

from models import WeatherCache, db

API_KEY = os.getenv("OPENWEATHER_API_KEY")
ONE_CALL_URL = "https://api.openweathermap.org/data/3.0/onecall"
DAY_SUMMARY_URL = "https://api.openweathermap.org/data/3.0/onecall/day_summary"
GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
REVERSE_GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/reverse"
CACHE_TTL = timedelta(minutes=5)
REQUEST_TIMEOUT = 15


class WeatherServiceError(Exception):
    pass


def _require_api_key():
    if not API_KEY:
        raise WeatherServiceError("OPENWEATHER_API_KEY is missing.")


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
    _require_api_key()

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, dict) and str(payload.get("cod", "")).startswith(("4", "5")):
        raise WeatherServiceError(payload.get("message", "Weather API request failed."))

    return payload


def geocode_location(query):
    normalized = query.strip()
    if not normalized:
        raise WeatherServiceError("Enter a city name to search.")

    cache_key = f"geocode:{normalized.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = _request_json(
        GEOCODE_URL,
        {
            "q": normalized,
            "limit": 1,
            "appid": API_KEY,
        },
    )

    if not payload:
        raise WeatherServiceError("Location not found.")

    result = payload[0]
    _cache_set(cache_key, result)
    return result


def reverse_geocode(lat, lon):
    cache_key = f"reverse:{round(float(lat), 4)}:{round(float(lon), 4)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = _request_json(
        REVERSE_GEOCODE_URL,
        {
            "lat": lat,
            "lon": lon,
            "limit": 1,
            "appid": API_KEY,
        },
    )

    result = payload[0] if payload else {}
    _cache_set(cache_key, result)
    return result


def build_location_name(location_data, fallback_lat=None, fallback_lon=None):
    if not location_data:
        if fallback_lat is not None and fallback_lon is not None:
            return f"{float(fallback_lat):.2f}, {float(fallback_lon):.2f}"
        return "Selected location"

    parts = [location_data.get("name")]
    if location_data.get("state"):
        parts.append(location_data["state"])
    if location_data.get("country"):
        parts.append(location_data["country"])

    return ", ".join([part for part in parts if part])


def _normalize_date(target_date):
    if isinstance(target_date, str):
        return datetime.strptime(target_date, "%Y-%m-%d").date()
    return target_date


def get_current_weather(lat, lon):
    cache_key = f"current:{round(float(lat), 4)}:{round(float(lon), 4)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = _request_json(
        ONE_CALL_URL,
        {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": "metric",
        },
    )
    _cache_set(cache_key, payload)
    return payload


def get_weather_for_date(lat, lon, target_date):
    normalized_date = _normalize_date(target_date)
    cache_key = f"day:{round(float(lat), 4)}:{round(float(lon), 4)}:{normalized_date.isoformat()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    payload = _request_json(
        DAY_SUMMARY_URL,
        {
            "lat": lat,
            "lon": lon,
            "date": normalized_date.isoformat(),
            "appid": API_KEY,
            "units": "metric",
        },
    )
    _cache_set(cache_key, payload)
    return payload


def classify_date(target_date):
    normalized_date = _normalize_date(target_date)
    today = date.today()

    if normalized_date < today:
        return "past"
    if normalized_date > today:
        return "future"
    return "today"
