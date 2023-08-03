import time
from datetime import datetime, timedelta
from logging import Logger

import requests
from Employee import Employee
from Singleton import Singleton

TTL_SECS = 86_400


class SlingApp(metaclass=Singleton):
    def __init__(self, logger: Logger, username: str, password: str):
        res = requests.post(
            "https://api.getsling.com/account/login",
            json={"email": username, "password": password},
        )
        if res.status_code == 200:
            self._logger = logger
            self._logger.info("Sling client authenticated")
            self._session_start_time = time.time()
            self._token = res.headers["authorization"]
        else:
            raise Exception("Invalid Sling credentials")

    def _renew_session(self):
        t = time.time()
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
            if time.time() - self.session_start_time > TTL_SECS:
                self._renew_session()
            return func(self, *args, **kwargs)

        return decorator

    @_ttl
    def fetch_scheduled_employee(self, start_time: datetime) -> Employee:
        """Returns the Employee object scheduled for the shift beginning at start_time"""
        try:
            start_timestamp = start_time.strftime(r"%Y-%m-%dT%H:%M:00Z")
            res = requests.get(
                "https://api.getsling.com/v1/reports/roster",
                headers={"Authorization": self._token},
                params={"dates": start_timestamp, "v": 2},
            )
            if res.status_code != 200:
                self._logger.error("Could not fetch employee ID from Sling")
                return None
            id = 0
            for event in res.json()["events"]:
                if (
                    datetime.fromisoformat(event["dtstart"]) == start_time
                    and event["status"] == "published"
                ):
                    id = event["user"]["id"]
            self._logger.info(f"Fetched ID for shift beginning {start_timestamp}")
            return self._fetch_employee_from_id(id)
        except Exception as e:
            self._logger.error(
                f"Error occurred when fetching scheduled employee from Sling: {e}"
            )
            return None

    @_ttl
    def _fetch_employee_from_id(self, employee_id: int) -> Employee:
        """Returns the Employee object matching a given user ID"""
        try:
            res = requests.get(
                f"https://api.getsling.com/v1/users/{employee_id}",
                headers={"Authorization": self._token},
            )
            if res.status_code != 200:
                self._logger.error(f"Could not fetch info for user {employee_id}")
                return None
            self._logger.info(f"Got info for user {employee_id}")
            e = res.json()
            return Employee(e["legalName"], e["lastname"], employee_id)
        except Exception as e:
            self._logger.error(f"Error occurred when fetching info for user: {e}")
            return None
