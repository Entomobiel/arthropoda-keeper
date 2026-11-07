"""Tests voor taken en schattingen."""

from datetime import UTC, datetime, timedelta

from arthropoda_core.tasks import (
    compute_tasks,
    estimate_next_molt,
    expected_hatches,
    project,
)

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
VALUES = {"feeding_interval_days": 7, "cleaning_interval_days": 30}


def test_compute_tasks():
    tasks = {t.kind: t for t in compute_tasks("a", VALUES, {"feeding": T0}, T0, False)}
    assert set(tasks) == {"feeding", "cleaning"}
    assert tasks["feeding"].due == T0 + timedelta(days=7)
    assert tasks["cleaning"].due == T0 + timedelta(days=30)  # basis = aanschaf
    assert tasks["feeding"].uid == "a:feeding"
    assert tasks["cleaning"].journal_type == "spot_clean"


def test_feeding_paused_and_snooze():
    kinds = [t.kind for t in compute_tasks("a", VALUES, {}, T0, True)]
    assert kinds == ["cleaning"]
    snooze = T0 + timedelta(days=10)
    (feed, _) = compute_tasks("a", VALUES, {}, T0, False, {"feeding": snooze})
    assert feed.due == snooze


def test_project():
    (feed, _) = compute_tasks("a", VALUES, {}, T0, False)
    dates = project(feed, T0 + timedelta(days=22))
    assert dates == [T0 + timedelta(days=d) for d in (7, 14, 21)]


def test_estimate_next_molt():
    assert estimate_next_molt([T0]) is None
    molts = [T0, T0 + timedelta(days=60), T0 + timedelta(days=150)]
    assert estimate_next_molt(molts) == T0 + timedelta(days=240)


def test_expected_hatches():
    entries = [
        ("egg_sac", T0, {}),
        ("hatch", T0 + timedelta(days=40), {}),
        ("ootheca", T0 + timedelta(days=50), {"incubation_days": 30}),
        ("egg_laying", T0 + timedelta(days=55), {}),
    ]
    result = expected_hatches(entries, [40, 50])
    assert [r[0] for r in result] == ["ootheca", "egg_laying"]
    _, laid, first, last = result[0]
    assert (first - laid).days == 30 and (last - laid).days == 30
    _, laid, first, last = result[1]
    assert ((first - laid).days, (last - laid).days) == (40, 50)
    assert expected_hatches([("egg_sac", T0, {})], None) == []
