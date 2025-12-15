import datetime as dt

from schemas import LifeEvent
from services.report_services import upcoming_event


def test_upcoming_event_expands_time_period_into_daily_entries():
    events = [
        LifeEvent(
            aspect="Jup Opp Mer",
            eventType="MAJOR",
            aspectNature="Negative",
            timePeriod="2025-12-15 to 2025-12-16",
            startDate="2025-12-15",
            endDate="2025-12-16",
            exactDate="2025-12-13",
            description="{'en': ['A'], 'hi': ['अ']}",
        ),
        LifeEvent(
            aspect="Ura Tri Mer",
            eventType="MAJOR",
            aspectNature="Positive",
            timePeriod="2025-12-16 to 2025-12-16",
            startDate="2025-12-16",
            endDate="2025-12-16",
            exactDate="2025-12-17",
            description="plain text",
        ),
    ]

    out = upcoming_event(events, from_date=dt.date(2025, 12, 15))

    assert out == [
        {
            "date": "2025-12-15",
            "events": [
                {"aspect": "Jup Opp Mer", "aspectNature": "Negative", "description": {"en": ["A"], "hi": ["अ"]}},
            ],
        },
        {
            "date": "2025-12-16",
            "events": [
                {"aspect": "Jup Opp Mer", "aspectNature": "Negative", "description": {"en": ["A"], "hi": ["अ"]}},
                {"aspect": "Ura Tri Mer", "aspectNature": "Positive", "description": "plain text"},
            ],
        },
    ]


def test_upcoming_event_respects_to_date_clip():
    events = [
        LifeEvent(
            aspect="Sat Sxt Mer",
            eventType="MAJOR",
            aspectNature="Negative",
            timePeriod="2025-12-15 to 2025-12-20",
            startDate="2025-12-15",
            endDate="2025-12-20",
            exactDate="2025-12-17",
            description="x",
        ),
    ]

    out = upcoming_event(events, from_date=dt.date(2025, 12, 15), to_date=dt.date(2025, 12, 16))
    assert [row["date"] for row in out] == ["2025-12-15", "2025-12-16"]
