from datetime import datetime

import pytest

from google_calendar_client import GoogleOAuthError, _build_event_payload, _format_oauth_error


def test_build_event_payload_includes_default_attendee() -> None:
    payload = _build_event_payload(
        summary="Grabación S04E36/37 - Sara Luna",
        start=datetime.fromisoformat("2026-04-06T20:00:00+02:00"),
        end=datetime.fromisoformat("2026-04-06T22:00:00+02:00"),
        location="Beer Station",
        description="Test event",
    )

    assert payload["attendees"] == [{"email": "cmilender@gmail.com"}]


def test_format_oauth_error_includes_google_error_details() -> None:
    class Response:
        status_code = 400
        text = ""

        def json(self) -> dict:
            return {
                "error": "invalid_grant",
                "error_description": "Token has been expired or revoked.",
            }

    message = _format_oauth_error(Response())

    assert message == (
        "Google OAuth token request failed (400): "
        "invalid_grant: Token has been expired or revoked."
    )


def test_get_access_token_raises_google_oauth_error_with_details() -> None:
    class Response:
        ok = False
        status_code = 400
        text = ""

        def json(self) -> dict:
            return {"error": "invalid_client"}

    class Session:
        def post(self, *args, **kwargs) -> Response:
            return Response()

    from google_calendar_client import GoogleCalendarClient

    client = GoogleCalendarClient("client-id", "client-secret", "refresh-token")
    client.session = Session()

    with pytest.raises(
        GoogleOAuthError,
        match=r"Google OAuth token request failed \(400\): invalid_client",
    ):
        client._get_access_token()
