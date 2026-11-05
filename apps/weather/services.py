from datetime import date, timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


DISTRICTS = {
    "Kurigram": (25.8072, 89.6295),
    "Dinajpur": (25.6279, 88.6332),
    "Rangpur": (25.7439, 89.2752),
    "Gaibandha": (25.3297, 89.5430),
    "Nilphamari": (25.9318, 88.8560),
    "Dhaka": (23.8103, 90.4125),
}

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with hail",
}


class WeatherServiceError(RuntimeError):
    pass


def available_districts():
    return sorted(DISTRICTS)


def _demo_weather(district, fallback_reason=""):
    today = timezone.localdate()
    temperatures = [(30, 23), (31, 24), (29, 23), (28, 22), (30, 23), (31, 24), (29, 23)]
    rain = [25, 35, 60, 70, 40, 30, 45]
    return {
        "available": True,
        "is_demo": True,
        "status_label": "DEMONSTRATION DATA - NOT LIVE",
        "district": district,
        "temperature": 28,
        "humidity": 72,
        "rainfall": 0,
        "rain_probability": 35,
        "wind_speed": 9,
        "condition": "Partly cloudy (illustrative)",
        "updated_at": timezone.now().isoformat(),
        "timezone": settings.TIME_ZONE,
        "source": "Farm Time Machine demonstration dataset",
        "source_url": "",
        "fallback_reason": fallback_reason,
        "forecast": [
            {
                "date": (today + timedelta(days=index)).isoformat(),
                "temperature_max": values[0],
                "temperature_min": values[1],
                "rain_probability": rain[index],
                "rainfall": round(rain[index] / 20, 1),
                "condition": "Illustrative outlook",
            }
            for index, values in enumerate(temperatures)
        ],
    }


def _unavailable(district, reason):
    return {
        "available": False,
        "is_demo": False,
        "status_label": "LIVE DATA UNAVAILABLE",
        "district": district,
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "updated_at": timezone.now().isoformat(),
        "timezone": settings.TIME_ZONE,
        "forecast": [],
        "error": reason,
    }


def _value(values, index, default=None):
    try:
        return values[index]
    except (IndexError, TypeError):
        return default


def get_weather(district="Kurigram"):
    district = district if district in DISTRICTS else "Kurigram"
    cache_key = f"weather:open-meteo:{district.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    if not settings.WEATHER_LIVE_ENABLED:
        result = _demo_weather(district, "Live weather is disabled in this environment.") if settings.DEMO_MODE else _unavailable(district, "Live weather is not configured.")
        cache.set(cache_key, result, 300)
        return result

    latitude, longitude = DISTRICTS[district]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "forecast_days": 7,
        "timezone": settings.TIME_ZONE,
    }
    try:
        response = requests.get(settings.WEATHER_API_BASE_URL, params=params, timeout=(2, 5))
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current") or {}
        daily = payload.get("daily") or {}
        if current.get("temperature_2m") is None:
            raise WeatherServiceError("The provider response did not include current temperature.")
        dates = daily.get("time") or []
        forecast = []
        for index, day in enumerate(dates):
            code = _value(daily.get("weather_code"), index)
            forecast.append(
                {
                    "date": day,
                    "temperature_max": _value(daily.get("temperature_2m_max"), index),
                    "temperature_min": _value(daily.get("temperature_2m_min"), index),
                    "rain_probability": _value(daily.get("precipitation_probability_max"), index),
                    "rainfall": _value(daily.get("precipitation_sum"), index),
                    "condition": WEATHER_CODES.get(code, "Conditions unavailable"),
                }
            )
        code = current.get("weather_code")
        result = {
            "available": True,
            "is_demo": False,
            "status_label": "LIVE WEATHER",
            "district": district,
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "rainfall": current.get("rain", current.get("precipitation")),
            "rain_probability": _value(daily.get("precipitation_probability_max"), 0),
            "wind_speed": current.get("wind_speed_10m"),
            "condition": WEATHER_CODES.get(code, "Conditions unavailable"),
            "updated_at": current.get("time") or timezone.now().isoformat(),
            "timezone": payload.get("timezone", settings.TIME_ZONE),
            "source": "Open-Meteo",
            "source_url": "https://open-meteo.com/",
            "forecast": forecast,
        }
        cache.set(cache_key, result, 1800)
        return result
    except (requests.RequestException, ValueError, WeatherServiceError) as exc:
        reason = "The weather provider could not be reached. Try again later."
        result = _demo_weather(district, reason) if settings.DEMO_MODE else _unavailable(district, reason)
        cache.set(cache_key, result, 120)
        return result
