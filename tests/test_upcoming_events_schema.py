import datetime as dt

from schemas import LifeEvent, UpcomingEventsCalendarOut
from services.report_services import upcoming_event


def test_upcoming_events_calendar_out_model_accepts_upcoming_event_output():
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
        )
    ]

    calendar = upcoming_event(events, from_date=dt.date(2025, 12, 15))
    out = UpcomingEventsCalendarOut(data=calendar)
    assert len(out.data) == 2
    assert out.data[0].date == "2025-12-15"
    assert out.data[0].events[0].aspect == "Jup Opp Mer"
