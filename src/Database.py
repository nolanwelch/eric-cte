import logging
import os
import sqlite3
import time
from csv import DictReader
from datetime import datetime, timedelta

import requests
from Booking import Booking
from Employee import Employee
from Singleton import Singleton

ZULU_FORMAT = r"%Y-%m-%dT%H:%M:00Z"
BOOKEO_FETCH_DELAY_SECS = 300


class Database(metaclass=Singleton):
    def __init__(
        self,
        db_filepath: str,
        roster_filepath: str,
        bookeo_secret_key: str,
        bookeo_api_key: str,
    ):
        if not os.path.exists(db_filepath):
            raise Exception("Database filepath not found")
        elif not os.path.exists(roster_filepath):
            raise Exception("Roster filepath not found")
        try:
            self._conn: sqlite3.Connection = sqlite3.connect(db_filepath)
            self._cur: sqlite3.Cursor = self._conn.cursor
            logging.info("Successfully connected to SQL database")
            self._db_filepath = db_filepath
            self._roster_filepath = roster_filepath
            self._bookeo_secret_key = bookeo_secret_key
            self._bookeo_api_key = bookeo_api_key
            self._last_fetch = -1
        except:
            raise Exception("SQLite connection unsuccessful")

    def fetch_bookings(self, delta: timedelta) -> list[Booking]:
        """Returns all bookings scheduled between now and (now + delta)"""
        if time.time() - self._last_fetch <= BOOKEO_FETCH_DELAY_SECS:
            return []
        current_time = datetime.now()
        bookings = requests.get(
            "https://api.bookeo.com/v2/bookings",
            params={
                "startTime": current_time.strftime(ZULU_FORMAT),
                "endTime": (current_time + delta).strftime(ZULU_FORMAT),
                "secretKey": self._bookeo_secret_key,
                "apiKey": self._bookeo_api_key,
            },
        )
        if bookings.status_code == 200:
            data = bookings.json()["data"]

            # TODO: Update this list comprehension once Booking class is fleshed out
            data["startTime"] = datetime.strptime(data["startTime"])
            logging.info(f"Fetched {len(data)} booking(s) from Bookeo")
            data = [Booking(0, d["startTime"]) for d in data]

            return data
        else:
            logging.error("Could not fetch bookings from Bookeo")
            return []

    def update_database(self, entries: list[Booking]):
        try:
            # TODO: Update this method to use the Booking object
            data = [
                (e.id, e.start_time.strftime(ZULU_FORMAT), e.employee_id, 0, 0, 0)
                for e in entries
            ]
            # TODO: Implement system to handle duplicates and check for changes
            q = "INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?)"
            res = self._cur.executemany(q, data)  # what does cur.executemany return?
            self._conn.commit()
            logging.info("Inserted bookings into database")
        except Exception as e:
            logging.error(f"Error when inserting bookings into database")

    def fetch_new_on_campus_pids() -> list[int]:
        pass

    def is_on_campus_student(self, pid: int) -> bool:
        try:
            with open(self._roster_filepath, "r") as f:
                for row in DictReader(f):
                    if int(row["PID"]) == pid:
                        return True
            return False
        except Exception as e:
            logging.error(f"Error reading from PID file: {e}")
            return False

    def get_admins(self) -> list[Employee]:
        # TODO: Rewrite this to use the Employee class
        """Return all employee entries that are marked as admins"""
        query = """SELECT (firstName, slackID)
                FROM employees 
                WHERE isAdmin=1"""
        return [
            {"firstName": r[0], "slackID": r[1]}
            for r in self._cur.execute(query).fetchall()
        ]
