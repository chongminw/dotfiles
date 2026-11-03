"""Open-Meteo 天气显示与网络边界测试；全部离线运行。"""

import copy
import datetime as dt
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/weather.py"
SPEC = importlib.util.spec_from_file_location("waybar_weather", MODULE_PATH)
weather = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = weather
SPEC.loader.exec_module(weather)

UNAVAILABLE = {
    "text": " 天气暂不可用",
    "tooltip": "长治 · 潞州区\n天气数据暂不可用，等待下次刷新",
    "class": "unavailable",
}


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 11, 3, 15, 55, tzinfo=weather.TIMEZONE)
        self.payload = {
            "latitude": 36.20,
            "longitude": 113.12,
            "current": {
                "time": "2026-11-03T15:45",
                "temperature_2m": 15.4,
                "weather_code": 3,
                "is_day": 1,
                "apparent_temperature": 13.4,
                "relative_humidity_2m": 36,
                "wind_speed_10m": 0.6,
            },
            "daily": {
                "time": ["2026-11-03"],
                "temperature_2m_min": [3.2],
                "temperature_2m_max": [16.1],
                "precipitation_probability_max": [0],
            },
        }

    def output(self, payload=None):
        return weather.build_output(lambda: self.payload if payload is None else payload, self.now)

    def test_full_output_contains_condition_and_source(self):
        output = self.output()
        self.assertEqual(output, {
            "text": "  15°C",
            "tooltip": (
                "长治 · 潞州区 · 阴\n"
                "体感 13°C · 湿度 36%\n"
                "风速 0.6 m/s\n"
                "今日 3–16°C · 降水概率 0%\n"
                "Open-Meteo · 模型估算 · 11-03 15:45"
            ),
            "class": "cloud",
        })
        self.assertEqual(json.loads(json.dumps(output, allow_nan=False)), output)

    def test_all_documented_weather_codes_have_weather_icons(self):
        # 包括旧版天气码表容易遗漏的 97（强雷暴）。
        groups = {
            "sun": (0, 1), "cloud": (2, 3), "fog": (45, 48),
            "rain": (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82),
            "snow": (71, 73, 75, 77, 85, 86), "thunder": (95, 96, 97, 99),
        }
        for expected_class, codes in groups.items():
            for code in codes:
                with self.subTest(code=code):
                    self.payload["current"]["weather_code"] = code
                    output = self.output()
                    self.assertEqual(output["class"], expected_class)
                    self.assertIn("15°C", output["text"])
                    self.assertNotIn("?", output["text"])
                    self.assertNotIn("天气未知", output["text"])

    def test_clear_weather_uses_api_daylight_instead_of_clock_hour(self):
        for code in (0, 1):
            for is_day, icon, css_class in ((1, "", "sun"), (0, "", "moon")):
                with self.subTest(code=code, is_day=is_day):
                    self.payload["current"].update(weather_code=code, is_day=is_day)
                    self.assertEqual(self.output()["text"], f"{icon}  15°C")
                    self.assertEqual(self.output()["class"], css_class)

    def test_invalid_or_missing_daylight_never_guesses_sun(self):
        self.payload["current"]["weather_code"] = 0
        for value in (None, True, 1.0, "1", -1, 2, [], {}):
            with self.subTest(is_day=value):
                self.payload["current"]["is_day"] = value
                self.assertEqual(self.output()["text"], "  15°C")
                self.assertEqual(self.output()["class"], "unknown")
        del self.payload["current"]["is_day"]
        self.assertEqual(self.output()["text"], "  15°C")

    def test_unknown_or_invalid_weather_code_preserves_temperature(self):
        for value in (None, True, 3.0, "3", -1, 100, 9999, 4, 98, [], {}):
            with self.subTest(code=value):
                self.payload["current"]["weather_code"] = value
                output = self.output()
                self.assertEqual(output["text"], "  15°C")
                self.assertEqual(output["class"], "unknown")
                self.assertIn("天气未知", output["tooltip"])
        del self.payload["current"]["weather_code"]
        self.assertEqual(self.output()["text"], "  15°C")

    def test_invalid_temperature_shows_unavailable(self):
        for value in (True, "15", None, float("nan"), float("inf"), -91, 66, 9999):
            with self.subTest(temperature=value):
                self.payload["current"]["temperature_2m"] = value
                self.assertEqual(self.output(), UNAVAILABLE)
        del self.payload["current"]["temperature_2m"]
        self.assertEqual(self.output(), UNAVAILABLE)

    def test_temperature_rounding_does_not_show_negative_zero(self):
        self.payload["current"]["temperature_2m"] = -0.1
        self.assertEqual(self.output()["text"], "  0°C")

    def test_malformed_responses_show_unavailable(self):
        for payload in (None, [], {}, {"current": None},
                        {"latitude": 36.20, "longitude": 113.12, "current": []}):
            with self.subTest(payload=payload):
                self.assertEqual(weather.build_output(lambda: payload, self.now), UNAVAILABLE)

    def test_coordinates_are_required_and_near_requested_location(self):
        for key in ("latitude", "longitude"):
            for value in (None, True, "36.20", float("nan"), float("inf"), 0):
                with self.subTest(key=key, value=value):
                    payload = copy.deepcopy(self.payload)
                    payload[key] = value
                    self.assertEqual(self.output(payload), UNAVAILABLE)
            payload = copy.deepcopy(self.payload)
            del payload[key]
            self.assertEqual(self.output(payload), UNAVAILABLE)
        for offset, available in ((-0.5, True), (0.5, True), (-0.51, False), (0.51, False)):
            for key, center in (("latitude", 36.20), ("longitude", 113.12)):
                with self.subTest(key=key, offset=offset):
                    payload = copy.deepcopy(self.payload)
                    payload[key] = center + offset
                    self.assertEqual(self.output(payload) != UNAVAILABLE, available)

    def test_invalid_observation_time_shows_unavailable(self):
        for value in (None, True, [], "invalid", "2026-11-02T15:45", "2026-11-03T17:00"):
            with self.subTest(time=value):
                self.payload["current"]["time"] = value
                self.assertEqual(self.output(), UNAVAILABLE)
        del self.payload["current"]["time"]
        self.assertEqual(self.output(), UNAVAILABLE)

    def test_freshness_boundaries_are_inclusive(self):
        for offset, available in ((-7200, True), (-7201, False), (900, True), (901, False)):
            with self.subTest(offset=offset):
                self.payload["current"]["time"] = (self.now + dt.timedelta(seconds=offset)).isoformat()
                self.assertEqual(self.output() != UNAVAILABLE, available)

    def test_timezone_aware_observation_is_converted_to_shanghai(self):
        self.payload["current"]["time"] = "2026-11-03T07:45:00+00:00"
        self.assertTrue(self.output()["tooltip"].endswith("11-03 15:45"))
        self.assertEqual(self.output()["text"], "  15°C")

    def test_optional_fields_can_all_be_missing(self):
        self.payload["current"] = {
            "time": "2026-11-03T15:45", "temperature_2m": 15.4, "weather_code": 3,
        }
        del self.payload["daily"]
        self.assertEqual(self.output(), {
            "text": "  15°C",
            "tooltip": "长治 · 潞州区 · 阴\nOpen-Meteo · 模型估算 · 11-03 15:45",
            "class": "cloud",
        })

    def test_invalid_optional_current_field_preserves_other_details(self):
        invalid_fields = (
            ("apparent_temperature", "体感", (True, "13", None, float("nan"), -121, 91)),
            ("relative_humidity_2m", "湿度", (True, "36", None, float("inf"), -1, 101)),
            ("wind_speed_10m", "风速", (True, "0.6", None, float("nan"), -1, 151)),
        )
        for key, label, invalid_values in invalid_fields:
            for value in invalid_values:
                with self.subTest(key=key, value=value):
                    payload = copy.deepcopy(self.payload)
                    payload["current"][key] = value
                    output = self.output(payload)
                    self.assertEqual(output["text"], "  15°C")
                    self.assertNotIn(label, output["tooltip"])
                    self.assertIn("今日 3–16°C · 降水概率 0%", output["tooltip"])
                    other = "湿度 36%" if key != "relative_humidity_2m" else "体感 13°C"
                    self.assertIn(other, output["tooltip"])

    def test_daily_uses_today_index_instead_of_first_entry(self):
        self.payload["daily"] = {
            "time": ["2026-11-02", "2026-11-03"],
            "temperature_2m_min": [-4, 3.2],
            "temperature_2m_max": [7, 16.1],
            "precipitation_probability_max": [90, 0],
        }
        self.assertIn("今日 3–16°C · 降水概率 0%", self.output()["tooltip"])

    def test_daily_without_today_is_ignored(self):
        for dates in (["2026-11-02"], ["2026-11-04"], [], None, "2026-11-03"):
            with self.subTest(dates=dates):
                self.payload["daily"]["time"] = dates
                output = self.output()
                self.assertEqual(output["text"], "  15°C")
                self.assertNotIn("今日", output["tooltip"])
                self.assertNotIn("降水概率", output["tooltip"])

    def test_bad_daily_temperature_range_keeps_probability(self):
        for key, value in (("temperature_2m_min", None), ("temperature_2m_max", True),
                           ("temperature_2m_min", float("nan")),
                           ("temperature_2m_max", 66), ("temperature_2m_min", 17)):
            with self.subTest(key=key, value=value):
                payload = copy.deepcopy(self.payload)
                payload["daily"][key] = [value]
                output = self.output(payload)
                self.assertEqual(output["text"], "  15°C")
                self.assertNotIn("今日", output["tooltip"])
                self.assertIn("降水概率 0%", output["tooltip"])

    def test_invalid_daily_probability_keeps_temperature_range(self):
        for value in (True, "0", None, float("nan"), -1, 101):
            with self.subTest(probability=value):
                self.payload["daily"]["precipitation_probability_max"] = [value]
                output = self.output()
                self.assertIn("今日 3–16°C", output["tooltip"])
                self.assertNotIn("降水概率", output["tooltip"])

    def test_malformed_daily_does_not_hide_current_weather(self):
        for daily in (None, [], "invalid", {},
                      {"time": ["2026-11-03"], "temperature_2m_min": []},
                      {"time": ["2026-11-03"], "temperature_2m_min": None}):
            with self.subTest(daily=daily):
                self.payload["daily"] = daily
                self.assertEqual(self.output()["text"], "  15°C")

    def test_external_failures_share_unavailable_output(self):
        for error in (OSError(), subprocess.TimeoutExpired("curl", 12),
                      subprocess.CalledProcessError(22, "curl"), ValueError("bad JSON")):
            with self.subTest(error=error):
                def fail():
                    raise error
                self.assertEqual(weather.build_output(fail, self.now), UNAVAILABLE)

    def test_fetcher_bounds_network_work_and_requests_correct_fields(self):
        with patch.object(weather.subprocess, "run") as run:
            run.return_value.stdout = json.dumps(self.payload).encode()
            self.assertEqual(weather.fetch_weather(), self.payload)
            run.assert_called_once()
            args, kwargs = run.call_args
            command = args[0]
            for option, value in (
                ("--proto", "=https"), ("--connect-timeout", "4"),
                ("--max-time", "12"), ("--retry", "0"), ("--max-filesize", "131072"),
            ):
                self.assertEqual(command[command.index(option) + 1], value)
            self.assertEqual(command[-1], weather.WEATHER_URL)
            self.assertTrue(kwargs["capture_output"])
            self.assertTrue(kwargs["check"])
            self.assertEqual(kwargs["timeout"], 14)
            url = urlparse(command[-1])
            self.assertEqual((url.scheme, url.netloc, url.path),
                             ("https", "api.open-meteo.com", "/v1/forecast"))
            query = parse_qs(url.query)
            self.assertEqual(float(query["latitude"][0]), 36.20)
            self.assertEqual(float(query["longitude"][0]), 113.12)
            self.assertEqual(query["timezone"], ["Asia/Shanghai"])
            self.assertEqual(query["wind_speed_unit"], ["ms"])
            self.assertTrue({"temperature_2m", "weather_code", "is_day",
                             "apparent_temperature", "relative_humidity_2m", "wind_speed_10m"}
                            <= set(query["current"][0].split(",")))
            self.assertTrue({"temperature_2m_min", "temperature_2m_max",
                             "precipitation_probability_max"}
                            <= set(query["daily"][0].split(",")))

    def test_fetcher_does_not_retry_failure(self):
        with patch.object(weather.subprocess, "run",
                          side_effect=subprocess.TimeoutExpired("curl", 12)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                weather.fetch_weather()
            run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
