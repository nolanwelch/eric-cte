import os
import sys
import unittest as ut

# https://machinelearningmastery.com/a-gentle-introduction-to-unit-testing-in-python/
# TODO: Write tests for Database and SlackApp classes
# TODO: Add test.py to the run bash script once finished


# Tests done!
class TestSecrets(ut.TestCase):
    def test_get_secrets(self):
        from app import get_secrets

        secrets = get_secrets("config.env")
        self.assertIsInstance(secrets, dict)

        with self.assertRaises(OSError):
            get_secrets("invalidpath")

    def test_validate_secrets(self):
        from app import validate_secrets

        validate_secrets({"foo": "bar", "test": "case"}, ["foo", "test"])
        validate_secrets({"foo": "bar", "test": "case"}, ["foo"])

        with self.assertRaises(KeyError):
            validate_secrets({"foo": "bar"}, ["foo", "test"])
        with self.assertRaises(ValueError):
            validate_secrets({"foo": "bar", "test": ""}, ["foo", "test"])


# Tests done!
class TestBooking(ut.TestCase):
    def test_booking_init(self):
        from datetime import datetime

        from Booking import Booking

        now = datetime.now()
        pids = [1, 2, 3]

        booking = Booking(123456789, now, pids)
        self.assertEqual(booking.id, 123456789)
        self.assertEqual(booking.start_datetime, now)
        self.assertEqual(booking.on_campus_pids, pids)

        with self.assertRaises(ValueError):
            Booking(-1, now, [])
        with self.assertRaises(TypeError):
            Booking(123456789, None, [])
        with self.assertRaises(TypeError):
            Booking(123456789, 200, [])


# Tests done!
class TestEmployee(ut.TestCase):
    def test_employee_init(self):
        from Employee import Employee

        id = 123456789

        employee = Employee("Foo", "Bar", id)
        self.assertEqual(employee.first_name, "Foo")
        self.assertEqual(employee.last_name, "Bar")
        self.assertEqual(employee.employee_id, id)

        with self.assertRaises(ValueError):
            Employee("", "Bar", 123456789)
        with self.assertRaises(ValueError):
            Employee("Foo", "", 123456789)
        with self.assertRaises(ValueError):
            Employee("Foo", "Bar", -1)


# Tests done!
class TestPID(ut.TestCase):
    def test_pid_init(self):
        from PID import PID

        id = 123456789

        pid = PID(id, "Foo", "Bar")
        self.assertEqual(pid.id, id)
        self.assertEqual(pid.first_name, "Foo")
        self.assertEqual(pid.last_name, "Bar")

        with self.assertRaises(ValueError):
            PID(-1, "Foo", "Bar")
        with self.assertRaises(ValueError):
            PID(123456789, "", "Bar")
        with self.assertRaises(ValueError):
            PID(123456789, "Foo", "")


# Tests done!
class TestMessage(ut.TestCase):
    def test_message_init(self):
        from datetime import datetime

        from SlackApp import Message

        now = datetime.now()
        channel_id = "U1234567890"

        m = Message(channel_id, now, "foo")
        self.assertEqual(m.resolved_channel_id, channel_id)
        self.assertEqual(m.timestamp, now)
        self.assertEqual(m.message, "foo")

        Message(channel_id, now, 3000)
        Message(channel_id, now, [x for x in range(30)])

        with self.assertRaises(ValueError):
            Message("", now, "foo")
        with self.assertRaises(TypeError):
            Message(channel_id, None, "foo")
        with self.assertRaises(TypeError):
            Message(channel_id, 200, "foo")
        with self.assertRaises(TypeError):
            Message(channel_id, now, None)


