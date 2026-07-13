"""
Google Calendar integration service.
Fetches upcoming events and returns formatted reminders.
"""

import datetime
import json
import os
import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import Config, OAUTH_FILE, CREDENTIALS_FILE

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarService:
    """Fetches events from Google Calendar."""

    def __init__(self, config: Config):
        self.config = config
        self._service = None
        self._last_events = []

    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API.
        Returns True if authenticated, False otherwise.
        """
        creds = None

        # Load saved token
        if OAUTH_FILE.exists():
            try:
                with open(OAUTH_FILE, "r") as f:
                    creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)
            except Exception:
                pass

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        # First time auth
        if not creds or not creds.valid:
            if not CREDENTIALS_FILE.exists():
                return False
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0, open_browser=True)
            except Exception:
                return False

            # Save token
            OAUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OAUTH_FILE, "w") as f:
                f.write(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        return True

    @property
    def is_authenticated(self) -> bool:
        return self._service is not None

    def get_upcoming_events(self, max_results: int = 10) -> list[dict]:
        """Fetch upcoming events from primary calendar."""
        if not self._service:
            return []

        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"
            end_of_day = (
                datetime.datetime.utcnow() + datetime.timedelta(hours=12)
            ).isoformat() + "Z"

            events_result = (
                self._service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    timeMax=end_of_day,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            self._last_events = events
            return events
        except Exception:
            return []

    def get_next_event(self) -> Optional[dict]:
        """Get the next upcoming event with its time."""
        events = self.get_upcoming_events(3)
        for event in events:
            start = event.get("start", {})
            start_time = start.get("dateTime") or start.get("date")
            if start_time:
                event["_parsed_start"] = start_time
                return event
        return None

    def format_events_summary(self, events: list[dict]) -> str:
        """Format events as a readable string for AI context."""
        if not events:
            return "Tidak ada acara di kalender untuk hari ini."

        lines = ["📅 Jadwal hari ini:"]
        for e in events:
            summary = e.get("summary", "(Tanpa judul)")
            start = e.get("start", {})
            start_time = start.get("dateTime") or start.get("date", "")
            if "T" in start_time:
                try:
                    dt = datetime.datetime.fromisoformat(start_time)
                    time_str = dt.strftime("%H:%M")
                except ValueError:
                    time_str = start_time
            else:
                time_str = "All day"

            lines.append(f"  • {time_str} — {summary}")

        return "\n".join(lines)

    def check_events_to_remind(self, minutes_before: int = 10) -> list[dict]:
        """Check if any event is starting within `minutes_before` minutes."""
        if not self._service:
            return []

        events = self.get_upcoming_events(5)
        now = datetime.datetime.now()
        now_utc = datetime.datetime.utcnow()
        upcoming = []

        for event in events:
            start = event.get("start", {})
            start_str = start.get("dateTime") or start.get("date")
            if not start_str or "T" not in start_str:
                continue

            try:
                event_time = datetime.datetime.fromisoformat(start_str)
                # Convert to local time if it has timezone
                diff = (event_time - now_utc).total_seconds() / 60
                if 0 <= diff <= minutes_before:
                    upcoming.append(event)
            except ValueError:
                continue

        return upcoming
