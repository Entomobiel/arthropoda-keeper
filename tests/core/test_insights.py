"""Tests voor inzichten: voerweigering, vervelling, levensverwachting, kolonie."""

from datetime import UTC, date, datetime, timedelta

from arthropoda_core.insights import colony_trend, compute_insights, lifespan, refusal_streak

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
TODAY = date(2026, 11, 12)


def _d(days: float) -> datetime:
    return NOW - timedelta(days=days)


def _base(**kw):
    args = dict(can_molt=True, kind="individual", premolt=False, feeding_history=[],
                premolt_since=None, molt_times=[], next_molt=None, life=None,
                sex="unknown", stage="juvenile", counts=[], now=NOW)
    args.update(kw)
    return compute_insights(**args)


def _keys(insights):
    return [i["key"] for i in insights]


def test_refusal_streak():
    assert refusal_streak([]) == 0
    assert refusal_streak([("feeding_refused", _d(1)), ("feeding_refused", _d(5)), ("feeding", _d(9))]) == 2
    assert refusal_streak([("feeding", _d(1)), ("feeding_refused", _d(5))]) == 0


def test_premolt_suspected_and_refusing():
    two = [("feeding_refused", _d(1)), ("feeding_refused", _d(6))]
    assert _keys(_base(feeding_history=two)) == ["premolt_suspected"]
    # Al bevestigd in premolt → geen vermoeden meer
    assert _keys(_base(feeding_history=two, premolt=True)) == []
    # Dier dat niet vervelt: pas na 3 weigeringen een waarschuwing
    assert _keys(_base(feeding_history=two, can_molt=False)) == []
    three = two + [("feeding_refused", _d(11))]
    assert _keys(_base(feeding_history=three, can_molt=False)) == ["refusing_food"]
    # Kolonies niet
    assert _keys(_base(feeding_history=three, kind="colony")) == []


def test_premolt_long_and_molt_overdue():
    assert "premolt_long" in _keys(_base(premolt=True, premolt_since=_d(100)))
    assert "premolt_long" not in _keys(_base(premolt=True, premolt_since=_d(30)))
    # Laatste interval 60 d, verwacht 40 d geleden → ruim voorbij (> 30 d)
    molts = [_d(160), _d(100)]
    res = _base(molt_times=molts, next_molt=_d(40))
    assert _keys(res) == ["molt_overdue"] and res[0]["days"] == 40
    assert _keys(_base(molt_times=molts, next_molt=_d(10))) == []


def test_lifespan_by_sex_and_adult():
    info = {"lifespan": {"female_years": [20, 30], "male_years": [5, 7]}}
    female = lifespan(info, "female", "2020-01-01", None, "subadult", None, TODAY)
    assert female["basis"] == "age" and female["end_min"][:4] in ("2039", "2040")
    assert female["age_estimated"] is False and female["remaining_min_days"] > 0
    male = lifespan(info, "male", "2020-11-12", None, "adult", None, TODAY)
    assert male["end_max"].startswith("2027-11")
    # Geslacht onbekend: kortste tot langste
    unknown = lifespan(info, "unknown", "2020-01-01", None, None, None, TODAY)
    assert unknown["end_min"][:7] in ("2024-12", "2025-01") and unknown["end_max"][:4] in ("2049", "2050")
    # Geen geboortedatum: vanaf aankoop (schatting)
    est = lifespan(info, "female", None, "2024-06-01", None, None, TODAY)
    assert est["age_estimated"] is True
    # Levensduur als adult (bidsprinkhaan): telt vanaf de laatste vervelling
    mantis = {"lifespan": {"adult_months": [6, 8]}}
    adult = lifespan(mantis, "female", "2026-01-01", None, "adult", _d(30), TODAY)
    assert adult["basis"] == "adult" and 140 < adult["remaining_min_days"] < 160
    assert lifespan({}, "female", "2020-01-01", None, None, None, TODAY) is None


def test_lifespan_insights():
    info = {"lifespan": {"female_years": [20, 30], "male_years": [5, 7]}}
    male = lifespan(info, "male", (TODAY - timedelta(days=int(6.8 * 365.25))).isoformat(), None, "adult", None, TODAY)
    assert _keys(_base(life=male, sex="male", stage="adult")) == ["pairing_window"]
    old = lifespan(info, "male", "2018-01-01", None, "adult", None, TODAY)
    assert _keys(_base(life=old, sex="male", stage="adult")) == ["beyond_lifespan"]
    female = lifespan(info, "female", "2024-01-01", None, "juvenile", None, TODAY)
    assert _keys(_base(life=female, sex="female")) == ["lifespan"]


def test_colony_trend():
    assert colony_trend([(_d(5), 100)], NOW) is None
    falling = [(_d(40), 500), (_d(20), 420), (_d(2), 300)]
    trend = colony_trend(falling, NOW)
    assert trend["declining"] is True and trend["change"] == -0.4 and trend["days"] == 38
    res = _base(kind="colony", can_molt=False, counts=falling)
    assert _keys(res) == ["colony_declining"] and res[0]["level"] == "warn"
    growing = [(_d(30), 100), (_d(1), 160)]
    assert _keys(_base(kind="colony", can_molt=False, counts=growing)) == ["colony_trend"]
    # Trage daling over lange tijd: geen alarm
    slow = [(_d(200), 500), (_d(100), 400)]
    assert colony_trend(slow, NOW)["declining"] is False
