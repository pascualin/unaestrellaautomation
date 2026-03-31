from datetime import datetime

from google_calendar_client import _build_event_payload


def test_build_event_payload_includes_default_attendee() -> None:
    payload = _build_event_payload(
        summary="Grabación S04E36/37 - Sara Luna",
        start=datetime.fromisoformat("2026-04-06T20:00:00+02:00"),
        end=datetime.fromisoformat("2026-04-06T22:00:00+02:00"),
        location="Beer Station",
        description="Test event",
    )

    assert payload["attendees"] == [{"email": "cmilender@gmail.com"}]
