"""Tests voor de regelbeslissingen."""

from datetime import UTC, datetime, timedelta

from arthropoda_core import control as c

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def test_combine_ranges():
    assert c.combine_ranges([[22, 26], [24, 28]]) == ([24, 26], False)
    assert c.combine_ranges([[22, 24], None]) == ([22, 24], False)
    assert c.combine_ranges([None]) == (None, False)
    rng, conflict = c.combine_ranges([[18, 20], [26, 30]])
    assert conflict and rng == [22, 25]


def test_heater_thermostat():
    t = [24, 26]  # setpoint 25
    assert c.heater([24.0], t, 31, False, 0.5, False).on is True
    assert c.heater([25.8], t, 31, True, 0.5, False).on is False
    within = c.heater([25.2], t, 31, True, 0.5, False)
    assert within.on is True and within.reason == "within_hysteresis"
    assert c.heater([25.2], t, 31, False, 0.5, False).on is False


def test_heater_safety():
    t = [24, 26]
    over = c.heater([24.0, 31.5], t, 31, True, 0.5, False)
    assert (over.on, over.reason, over.critical) == (False, "over_safe_max", True)
    assert c.heater([24.0, 26.5], t, 31, True, 0.5, False).reason == "above_max"
    assert c.heater([], t, 31, True, 0.5, False).on is False
    assert c.heater([24.0], t, 31, True, 0.5, True).reason == "sensor_unavailable"
    assert c.heater([24.0], None, None, True, 0.5, False).on is None


def test_heater_proportional():
    t = [24, 26]
    assert c.heater([25.0], t, 31, False, 0.5, False, proportional=True).level == 50
    assert c.heater([23.0], t, 31, False, 0.5, False, proportional=True).level == 100
    cold = c.heater([27.0], t, 31, True, 0.5, False, proportional=True)
    assert (cold.on, cold.level) == (False, 0)


def test_mister():
    t = [60, 80]
    pause = timedelta(minutes=30)
    assert c.mister(50, t, NOW, None, 0, 6, pause, False).on is True
    assert c.mister(65, t, NOW, None, 0, 6, pause, False).reason == "humidity_ok"
    assert c.mister(50, t, NOW, NOW - timedelta(minutes=10), 1, 6, pause, False).reason == "pause"
    assert c.mister(50, t, NOW, None, 6, 6, pause, False).reason == "daily_limit"
    assert c.mister(None, t, NOW, None, 0, 6, pause, False).on is False
    assert c.mister(90, t, NOW, None, 9, 6, pause, True).reason == "schedule"


def test_fan():
    assert c.fan([24], 85, [22, 26], [60, 80], False).on is True
    assert c.fan([27], 70, [22, 26], [60, 80], False).reason == "temperature_high"
    assert c.fan([24], 70, [22, 26], [60, 80], True).on is False
    assert c.fan([24], 79, [22, 26], [60, 80], True).reason == "within_hysteresis"


def test_light_ramp():
    start = NOW.replace(hour=8)
    end = NOW.replace(hour=20)
    assert c.light(False, NOW, start, end, 30).on is False
    assert c.light(True, NOW, start, end, 0).level == 100
    assert c.light(True, start + timedelta(minutes=15), start, end, 30).level == 50
    assert c.light(True, end - timedelta(minutes=3), start, end, 30).reason == "sunset"


def test_parse_times():
    assert c.parse_times("08:00, 20:30;7:5, bla, 25:00") == [(8, 0), (20, 30), (7, 5)]
    assert c.parse_times(None) == []
