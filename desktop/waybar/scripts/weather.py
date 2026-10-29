#!/usr/bin/env python3
"""中央气象台长治站：获取、校验、图标选择、Waybar 输出分别负责单一职责。"""

import datetime as dt
import html
import json
import math
import subprocess
from dataclasses import dataclass
from zoneinfo import ZoneInfo

# 集中调节项；站点标识不是 API Key。刷新间隔仍由 config.jsonc 控制。
STATION_URL = "https://www.nmc.cn/rest/real/dwSMC"
STATION_CITY = "长治"
LOCATION_LABEL = "长治 · 潞州区"
TIMEZONE = ZoneInfo("Asia/Shanghai")
CONNECT_TIMEOUT_SECONDS = 3
REQUEST_TIMEOUT_SECONDS = 8
MAX_RESPONSE_BYTES = 131072
MAX_DATA_AGE_SECONDS = 3 * 60 * 60
MAX_CLOCK_SKEW_SECONDS = 60 * 60
DAY_START_HOUR = 6
NIGHT_START_HOUR = 19
ICONS = {
    "thunder": "", "snow": "", "rain": "", "fog": "󰖑",
    "cloud": "", "sun": "", "moon": "", "unknown": "?",
}
ICON_CONDITIONS = (
    ("雷", "thunder"), ("雪", "snow"), ("雨", "rain"),
    ("雾霾沙尘", "fog"), ("云阴", "cloud"),
)
OPTIONAL_DETAILS = (
    ("feelst", -120, 90, "体感", "°C"),
    ("humidity", 0, 100, "湿度", "%"),
)


@dataclass(frozen=True)
class Observation:
    """校验后的数据契约；展示层不读取原始 API 字段。"""

    temperature: float
    description: str
    published_at: dt.datetime
    details: tuple[str, ...]


def fetch_weather():
    """每次刷新仅请求一次，并限制请求时间和响应大小。"""
    response = subprocess.run(
        ["curl", "--silent", "--fail", "--proto", "=https",
         "--connect-timeout", str(CONNECT_TIMEOUT_SECONDS),
         "--max-time", str(REQUEST_TIMEOUT_SECONDS), "--retry", "0",
         "--max-filesize", str(MAX_RESPONSE_BYTES), STATION_URL],
        capture_output=True, timeout=REQUEST_TIMEOUT_SECONDS + 2, check=True,
    )
    return json.loads(response.stdout)


def checked_number(values, key, minimum, maximum):
    value = values[key]
    # bool 是 int 的子类，但天气数值不接受 bool、字符串、NaN 或缺测值 9999。
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"invalid {key}")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"out-of-range {key}")
    return value


def _parse_published_at(value, now):
    """无时区的站点时间按上海时间解释，统一后检查新鲜度。"""
    published = dt.datetime.fromisoformat(value)
    if published.tzinfo is None:
        published = published.replace(tzinfo=TIMEZONE)
    published = published.astimezone(TIMEZONE)
    age = (now - published).total_seconds()
    if not -MAX_CLOCK_SKEW_SECONDS <= age <= MAX_DATA_AGE_SECONDS:
        raise ValueError("stale weather")
    return published


def _optional_details(weather):
    """按固定顺序生成可选详情；单个字段异常不隐藏有效的温度。"""
    details = []
    for key, minimum, maximum, label, unit in OPTIONAL_DETAILS:
        try:
            details.append(f"{label} {checked_number(weather, key, minimum, maximum):.0f}{unit}")
        except (KeyError, ValueError, TypeError):
            # 可选字段异常不影响温度显示。
            continue
    return tuple(details)


def parse_observation(payload, now):
    if not isinstance(payload, dict) or payload["station"]["city"] != STATION_CITY:
        raise ValueError("wrong station")
    weather = payload["weather"]
    if not isinstance(weather, dict):
        raise ValueError("invalid weather")
    temperature = checked_number(weather, "temperature", -90, 65)
    published = _parse_published_at(payload["publish_time"], now)
    description = weather["info"]
    if not isinstance(description, str) or not description or description == "9999":
        raise ValueError("missing condition")
    return Observation(temperature, description, published, _optional_details(weather))


def select_icon(description, hour):
    # 雨雪、雷雨等复合状态按优先级匹配，避免未知条件被误画成晴天。
    for conditions, name in ICON_CONDITIONS:
        if any(condition in description for condition in conditions):
            return ICONS[name]
    if description == "晴":
        return ICONS["sun" if DAY_START_HOUR <= hour < NIGHT_START_HOUR else "moon"]
    return ICONS["unknown"]


def render_observation(observation, now):
    icon = select_icon(observation.description, now.hour)
    tooltip = [f"{LOCATION_LABEL} · {html.escape(observation.description)}"]
    if observation.details:
        tooltip.append(" · ".join(observation.details))
    tooltip.append(f"中央气象台 · {observation.published_at:%H:%M}")
    return {
        "text": f"{icon}  {observation.temperature:.0f}°C",
        "tooltip": "\n".join(tooltip),
    }


def build_output(fetcher=fetch_weather, now=None):
    """注入数据源便于离线测试；所有正常失败都遵守同一个空输出契约。"""
    now = now or dt.datetime.now(TIMEZONE)
    try:
        return render_observation(parse_observation(fetcher(), now), now)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, OverflowError):
        return {"text": "", "tooltip": ""}


if __name__ == "__main__":
    print(json.dumps(build_output(), ensure_ascii=False, allow_nan=False))
