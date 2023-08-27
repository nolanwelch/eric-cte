import os
import sqlite3
from csv import DictReader
from datetime import datetime, timedelta, timezone
from logging import Logger

import requests
from Booking import Booking
from Employee import Employee
from PID import PID

CLEAR_DELAY = timedelta(days=1)
ZULU_FORMAT = r"%Y-%m-%dT%H:%M:00Z"
USERAGENT = "ERIC-CTE/1.0 (nolanwelch@outlook.com)"

# TODO: Split Bookeo and Database into two classes

# TIMESTAMP GUIDELINES (from https://stackoverflow.com/a/64886073/8344620)
# Reading:
#   in = datetime.datetime.fromtimestamp(posix_ts, timezone.utc)
# Writing:
#   out_0 = datetime.datetime.now(timezone.utc).timestamp()
#   out_1 = aware_dt.timestamp()

# You're currently working on implementing the above guidelines.


class Database:
    ON_CAMPUS_CATEGORY_IDS = ["MPJWRE", "PJNEYX"]
    DB_TABLES = ["employees", "bookings", "pids"]

    def __init__(
        self,
        logger: Logger,
        db_filepath: str,
        roster_filepath: str,
        bookeo_secret_key: str,
        bookeo_api_key: str,
    ):
        if not os.path.exists(db_filepath):
            raise IOError("Database filepath not found")
        elif not os.path.exists(roster_filepath):
            raise IOError("Roster filepath not found")
        elif "" in (bookeo_api_key, bookeo_secret_key):
            raise ValueError("Bookeo keys cannot be empty")
        elif os.path.getsize(db_filepath) < 100:
            raise IOError("Database file too small to be a SQLite file")
        with open(db_filepath, "rb") as f:
            if f.read(100)[:16].decode() != "SQLite format 3\x00":
                raise IOError("Database file is not a SQLite file")

        self._conn: sqlite3.Connection = sqlite3.connect(db_filepath)
        self._cur: sqlite3.Cursor = self._conn.cursor()
        self._logger = logger
        self._logger.info("Successfully connected to SQLite database")

        q = "SELECT tbl_name FROM sqlite_master WHERE type='table' AND tbl_name=?"
        for table in self.DB_TABLES:
            if self._cur.execute(q, (table,)).fetchone() is None:
                raise IOError(f"Table {table} not found in {db_filepath}")

        self._db_filepath = db_filepath
        self._roster_filepath = roster_filepath
        self._bookeo_secret_key = bookeo_secret_key
        self._bookeo_api_key = bookeo_api_key

    def clear(self):
        """Removes expired bookings from the local database"""
        now = datetime.now(timezone.utc).timestamp()
        q = "SELECT id FROM bookings WHERE timestamp<?"
        res = self._cur.execute(q, (now,)).fetchall()
        stale_ids = [(r[0],) for r in res]
        if stale_ids:
            self._cur.executemany("DELETE FROM bookings WHERE id=?", stale_ids)
            self._cur.executemany("DELETE FROM pids WHERE bookingID=?", stale_ids)
            self._conn.commit()

    def fetch_bookings(self, delta: timedelta, start: datetime = None) -> list[Booking]:
        """Use the Bookeo API to fetch all Bookings scheduled
        between start and (start + delta)"""
        if start is None:
            start = datetime.now(timezone.utc)
        res = requests.get(
            "https://api.bookeo.com/v2/bookings",
            params={
                "startTime": start.strftime(ZULU_FORMAT),
                "endTime": (start + delta).strftime(ZULU_FORMAT),
                "secretKey": self._bookeo_secret_key,
                "apiKey": self._bookeo_api_key,
                "expandParticipants": True,
                "itemsPerPage": 100,
            },
            headers={"User-Agent": USERAGENT},
        )
        if res.status_code != 200:
            self._logger.error("Could not fetch bookings from Bookeo")
            return []

        data = res.json()["data"]
        self._logger.info(f"Fetched {len(data)} booking(s) from Bookeo")

        bookings = []
        for b in data:
            on_campus_pids: list[PID] = []
            email = ""
            for p in b["participants"]["details"]:
                if p["personId"] == "PSELF":
                    email = p["personDetails"]["emailAddress"]
                if p["peopleCategoryId"] not in self.ON_CAMPUS_CATEGORY_IDS:
                    continue
                pid = self._extract_pid(p["personDetails"]["customFields"])
                first_name = p["personDetails"]["firstName"]
                last_name = p["personDetails"]["lastName"]
                on_campus_pids.append(PID(pid, first_name, last_name))

            id = int(b["bookingNumber"])

            if "lastChangeTime" in b.keys():
                last_change = datetime.fromisoformat(b["lastChangeTime"])
                self._delete_if_lastchange_stale(id, last_change)
            else:
                last_change = datetime.now(timezone.utc)

            bookings.append(
                Booking(
                    id,
                    datetime.fromisoformat(b["startTime"]),
                    on_campus_pids,
                    last_change,
                    email,
                )
            )

        return bookings

    def insert_new_bookings(self, bookings: list[Booking]):
        """Inserts only new bookings into the local database
        (determined by comparing booking IDs)"""
        q = "SELECT id FROM bookings"
        res = self._cur.execute(q).fetchall()
        local_ids = [r[0] for r in res]

        for b in bookings:
            if b.id in local_ids:
                continue
            timestamp = b.start.timestamp()
            last_change = b.last_change.timestamp()
            q = """INSERT INTO bookings (id, timestamp, lastChange, email)
                VALUES (?, ?, ?, ?)"""
            self._cur.execute(
                q,
                (b.id, timestamp, last_change, b.email),
            )
            q = """INSERT INTO pids (pid, firstName, lastName, bookingID)
                VALUES (?, ?, ?, ?)"""
            self._cur.executemany(
                q,
                [(p.id, p.first_name, p.last_name, b.id) for p in b.on_campus_pids],
            )

        self._conn.commit()

    # TODO: Rewrite this using Bookeo's "canceled" field
    def get_remove_canceled_bookings(self, delta: timedelta) -> list[Booking]:
        """Checks for any Bookings that are stored locally but no longer
        visible from the Bookeo API, indicating that the event was canceled.
        Also removes these Bookings from the local database."""
        api_bookings = self.fetch_bookings(delta)
        api_bookings_ids = [b.id for b in api_bookings]

        q = """SELECT id, timestamp, lastChange
        FROM bookings"""
        local_bookings = self._cur.execute(q).fetchall()
        local_bookings = [
            Booking(
                r[0],
                datetime.fromtimestamp(int(r[1]), timezone.utc),
                self.get_on_campus_pids(r[0]),
                datetime.fromtimestamp(int(r[2]), timezone.utc),
                "",
            )
            for r in local_bookings
        ]
        canceled_bookings = [b for b in local_bookings if b.id not in api_bookings_ids]
        canceled_ids = [(b.id,) for b in canceled_bookings]

        q = "DELETE FROM bookings WHERE id=?"
        self._cur.executemany(q, canceled_ids)
        q = "DELETE FROM pids WHERE bookingID=?"
        self._cur.executemany(q, canceled_ids)
        self._conn.commit()

        return canceled_bookings

    def _extract_pid(self, custom_fields: list[dict]) -> int:
        for f in custom_fields:
            if "name" in f.keys() and f["name"] == "PID":
                return int(f["value"]) or 0
        return 0

    def get_on_campus_pids(self, booking_id: int) -> list[PID]:
        """Returns the on-campus PIDs associated with a Booking"""
        q = """SELECT pid, firstName, lastName
            FROM pids
            WHERE bookingID=?"""
        pids = self._cur.execute(q, (booking_id,)).fetchall()
        return [PID(p[0], p[1], p[2]) for p in pids]

    def get_matching_pid(self, pid: PID) -> PID:
        with open(self._roster_filepath, "r") as f:
            for r in DictReader(f):
                if int(r["PID"]) == pid.id:
                    return PID(int(r["PID"], r["firstName"], r["lastName"]))
        return None

    def get_admins(self) -> list[Employee]:
        q = """SELECT firstName, lastName, id
            FROM employees
            WHERE isAdmin=1"""
        res = self._cur.execute(q).fetchall()
        return [Employee(r[0], r[1], r[2]) for r in res]

    def get_slack_id(self, employee_id: int) -> str:
        """Returns an Employee's Slack ID"""
        q = """SELECT slackID
            FROM employees
            WHERE id=?"""
        res = self._cur.execute(q, (employee_id,)).fetchone()
        if res is not None:
            return res[0]
        return ""

    def remove_pid(self, pid: PID):
        q = "DELETE FROM pids WHERE pid=?"
        self._cur.execute(q, (pid.id,))
        self._conn.commit()

    def get_upcoming_bookings(self, delta: timedelta) -> list[Booking]:
        """Returns all Bookings scheduled between now and (now + delta)"""
        t = datetime.now(timezone.utc)
        q = """SELECT id, timestamp, lastChange
            FROM bookings
            WHERE timestamp BETWEEN ? AND ?"""
        bookings = self._cur.execute(
            q, (t.timestamp(), (t + delta).timestamp())
        ).fetchall()

        return [
            Booking(
                b[0],
                datetime.fromtimestamp(b[1], timezone.utc),
                self.get_on_campus_pids(b[0]),
                b[2],
            )
            for b in bookings
        ]

    # TODO: Implement this method
    def get_changed_bookings(self, delta: timedelta) -> list[Booking]:
        return []

    def _delete_if_lastchange_stale(self, id: int, dt: datetime):
        """Removes the booking from the database if lastChange is older than dt"""
        ts = dt.timestamp()
        q = """SELECT * FROM bookings
            WHERE id=? AND lastChange<?"""
        res = self._cur.execute(q, (id, ts)).fetchall()
        if not res:
            return

        q = """DELETE FROM bookings
            WHERE id=? AND lastChange<?"""
        self._cur.execute(q, (id, ts))
        q = "DELETE FROM pids WHERE bookingID=?"
        self._cur.execute(q, (id,))
        self._conn.commit()

    def mark_admin_notified_pids(self, booking: Booking):
        q = """UPDATE bookings
            SET adminNotifiedPIDs=1
            WHERE id=?"""
        self._cur.execute(q, (booking.id,))
        self._conn.commit()

    def admin_notified_pids(self, booking: Booking) -> bool:
        q = """SELECT adminNotifiedPIDs
            FROM bookings
            WHERE id=?"""
        res = self._cur.execute(q, (booking.id,)).fetchone()
        return res[0] or False
