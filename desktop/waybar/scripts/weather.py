#!/usr/bin/env python3
"""长治当前天气：Open-Meteo 天气码、中文状况与 Waybar JSON 输出。"""

import datetime as dt
import json
import math
import subprocess
from dataclasses import dataclass
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

# 固定长治潞州城区中心坐标，无需 API Key；刷新间隔由 config.jsonc 控制。
LATITUDE = 36.20
LONGITUDE = 113.12
LOCATION_LABEL = "长治 · 潞州区"
TIMEZONE = ZoneInfo("Asia/Shanghai")
CONNECT_TIMEOUT_SECONDS = 4
REQUEST_TIMEOUT_SECONDS = 12
MAX_RESPONSE_BYTES = 131072
MAX_DATA_AGE_SECONDS = 2 * 60 * 60
MAX_CLOCK_SKEW_SECONDS = 15 * 60
WEATHER_URL = "https://api.open-meteo.com/v1/forecast?" + urlencode({
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
               "is_day,weather_code,wind_speed_10m",
    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    "timezone": "Asia/Shanghai",
    "temperature_unit": "celsius",
    "wind_speed_unit": "ms",
    "precipitation_unit": "mm",
    "forecast_days": 1,
})
ICONS = {
    "sun": "", "moon": "", "cloud": "", "fog": "󰖑",
    "rain": "", "snow": "", "thunder": "", "unknown": "",
}
# https://open-meteo.com/en/docs#weathervariables
# current 为当前时刻的模型估算；不与气象站实测或全天预报混用。
CONDITIONS = {
    0: ("晴", "sun"),
    1: ("少云", "sun"),
    2: ("多云", "cloud"),
    3: ("阴", "cloud"),
    45: ("雾", "fog"),
    48: ("冻雾", "fog"),
    51: ("小毛毛雨", "rain"),
    53: ("毛毛雨", "rain"),
    55: ("强毛毛雨", "rain"),
    56: ("轻微冻毛毛雨", "rain"),
    57: ("强冻毛毛雨", "rain"),
    61: ("小雨", "rain"),
    63: ("中雨", "rain"),
    65: ("大雨", "rain"),
    66: ("小冻雨", "rain"),
    67: ("强冻雨", "rain"),
    71: ("小雪", "snow"),
    73: ("中雪", "snow"),
    75: ("大雪", "snow"),
    77: ("米雪", "snow"),
    80: ("小阵雨", "rain"),
    81: ("阵雨", "rain"),
    82: ("强阵雨", "rain"),
    85: ("小阵雪", "snow"),
    86: ("强阵雪", "snow"),
    95: ("雷暴", "thunder"),
    96: ("雷暴伴冰雹", "thunder"),
    97: ("强雷暴", "thunder"),
    99: ("雷暴伴强冰雹", "thunder"),
}
UNAVAILABLE_OUTPUT = {
    "text": f"{ICONS['unknown']} 天气暂不可用",
    "tooltip": f"{LOCATION_LABEL}\n天气数据暂不可用，等待下次刷新",
    "class": "unavailable",
}


@dataclass(frozen=True)
class Observation:
    temperature: float
    weather_code: int | None
    is_day: bool | None
    published_at: dt.datetime
    details: tuple[str, ...]


def fetch_weather():
    """每次刷新一个有界请求；无缓存、无重试，无需额外 Python 依赖。"""
    response = subprocess.run(
        ["curl", "--silent", "--fail", "--proto", "=https",
         "--connect-timeout", str(CONNECT_TIMEOUT_SECONDS),
         "--max-time", str(REQUEST_TIMEOUT_SECONDS), "--retry", "0",
         "--max-filesize", str(MAX_RESPONSE_BYTES), WEATHER_URL],
        capture_output=True, timeout=REQUEST_TIMEOUT_SECONDS + 2, check=True,
    )
    return json.loads(response.stdout)


def checked_number(values, key, minimum, maximum):
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"invalid {key}")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"out-of-range {key}")
    return value


def _optional_number(values, key, minimum, maximum):
    """可选数值统一降级为 None；合法的 0 仍保留。"""
    try:
        return checked_number(values, key, minimum, maximum)
    except (KeyError, ValueError, TypeError, OverflowError):
        return None


