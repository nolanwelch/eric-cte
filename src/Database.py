import os
import sqlite3
import time
from csv import DictReader
from datetime import datetime, timedelta, timezone
from logging import Logger

import requests
from Booking import Booking
from Employee import Employee
from PID import PID
from Singleton import Singleton

BOOKEO_FETCH_DELAY_SECS = 300
CLEAR_DELAY_SECS = 86_400  # 24 hrs


class Database(metaclass=Singleton):
    ZULU_FORMAT = r"%Y-%m-%dT%H:%M:00Z"
    ON_CAMPUS_CATEGORY_IDS = ["MPJWRE", "PJNEYX"]

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
            q = f"DELETE FROM bookings WHERE startTime<{time.time()}"
            self._cur.execute(q)
            self._conn.commit()
        except Exception as e:
            self._logger.error(f"Error when purging stale bookings: {e}")

    def _zulu_to_datetime(cls, timestamp: str) -> datetime:
        """Converts a timestamp in Zulu format to a datetime object"""
        return datetime.strptime(timestamp, cls.ZULU_FORMAT)

    def _datetime_to_zulu(cls, timestamp: datetime) -> str:
        """Converts a datetime object to a Zulu-formatted timestamp"""
        return timestamp.strftime(cls.ZULU_FORMAT)

    @_ttl
    def fetch_new_bookings(self, delta: timedelta):
        """Uses the Bookeo API to fetch all bookings scheduled between now and (now + delta)
        and updates the local database with booking and on-campus PID information"""
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

            for b in data:
                bookingid = {int(b["bookingNumber"])}
                on_campus_pids = [
                    PID(
                        self._extract_pid_from_custom_fields(
                            p["personDetails"]["customFields"]
                        ),
                        p["personDetails"]["firstName"],
                        p["personDetails"]["lastName"],
                    )
                    for p in b["participants"]["details"]
                    if p["peopleCategoryId"] in self.ON_CAMPUS_CATEGORY_IDS
                ]
                q = f"""INSERT INTO bookings (id, timestamp)
                    SELECT ({bookingid}, {datetime.fromisoformat(b["startTime"]).astimezone(timezone.utc)})
                    WHERE NOT EXISTS
                        (SELECT id
                        FROM bookings
                        WHERE id={bookingid})"""
                self._cur.execute(q)

                q = f"""INSERT INTO pids (pid, firstName, lastName, bookingID)
                    VALUES (? ? ? ?)"""
                self._cur.executemany(
                    q,
                    [
                        (p.id, p.first_name, p.last_name, bookingid)
                        for p in on_campus_pids
                    ],
                )

            self._conn.commit()
            self._last_fetch = current_time
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
    def get_on_campus_pids(self, booking: Booking) -> list[PID]:
        """Uses the local database to return the on-campus PIDs associated with the given Booking"""
        try:
            q = f"""SELECT (pid, firstName, lastName)
            FROM pids
            WHERE bookingId={booking.id}"""
            pids = self._cur.execute(q).fetchall()
            return [PID(p[0], p[1], p[2]) for p in pids]
        except Exception as e:
            self._logger.error(f"Error fetching new on-campus PIDs: {e}")
            return []

    def is_on_campus_student(self, pid: PID) -> bool:
        """Checks if the given PID is in the list of on-campus students"""
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
    def get_slackid(self, slingid: int) -> str:
        """Returns the Slack ID of the employee matching the given Sling ID"""
        try:
            q = f"""SELECT slackID
                FROM employees
                WHERE slingId={slingid}"""
            return self._cur.execute(q).fetchone()[0]
        except Exception as e:
            self._logger.error(f"Error when getting Slack ID for {slingid}: {e}")
            return ""

    @_ttl
    def remove_pid(self, pid: PID):
        """Remove the given PID from the local database"""
        try:
            q = f"DELETE FROM pids WHERE pid={pid.id}"
            self._cur.execute(q)
            self._conn.commit()
        except Exception as e:
            self._logger.error(f"Error when removing record for PID {pid}: {e}")

    @_ttl
    def get_upcoming_bookings(
        self, delta: timedelta = timedelta(weeks=1)
    ) -> list[Booking]:
        """Uses the local database to return all Bookings scheduled between now and (now + delta)"""
        try:
            t = time.time()
            q = f"""SELECT (id, timestamp)
                FROM bookings
                WHERE timestamp BETWEEN {t} AND {t+delta}"""
            bookings = self._cur.execute(q).fetchall()
            return [
                Booking(b[0], datetime.fromtimestamp(b[1]), self.get_on_campus_pids(b))
                for b in bookings
            ]
        except Exception as e:
            self._logger.error(f"Error when fetching upcoming bookings: {e}")
            return []
