import os
import sqlite3
import time
from csv import DictReader
from datetime import datetime, timedelta
from logging import Logger

import requests
from Booking import Booking
from Employee import Employee
from PID import PID
from Singleton import Singleton

BOOKEO_FETCH_DELAY_SECS = 300
DB_TTL_SECS = 259_200  # 3 days
CLEAR_DELAY_SECS = 86_400  # 24 hrs

# TODO: Make sure that startTime is stored in Unix timestamp format everywhere. Currently in datetime format.


class Database(metaclass=Singleton):
    ZULU_FORMAT = r"%Y-%m-%dT%H:%M:00Z"
    ON_CAMPUS_STUDENT_IDS = ["MPJWRE", "PJNEYX"]

    def __init__(
        self,
        logger: Logger,
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
            self._logger = logger
            self._logger.info("Successfully connected to SQL database")
            self._db_filepath = db_filepath
            self._roster_filepath = roster_filepath
            self._bookeo_secret_key = bookeo_secret_key
            self._bookeo_api_key = bookeo_api_key
            self._last_fetch = -1
            self._last_clear = -1
        except:
            raise Exception("SQLite connection unsuccessful")

    def _ttl(func):
        """Decorator to check whether the database should be
        purged of old entries before executing the function"""

        def decorator(self, *args, **kwargs):
            if time.time() - self._last_clear > CLEAR_DELAY_SECS:
                self._clear()
            return func(self, *args, **kwargs)

        return decorator

    def _clear(self):
        try:
            q = f"DELETE FROM Bookings WHERE startTime<{time.time()-DB_TTL_SECS}"
            self._cur.execute(q)
            self._conn.commit()
        except Exception as e:
            self._logger.error(f"Error when purging old Bookings entries: {e}")

    def _zulu_to_datetime(cls, timestamp: str) -> datetime:
        """Converts a timestamp in Zulu format to a datetime object"""
        return datetime.strptime(cls.ZULU_FORMAT)

    def _datetime_to_zulu(cls, timestamp: datetime) -> str:
        """Converts a datetime object to a Zulu-formatted timestamp"""
        return timestamp.strftime(cls.ZULU_FORMAT)

    @_ttl
    def fetch_new_bookings(self, delta: timedelta) -> list[Booking]:
        """Uses the Bookeo API to fetch all bookings scheduled between now and (now + delta)"""
        if time.time() - self._last_fetch <= BOOKEO_FETCH_DELAY_SECS:
            return []
        try:
            current_time = datetime.now()
            res = requests.get(
                "https://api.bookeo.com/v2/bookings",
                params={
                    "startTime": self._datetime_to_zulu(current_time),
                    "endTime": self._datetime_to_zulu(current_time + delta),
                    "secretKey": self._bookeo_secret_key,
                    "apiKey": self._bookeo_api_key,
                    "expandParticipants": True,
                },
            )
            if res.status_code != 200:
                self._logger.error("Could not fetch bookings from Bookeo")
                return []

            data = res.json()["data"]
            self._logger.info(f"Fetched {len(data)} booking(s) from Bookeo")
            bookings = []
            for b in data:
                booking = Booking(
                    int(b["bookingNumber"]),
                    datetime.fromisoformat(b["startTime"]),
                    b["title"],
                    [
                        PID(
                            self._extract_pid_from_custom_fields(
                                p["personDetails"]["customFields"]
                            ),
                            p["personDetails"]["firstName"],
                            p["personDetails"]["lastName"],
                        )
                        for p in b["participants"["details"]]
                        if p["peopleCategoryId"] in self.ON_CAMPUS_STUDENT_IDS
                    ],
                )
                bookings.append(booking)
            return bookings
        except Exception as e:
            self._logger.error(
                f"Error occurred while fetching bookings from Bookeo: {e}"
            )

    def _extract_pid_from_custom_fields(self, custom_fields: dict) -> int:
        for f in custom_fields:
            if f["name"] == "PID":
                return f["value"]
        return 0

    @_ttl
    def update_database(self, entries: list[Booking]):
        try:
            # TODO: Update this method to use the Booking object. I'll need to find out which fields Bookeo returns to do this.
            data = [
                (e.id, self._datetime_to_zulu(e.start_time), e.employee_id, 0, 0, 0)
                for e in entries
            ]
            # TODO: Implement system to handle duplicates and check for changes
            q = "INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?)"
            self._cur.executemany(q, data)
            self._conn.commit()
            self._logger.info("Inserted bookings into database")
        except Exception as e:
            self._logger.error(f"Error when inserting bookings into database")

    @_ttl
    def fetch_new_on_campus_pids(self) -> dict[Booking, list[PID]]:
        """Uses the local database to return a map between Bookings and their associated on-campus PIDs"""
        try:
            # TODO: Write this method
            pass
        except Exception as e:
            self._logger.error(f"Error fetching new on-campus PIDs: {e}")
            return []

    def is_on_campus_student(self, pid: PID) -> bool:
        try:
            with open(self._roster_filepath, "r") as f:
                for row in DictReader(f):
                    if int(row["PID"]) == pid.id:
                        return True
            return False
        except Exception as e:
            self._logger.error(f"Error reading from PID file: {e}")
            return False

    @_ttl
    def get_admins(self) -> list[Employee]:
        """Returns all Employees that are marked as admins"""
        try:
            q = """SELECT (firstName, lastName, slackID)
                    FROM employees 
                    WHERE isAdmin=1"""
            res = self._cur.execute(q).fetchall()
            return [Employee(r[0], r[1], r[2]) for r in res]
        except Exception as e:
            self._logger.error(f"Error when getting admin Employee objects: {e}")
            return []

    @_ttl
    def get_employee(self, id: int) -> Employee:
        """Returns the employee matching the given id"""
        try:
            q = f"""SELECT (firstName, lastName, slackID)
            FROM employees
            WHERE id={id}"""
            res = self._cur.execute(q).fetchone()
            return Employee(res[0], res[1], res[2])
        except Exception as e:
            self._logger.error(f"Error when getting Employee object for id {id}: {e}")
            return None

    # Is this even necessary? There's no real reason to hold PIDs after admins have been notified.
    # TODO: Consider replacing this with a DELETE query and removing the adminNotified field.
    @_ttl
    def mark_pid_notified(self, pid: PID):
        try:
            q = f"UPDATE pids SET adminNotified=1 WHERE pid={pid.id}"
            self._cur.execute(q)
            self._conn.commit()
        except Exception as e:
            self._logger.error(f"Error when updating record for PID {pid}: {e}")

    @_ttl
    def get_upcoming_bookings(self, delta: timedelta) -> list[Booking]:
        """Uses the local database to return all Bookings scheduled between now and (now + delta)"""
        try:
            t = time.time()
            # TODO: Fill in appropriate fields once Booking class fields have been decided
            q = f"""SELECT (fields)
            FROM bookings
            WHERE startTime BETWEEN {t} AND {t+delta}"""
            res = self._cur.execute(q).fetchall()
            return [Booking(r[0]) for r in res]
        except Exception as e:
            self._logger.error(f"Error when fetching upcoming bookings: {e}")
            return []
