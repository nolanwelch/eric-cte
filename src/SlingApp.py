import datetime
import logging
import time

import requests
from Singleton import Singleton


class SlingApp(metaclass=Singleton):
    def __init__(self, username: str, password: str, ttl_secs: int):
        auth = requests.post(
            "https://api.getsling.com/account/login",
            json={"email": username, "password": password},
        )
        if auth.status_code == 200:
            logging.info("Sling client authenticated")
            self.session_start_time = time.time()
            self.token = auth.headers["authorization"]
            self.ttl_secs = ttl_secs
        else:
            raise Exception("Invalid Sling credentials")

    def renew_session(self):
        t = time.time()
        new_auth = requests.post(
            "https://api.getsling.com/v1/account/session",
            headers={"Authorization": self.token},
        )
        if new_auth.status_code == 201:
            logging.info("Sling session renewed")
            self.session_start_time = t
            self.token = new_auth.headers["Authorization"]
        else:
            logging.error("Could not renew Sling session")

    def ttl(func):
        """Decorator to check whether the session must be
        renewed before executing the function"""

        def decorator(self, *args, **kwargs):
            if time.time() - self.session_start_time > self.ttl_secs:
                self.renew_session()
            return func(self, *args, **kwargs)

        return decorator

    @ttl
    def fetch_employee_id(self, start_time: datetime.datetime) -> int:
        t = start_time.strftime(r"%Y-%m-%dT%H:%M:00Z")
        date_span = t + "/P0Y0M0DT1H45M"
        date_span = "2023-06-30T11:45:00Z/P0Y0M0DT1H45M"  # for testing
        response = requests.get(
            "https://api.getsling.com/v1/reports/roster",
            headers={"Authorization": self.token},
            json={"dates": date_span, "v": 1},
        )
        if response.status_code == 200:
            logging.info(f"Fetched employee ID for shift beginning {t}")
            return response.json()  # TODO: Figure out specific field needed
        else:
            print(response.status_code)
            logging.error("Could not fetch employee ID from Sling")
            return -1
