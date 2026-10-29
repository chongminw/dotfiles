"""天气纯函数与外部边界测试，不请求网络。"""

import copy
import datetime as dt
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/weather.py"
SPEC = importlib.util.spec_from_file_location("waybar_weather", MODULE_PATH)
weather = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = weather
SPEC.loader.exec_module(weather)


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 9, 17, 10, 24, tzinfo=weather.TIMEZONE)
        self.payload = {
            "station": {"city": "长治"}, "publish_time": "2026-09-17 10:00",
            "weather": {"temperature": 18, "info": "晴", "feelst": 17, "humidity": 60},
        }

    def output(self, payload):
        return weather.build_output(lambda: payload, self.now)

    def test_render_contract_inherits_css_font(self):
        output = self.output(self.payload)
        self.assertEqual(output["text"], "  18°C")
        self.assertEqual(output["tooltip"], "长治 · 潞州区 · 晴\n体感 17°C · 湿度 60%\n中央气象台 · 10:00")
        self.assertEqual(json.loads(json.dumps(output, allow_nan=False)), output)

    def test_required_numeric_values_fail_closed(self):
        for value in (True, "18", None, float("nan"), float("inf"), -91, 66, 9999):
            with self.subTest(value=value):
                payload = copy.deepcopy(self.payload)
                payload["weather"]["temperature"] = value
                self.assertEqual(self.output(payload)["text"], "")

    def test_bad_payloads_do_not_raise(self):
        for payload in (None, [], {}, {"station": None}, {"station": {"city": "北京"}}):
            with self.subTest(payload=payload):
                self.assertEqual(self.output(payload), {"text": "", "tooltip": ""})

    def test_optional_values_can_be_missing(self):
        del self.payload["weather"]["feelst"]
        self.payload["weather"]["humidity"] = 9999
        output = self.output(self.payload)
        self.assertIn("18°C", output["text"])
        self.assertNotIn("湿度", output["tooltip"])

    def test_invalid_optional_field_preserves_other_details(self):
        for value in (True, "17", None, float("nan"), float("inf"), -121, 91, 9999):
            with self.subTest(value=value):
                self.payload["weather"]["feelst"] = value
                output = self.output(self.payload)
                self.assertIn("18°C", output["text"])
                self.assertEqual(output["tooltip"], "长治 · 潞州区 · 晴\n湿度 60%\n中央气象台 · 10:00")

    def test_missing_condition_hides_observation(self):
        for description in (None, "", "9999", 9999, True):
            with self.subTest(description=description):
                self.payload["weather"]["info"] = description
                self.assertEqual(self.output(self.payload), {"text": "", "tooltip": ""})

    def test_stale_and_future_data_hidden(self):
        for stamp in ("2026-09-16 10:00", "2026-09-17 12:00", "invalid"):
            with self.subTest(stamp=stamp):
                self.payload["publish_time"] = stamp
                self.assertEqual(self.output(self.payload)["text"], "")

    def test_timezone_aware_observation(self):
        self.payload["publish_time"] = "2026-09-17T02:00:00+00:00"
        self.assertIn("10:00", self.output(self.payload)["tooltip"])

    def test_freshness_boundaries_are_inclusive(self):
        for offset, visible in ((-10800, True), (-10801, False), (3600, True), (3601, False)):
            with self.subTest(offset=offset):
                self.payload["publish_time"] = (self.now + dt.timedelta(seconds=offset)).isoformat()
                self.assertEqual(bool(self.output(self.payload)["text"]), visible)

    def test_icon_priorities_and_day_night(self):
        for description, name in (("雷阵雨", "thunder"), ("雨夹雪", "snow"),
                                  ("小雨", "rain"), ("雾", "fog"), ("多云", "cloud")):
            with self.subTest(description=description):
                self.assertEqual(weather.select_icon(description, 10), weather.ICONS[name])
        for hour in (0, 5, 19, 23):
            self.assertEqual(weather.select_icon("晴", hour), weather.ICONS["moon"])
        for hour in (6, 12, 18):
            self.assertEqual(weather.select_icon("晴", hour), weather.ICONS["sun"])
        self.payload["weather"]["info"] = "未知"
        output = self.output(self.payload)
        self.assertIn(weather.ICONS["unknown"], output["text"])
        self.assertIn("18°C", output["text"])
        self.assertIn("未知", output["tooltip"])

    def test_tooltip_escapes_markup(self):
        self.payload["weather"]["info"] = "多云<script>"
        self.assertIn("&lt;script&gt;", self.output(self.payload)["tooltip"])

    def test_external_failures_share_empty_contract(self):
        for error in (OSError(), subprocess.TimeoutExpired("curl", 10),
                      subprocess.CalledProcessError(22, "curl"), ValueError("bad JSON")):
            with self.subTest(error=error):
                def fail():
                    raise error
                self.assertEqual(weather.build_output(fail, self.now), {"text": "", "tooltip": ""})

    def test_fetcher_bounds_network_work(self):
        with patch.object(weather.subprocess, "run") as run:
            run.return_value.stdout = json.dumps(self.payload).encode()
            self.assertEqual(weather.fetch_weather(), self.payload)
            args, kwargs = run.call_args
            command = args[0]
            for option, value in (
                ("--proto", "=https"),
                ("--connect-timeout", str(weather.CONNECT_TIMEOUT_SECONDS)),
                ("--max-time", str(weather.REQUEST_TIMEOUT_SECONDS)),
                ("--retry", "0"),
                ("--max-filesize", str(weather.MAX_RESPONSE_BYTES)),
            ):
                self.assertEqual(command[command.index(option) + 1], value)
            self.assertEqual(command[-1], weather.STATION_URL)
            self.assertTrue(kwargs["capture_output"])
            self.assertEqual(kwargs["timeout"], weather.REQUEST_TIMEOUT_SECONDS + 2)

    def test_fetcher_does_not_retry_failure(self):
        with patch.object(
            weather.subprocess, "run",
            side_effect=subprocess.TimeoutExpired("curl", 10),
        ) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                weather.fetch_weather()
            run.assert_called_once()