class TestDatabase(ut.TestCase):
    def test_valid_database_init(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )
        self.assertIs(db._logger, logger)
        self.assertEqual(db._bookeo_secret_key, s["BOOKEO_SECRET_KEY"])
        self.assertEqual(db._bookeo_api_key, s["BOOKEO_API_KEY"])
        self.assertEqual(db._db_filepath, s["CTE_DB_PATH"])
        self.assertEqual(db._roster_filepath, s["CAMPUS_ROSTER_PATH"])

    def test_invalid_database_init(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        with self.assertRaises(IOError):
            Database(logger, "invalidpath", s["CAMPUS_ROSTER_PATH"], "X", "X")
        with self.assertRaises(IOError):
            Database(logger, s["CTE_DB_PATH"], "invalidpath", "X", "X")
        with self.assertRaises(ValueError):
            Database(logger, s["CTE_DB_PATH"], s["CAMPUS_ROSTER_PATH"], "", "X")
        with self.assertRaises(ValueError):
            Database(logger, s["CTE_DB_PATH"], s["CAMPUS_ROSTER_PATH"], "X", "")
        with self.assertRaises(IOError):
            Database(logger, "invalidfile", s["CAMPUS_ROSTER_PATH"], "X", "X")
        with self.assertRaises(IOError):
            Database(logger, "invalidheader", s["CAMPUS_ROSTER_PATH"], "X", "X")
        with self.assertRaises(IOError):
            Database(logger, "invalid.sqlite3", s["CAMPUS_ROSTER_PATH"], "X", "X")

    def test_clear(self):
        from datetime import datetime, timezone
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )

        id = 9999999
        dt = datetime.fromtimestamp(0).astimezone(timezone.utc)
        dt = dt.timestamp()
        db._cur.execute(
            "INSERT INTO bookings (id, timestamp, lastChange) VALUES (?, ?, ?)",
            (id, dt, dt),
        )
        db._conn.commit()
        db._clear()
        res = db._cur.execute("SELECT * FROM bookings WHERE id=?", (id,)).fetchone()
        self.assertIsNone(res)

    def test_zulu_to_datetime(self):
        from datetime import datetime

        from Database import Database

        zulu = "1970-01-01T00:00:00Z"
        dt = datetime(1970, 1, 1, 0, 0, 0)
        self.assertEqual(Database._zulu_to_datetime(zulu), dt)

    def test_datetime_to_zulu(self):
        from datetime import datetime

        from Database import Database

        zulu = "1970-01-01T00:00:00Z"
        dt = datetime(1970, 1, 1, 0, 0, 0)
        self.assertEqual(Database._datetime_to_zulu(dt), zulu)

    def test_retrieve_new_bookings(self):
        pass

    def test_extract_pid_from_custom_fields(self):
        pass

    def test_get_on_campus_pids(self):
        from datetime import datetime, timezone
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Booking import Booking
        from Database import Database
        from PID import PID
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )
        pids = [1, 2, 3, 4, 5]
        pids = [PID(x, "Foo", "Bar") for x in pids]
        b = Booking(1, datetime(2023, 7, 23, 12, 0).astimezone(timezone.utc), pids)

        q = """INSERT INTO bookings (id, timestamp, lastChange)
            VALUES (?, ?, ?)"""

        db._cur.execute(
            q, (b.id, b.start_datetime.timestamp(), datetime.now().timestamp())
        )

        db._cur.executemany(
            f"""INSERT INTO pids (pid, firstName, lastName, bookingID)
                VALUES (?, ?, ?, ?)""",
            [(p.id, p.first_name, p.last_name, b.id) for p in pids],
        )
        db._conn.commit()

        db_pids = db.get_on_campus_pids(b)
        db._cur.execute("DELETE FROM bookings WHERE id=?", (b.id,))
        db._cur.execute("DELETE FROM pids WHERE bookingID=?", (b.id,))
        db._conn.commit()
        self.assertEqual(db_pids, pids)

    def test_is_on_campus_student(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from PID import PID
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )
        p_1 = PID(17, "Nolan", "Welch")
        p_2 = PID(0, "Foo", "Bar")
        self.assertTrue(db.is_on_campus_student(p_1))
        self.assertFalse(db.is_on_campus_student(p_2))

    def test_get_admins(self):
        from datetime import datetime, timezone
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )

        admins = db.get_admins()
        self.assertEqual(len(admins), 1)
        admin = admins[0]
        self.assertEqual(admin.first_name, "Nolan")
        self.assertEqual(admin.last_name, "Welch")
        self.assertEqual(admin.employee_id, 13051138)

    def test_get_slack_id(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )

        self.assertEqual(db.get_slack_id(13051138), "U04LJEPH7GT")
        self.assertEqual(db.get_slack_id(-1), "")

    def test_remove_pid(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from PID import PID
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )

        pid_1 = PID(17, "foo", "bar")
        pid_2 = PID(29, "lorem", "ipsum")

        q = """INSERT INTO pids (firstName, lastName, pid, bookingID)
        VALUES (?, ?, ?, ?)"""
        db._cur.execute(q, (pid_1.first_name, pid_1.last_name, pid_1.id, 1))
        db._cur.execute(q, (pid_2.first_name, pid_2.last_name, pid_2.id, 2))
        db._conn.commit()

        db.remove_pid(pid_1)

        q = """SELECT firstName, lastName, pid
        FROM pids
        WHERE pid=?"""
        res = db._cur.execute(q, (pid_1.id,)).fetchone()
        self.assertIsNone(res)
        res = db._cur.execute(q, (pid_2.id,)).fetchone()
        self.assertEqual(res[0], pid_2.first_name)
        self.assertEqual(res[1], pid_2.last_name)
        self.assertEqual(res[2], pid_2.id)

        q = """DELETE FROM pids
        WHERE pid=?"""
        db._cur.execute(q, (pid_2.id,))
        db._conn.commit()

    def test_get_upcoming_bookings(self):
        from datetime import datetime, timedelta, timezone
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )

        now = datetime.now()
        dt = now + timedelta(days=2)
        dt = dt.astimezone(timezone.utc)

        q = """INSERT INTO bookings (id, timestamp, lastChange)
        VALUES (?, ?, ?)"""
        db._cur.execute(q, (1967, dt.timestamp(), now))
        db._conn.commit()

        b_1 = db.get_upcoming_bookings(timedelta(days=3))
        b_2 = db.get_upcoming_bookings(timedelta(days=1))

        q = """DELETE FROM bookings
        WHERE id=?"""
        db._cur.execute(q, (1967,))
        db._conn.commit()

        self.assertEqual(len(b_1), 1)
        self.assertEqual(b_1[0].id, 1967)
        self.assertEqual(b_1[0].start_datetime, dt)
        self.assertEqual(len(b_2), 0)

    def test_delete_if_lastchange_stale(self):
        pass

    def test_mark_employee_notified(self):
        pass

    def test_get_employee_message(self):
        pass