def _parse_published_at(value, now):
    if not isinstance(value, str):
        raise ValueError("invalid time")
    published = dt.datetime.fromisoformat(value)
    if published.tzinfo is None:
        published = published.replace(tzinfo=TIMEZONE)
    published = published.astimezone(TIMEZONE)
    age = (now - published).total_seconds()
    if not -MAX_CLOCK_SKEW_SECONDS <= age <= MAX_DATA_AGE_SECONDS:
        raise ValueError("stale weather")
    return published


def _daily_details(daily, now):
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        return ""
    try:
        index = daily["time"].index(now.date().isoformat())
    except ValueError:
        return ""

    def number(key, minimum, maximum):
        values = daily.get(key)
        if not isinstance(values, list) or index >= len(values):
            return None
        return _optional_number(values, index, minimum, maximum)

    parts = []
    low = number("temperature_2m_min", -90, 65)
    high = number("temperature_2m_max", -90, 65)
    if low is not None and high is not None and low <= high:
        parts.append(f"今日 {round(low)}–{round(high)}°C")
    probability = number("precipitation_probability_max", 0, 100)
    if probability is not None:
        parts.append(f"降水概率 {round(probability)}%")
    return " · ".join(parts)


def _optional_details(current, daily, now):
    parts = []
    for key, minimum, maximum, label, unit in (
        ("apparent_temperature", -120, 90, "体感", "°C"),
        ("relative_humidity_2m", 0, 100, "湿度", "%"),
    ):
        value = _optional_number(current, key, minimum, maximum)
        if value is not None:
            parts.append(f"{label} {round(value)}{unit}")
    details = [" · ".join(parts)] if parts else []
    speed = _optional_number(current, "wind_speed_10m", 0, 150)
    if speed is not None:
        details.append(f"风速 {speed:.1f} m/s")
    forecast = _daily_details(daily, now)
    if forecast:
        details.append(forecast)
    return tuple(details)


def parse_observation(payload, now):
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError("invalid response")
    for key, expected in (("latitude", LATITUDE), ("longitude", LONGITUDE)):
        # API 返回附近模型网格点的坐标，允许网格偏移，不接受其他城市数据。
        if abs(checked_number(payload, key, -180, 180) - expected) > 0.5:
            raise ValueError("wrong location")
    current = payload["current"]
    if not isinstance(current, dict):
        raise ValueError("invalid current weather")
    temperature = checked_number(current, "temperature_2m", -90, 65)
    published = _parse_published_at(current["time"], now)
    code = current.get("weather_code")
    if type(code) is not int or not 0 <= code <= 99:
        code = None
    daylight = current.get("is_day")
    is_day = bool(daylight) if type(daylight) is int and daylight in (0, 1) else None
    return Observation(temperature, code, is_day, published,
                       _optional_details(current, payload.get("daily"), now))


def select_condition(code, is_day):
    description, category = CONDITIONS.get(code, ("天气未知", "unknown"))
    if category == "sun":
        category = "unknown" if is_day is None else ("sun" if is_day else "moon")
    return description, ICONS[category], category


def render_observation(observation, now):
    description, icon, category = select_condition(observation.weather_code, observation.is_day)
    tooltip = [f"{LOCATION_LABEL} · {description}", *observation.details,
               f"Open-Meteo · 模型估算 · {observation.published_at:%m-%d %H:%M}"]
    # Nerd Font 图标向右伸出一格；补齐占位后，视觉上保留一格空隙。
    return {"text": f"{icon}  {round(observation.temperature)}°C",
            "tooltip": "\n".join(tooltip), "class": category}


def build_output(fetcher=fetch_weather, now=None):
    now = (now or dt.datetime.now(TIMEZONE)).astimezone(TIMEZONE)
    try:
        return render_observation(parse_observation(fetcher(), now), now)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, OverflowError):
        return dict(UNAVAILABLE_OUTPUT)


if __name__ == "__main__":
    print(json.dumps(build_output(), ensure_ascii=False, allow_nan=False))
