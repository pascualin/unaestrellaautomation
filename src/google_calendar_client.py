from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import requests


GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
DEFAULT_EVENT_DURATION_HOURS = 2
DEFAULT_EVENT_ATTENDEE_EMAILS = ["cmilender@gmail.com"]


@dataclass
class CalendarEventData:
    event_id: str
    html_link: str | None


class GoogleCalendarClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.session = requests.Session()

    def _get_access_token(self) -> str:
        response = self.session.post(
            GOOGLE_OAUTH_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ValueError("Google OAuth token response did not include access_token")
        return access_token

    def create_event(
        self,
        calendar_id: str,
        summary: str,
        start_datetime: str,
        location: str,
        description: str,
    ) -> CalendarEventData:
        start = _parse_iso_datetime(start_datetime)
        end = start + timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)
        access_token = self._get_access_token()

        response = self.session.post(
            GOOGLE_CALENDAR_EVENTS_URL.format(calendar_id=calendar_id),
            headers={"Authorization": f"Bearer {access_token}"},
            json=_build_event_payload(
                summary=summary,
                start=start,
                end=end,
                location=location,
                description=description,
            ),
            timeout=30,
        )
        response.raise_for_status()
        event = response.json()
        return CalendarEventData(
            event_id=event["id"],
            html_link=event.get("htmlLink"),
        )


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def _build_event_payload(
    summary: str,
    start: datetime,
    end: datetime,
    location: str,
    description: str,
) -> dict:
    return {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {"dateTime": _serialize_datetime(start)},
        "end": {"dateTime": _serialize_datetime(end)},
        "attendees": [{"email": email} for email in DEFAULT_EVENT_ATTENDEE_EMAILS],
    }