# Tests done!
class TestSlackApp(ut.TestCase):
    def test_valid_slack_init(self):
        from datetime import time
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=21)
        qh_end = time(hour=8)

        slack = SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)
        self.assertIs(slack._logger, logger)
        self.assertEqual(slack._token, s["SLACK_BOT_TOKEN"])
        self.assertEqual(slack._quiet_hours_start, qh_start)
        self.assertEqual(slack._quiet_hours_end, qh_end)

    def test_invalid_slack_init(self):
        from datetime import time
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=21)
        qh_end = time(hour=8)

        with self.assertRaises(TypeError):
            SlackApp(logger, s["SLACK_BOT_TOKEN"], None, qh_end)
        with self.assertRaises(TypeError):
            SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, None)
        with self.assertRaises(ValueError):
            qh_start = time(hour=12)
            qh_end = time(hour=12)
            SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)
        with self.assertRaises(ValueError):
            qh_start = time(hour=15)
            qh_end = time(hour=16)
            SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)

    def test_in_quiet_hours(self):
        from datetime import datetime, time
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=21)
        qh_end = time(hour=8)

        slack = SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)
        self.assertTrue(slack.in_quiet_hrs(datetime(2022, 5, 29, 5)))
        self.assertFalse(slack.in_quiet_hrs(datetime(2022, 5, 29, 10)))

    def test_send_message(self):
        if not send_messages:
            return

        from datetime import datetime, time
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=11, minute=59)
        qh_end = time(hour=0)

        slack = SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)
        slack.send_message("U05F0L9LN3G", f"Test at {datetime.now()}")

    def test_send_multiple(self):
        if not send_messages:
            return

        from datetime import datetime, time
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=11, minute=59)
        qh_end = time(hour=0)

        slack = SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)
        slack.send_multiple(
            ["U05F0L9LN3G", "U05F0L9LN3G"], f"Multiple test at {datetime.now()}"
        )

    def test_schedule_message(self):
        if not send_messages:
            return

        from datetime import datetime, time, timedelta
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=11, minute=59)
        qh_end = time(hour=0)
        dt = datetime.now() + timedelta(seconds=30)

        slack = SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)

        slack.schedule_message(
            "U05F0L9LN3G", dt, f"Test at {datetime.now()} scheduled for {dt}"
        )

    def test_message_has_reaction(self):
        from datetime import datetime, time, timezone
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import Message, SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=11, minute=59)
        qh_end = time(hour=0)

        dt = datetime.fromtimestamp(1691438364.990979)
        dt = dt.astimezone(timezone.utc)

        slack = SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)

        message = Message(
            "D05F7BU02Q2",
            dt,
            "React to this message.",
        )

        self.assertTrue(slack.message_has_reaction(message, "+1"))
        self.assertFalse(slack.message_has_reaction(message, "grin"))

    def test_fetch_timestamp(self):
        from datetime import datetime, time, timezone
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import Message, SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=11, minute=59)
        qh_end = time(hour=0)

        slack = SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)

        approx_ts = datetime.fromtimestamp(1691438365)
        approx_ts = approx_ts.astimezone(timezone.utc)

        ts_1 = slack.fetch_timestamp(
            Message(
                "D05F7BU02Q2",
                approx_ts,
                "React to this message.",
            )
        )
        correct_ts = datetime.fromtimestamp(1691438364.990979)
        correct_ts = correct_ts.astimezone(timezone.utc)
        self.assertEqual(ts_1, correct_ts)

        ts_2 = slack.fetch_timestamp(Message("D05F7BU02Q2", approx_ts, "foo bar"))
        self.assertIsNone(ts_2)

        self.assertIsNone(slack.fetch_timestamp(None))

    def test_update_message(self):
        from datetime import datetime, time, timezone
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import Message, SlackApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=11, minute=59)
        qh_end = time(hour=0)

        slack = SlackApp(logger, s["SLACK_BOT_TOKEN"], qh_start, qh_end)

        approx_ts = datetime.fromtimestamp(1691438365)
        approx_ts = approx_ts.astimezone(timezone.utc)

        msg_1 = slack.update_message(
            Message(
                "D05F7BU02Q2",
                approx_ts,
                "React to this message.",
            )
        )
        correct_ts = datetime.fromtimestamp(1691438364.990979)
        correct_ts = correct_ts.astimezone(timezone.utc)
        self.assertEqual(msg_1.timestamp, correct_ts)

        msg_2 = slack.update_message(Message("D05F7BU02Q2", approx_ts, "foo bar"))
        self.assertIsNone(msg_2)

        self.assertIsNone(slack.update_message(None))


