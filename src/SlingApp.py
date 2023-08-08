from datetime import datetime, timedelta, timezone
from logging import Logger

import requests
from Employee import Employee

SLING_TTL = timedelta(days=1)


class SlingApp:
    def __init__(self, logger: Logger, username: str, password: str):
        t = datetime.now()
        res = requests.post(
            "https://api.getsling.com/account/login",
            json={"email": username, "password": password},
        )
        if res.status_code == 200:
            self._logger = logger
            self._logger.info("Sling client authenticated")
            self._session_start_time = t
            self._token = res.headers["authorization"]
        else:
            raise ValueError("Could not validate Sling credentials")

    def _renew_session(self):
        t = datetime.now()
        res = requests.post(
            "https://api.getsling.com/v1/account/session",
            headers={"Authorization": self._token},
        )
        if res.status_code == 201:
            self._logger.info("Sling session renewed")
            self._session_start_time = t
            self._token = res.headers["Authorization"]
        else:
            self._logger.error("Could not renew Sling session")

    def _ttl(func):
        """Decorator to check whether the session must be
        renewed before executing the function"""

        def decorator(self, *args, **kwargs):
            if datetime.now() - self._session_start_time > SLING_TTL:
                self._renew_session()
            return func(self, *args, **kwargs)

        return decorator

    @_ttl
    def fetch_scheduled_employee(self, start_time: datetime) -> Employee:
        """Returns the Employee object scheduled for the shift beginning at start_time"""
        start_timestamp = start_time.strftime(r"%Y-%m-%dT%H:%M:00Z")
        res = requests.get(
            "https://api.getsling.com/v1/reports/roster",
            headers={"Authorization": self._token},
            params={"dates": start_timestamp, "v": 2},
        )
        if res.status_code != 200:
            self._logger.warning("Could not fetch employee ID from Sling")
            return None
        id = 0
        for event in res.json()["events"]:
            dtstart = datetime.fromisoformat(event["dtstart"])
            if dtstart == start_time and event["status"] == "published":
                id = event["user"]["id"]
        self._logger.info(f"Fetched ID for shift beginning {start_timestamp}")
        return self._fetch_employee_from_id(id)

    @_ttl
    def _fetch_employee_from_id(self, employee_id: int) -> Employee:
        """Returns the Employee object matching a given user ID"""
        res = requests.get(
            f"https://api.getsling.com/v1/users/{employee_id}",
            headers={"Authorization": self._token},
        )
        if res.status_code != 200:
            self._logger.warning(f"User {employee_id} not found")
            return None
        self._logger.info(f"Got info for user {employee_id}")
        e = res.json()
        return Employee(e["legalName"], e["lastname"], employee_id)