# Tests done!
class TestSlingApp(ut.TestCase):
    def test_valid_sling_init(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        sling = SlingApp(logger, s["SLING_USERNAME"], s["SLING_PASSWORD"])
        self.assertIs(sling._logger, logger)

    def test_invalid_sling_init(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        with self.assertRaises(ValueError):
            SlingApp(logger, "foo", "bar")

    def test_fetch_employee_from_id(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Employee import Employee
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        sling = SlingApp(logger, s["SLING_USERNAME"], s["SLING_PASSWORD"])
        employee = sling._fetch_employee_from_id(13449876)
        self.assertIsInstance(employee, Employee)
        self.assertEqual(employee.first_name, "Haven")
        self.assertEqual(employee.last_name, "Biddix")

        self.assertIsNone(sling._fetch_employee_from_id(0))

    def test_fetch_scheduled_employee(self):
        from datetime import datetime, timedelta, timezone
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        tz = timezone(timedelta(hours=-4))

        sling = SlingApp(logger, s["SLING_USERNAME"], s["SLING_PASSWORD"])
        dt = datetime(2023, 7, 29, 11, 45, tzinfo=tz)
        employee = sling.fetch_scheduled_employee(dt)
        self.assertEqual(employee.employee_id, 11896239)
        self.assertEqual(employee.first_name, "Sarah")
        self.assertEqual(employee.last_name, "Giang")

        dt = datetime(2017, 5, 14, tzinfo=tz)
        employee = sling.fetch_scheduled_employee(dt)
        self.assertIsNone(employee)

    def test_renew_session(self):
        from logging import INFO, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", level=INFO)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        sling = SlingApp(logger, s["SLING_USERNAME"], s["SLING_PASSWORD"])
        old_token = sling._token
        old_start_time = sling._session_start_time
        sling._renew_session()
        self.assertNotEqual(sling._token, old_token)
        self.assertGreater(sling._session_start_time, old_start_time)


def setup_db(filepath: str):
    import sqlite3

    if not os.path.exists(filepath):
        open(filepath, "a").close()

    conn = sqlite3.connect(filepath)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS "bookings" (
                "id" INTEGER NOT NULL UNIQUE,
                "timestamp" REAL NOT NULL,
                "msgChannelID" TEXT,
                "msgTimestamp" REAL,
                "msgText" TEXT,
                "employeeNotified" INTEGER DEFAULT 0,
                "lastChange" REAL NOT NULL,
                PRIMARY KEY("id")
                )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS "employees" (
	        "firstName"	TEXT NOT NULL,
        	"lastName"	TEXT NOT NULL,
        	"id" INTEGER NOT NULL UNIQUE,
        	"slackID" TEXT UNIQUE,
        	"isAdmin" INTEGER NOT NULL,
        	PRIMARY KEY("id")
            )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS "pids" (
            "pid" INTEGER NOT NULL,
            "firstName"	TEXT NOT NULL,
            "lastName" TEXT NOT NULL,
            "bookingID"	INTEGER NOT NULL,
            PRIMARY KEY("pid")
            )"""
    )

    cur.execute("DELETE FROM employees")
    cur.execute("DELETE FROM pids")
    cur.execute("DELETE FROM bookings")
    conn.commit()

    cur.execute(
        """INSERT INTO employees (firstName, lastName, id, slackID, isAdmin)
                VALUES ("Nolan", "Welch", 13051138, "U04LJEPH7GT", 1)"""
    )
    conn.commit()


def setup_roster(filepath: str):
    from csv import DictWriter

    with open(filepath, "w") as f:
        fields = ["lastName", "firstName", "PID"]
        writer = DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"lastName": "Welch", "firstName": "Nolan", "PID": 17})


def setup_invalid_files():
    import sqlite3

    with open("invalidfile", "w") as f:
        f.write("E")

    with open("invalidheader", "w") as f:
        f.write(
            "Lorem ipsum dolor sit amet,\ consectetur adipiscing elit,\
                  sed do eiusmod tempor incididunt ut labore\
                      et dolore magna aliqua"
        )

    db_path = "invalid.sqlite3"
    if not os.path.exists(db_path):
        open(db_path, "a").close()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS "bookings" (
	    "id" INTEGER,
    	PRIMARY KEY("id")
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS "employees" (
    	"id" INTEGER,
    	PRIMARY KEY("id")
        )"""
    )
    conn.commit()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    sys.path.append("..")
    send_messages = False
    setup_db("test.sqlite3")
    setup_roster("testroster.csv")
    setup_invalid_files()
    ut.main()
