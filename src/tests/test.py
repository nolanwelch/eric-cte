import os
import sys
import unittest as ut

# https://machinelearningmastery.com/a-gentle-introduction-to-unit-testing-in-python/


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


class TestBooking(ut.TestCase):
    def test_booking_init(self):
        from datetime import datetime

        from Booking import Booking

        now = datetime.now()

        booking = Booking(123456789, now, [1, 2, 3])
        self.assertEqual(booking.id, 123456789)
        self.assertEqual(booking.start_datetime, now)
        self.assertEqual(booking.on_campus_pids, [1, 2, 3])

        with self.assertRaises(ValueError):
            Booking(-1, now, [])
        with self.assertRaises(TypeError):
            Booking(123456789, None, [])


class TestEmployee(ut.TestCase):
    def test_employee_init(self):
        from Employee import Employee

        employee = Employee("Foo", "Bar", 123456789)
        self.assertEqual(employee.first_name, "Foo")
        self.assertEqual(employee.last_name, "Bar")
        self.assertEqual(employee.employee_id, 123456789)

        with self.assertRaises(ValueError):
            Employee("", "Bar", 123456789)
        with self.assertRaises(ValueError):
            Employee("Foo", "", 123456789)
        with self.assertRaises(ValueError):
            Employee("Foo", "Bar", -1)


class TestEvent(ut.TestCase):
    pass


class TestPID(ut.TestCase):
    def test_pid_init(self):
        from PID import PID

        pid = PID(123456789, "Foo", "Bar")
        self.assertEqual(pid.id, 123456789)
        self.assertEqual(pid.first_name, "Foo")
        self.assertEqual(pid.last_name, "Bar")

        with self.assertRaises(ValueError):
            PID(-1, "Foo", "Bar")
        with self.assertRaises(ValueError):
            PID(123456789, "", "Bar")
        with self.assertRaises(ValueError):
            PID(123456789, "Foo", "")


class TestDatabase(ut.TestCase):
    def test_valid_database_init(self):
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", CRITICAL)
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
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        with self.assertRaises(OSError):
            Database(logger, "invalidpath", s["CAMPUS_ROSTER_PATH"], "X", "X")
        with self.assertRaises(OSError):
            Database(logger, s["CTE_DB_PATH"], "invalidpath", "X", "X")
        with self.assertRaises(ValueError):
            Database(logger, s["CTE_DB_PATH"], s["CAMPUS_ROSTER_PATH"], "", "")
        with self.assertRaises(IOError):
            # TODO: Make a database with invalid/missing table names
            Database(logger, "invalid.sqlite3", s["CAMPUS_ROSTER_PATH"], "X", "X")
        with self.assertRaises(IOError):
            raise IOError
        with self.assertRaises(KeyError):
            raise KeyError

    def test_clear(self):
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )
        db._cur.execute(
            """INSERT INTO bookings (id, timestamp)
            VALUES (9999999, 0)"""
        )
        db._conn.commit()
        db._clear()
        res = db._cur.execute(
            """SELECT *
            FROM bookings
            WHERE id=9999999"""
        ).fetchone()
        db._cur.execute(
            """DELETE FROM bookings
                        WHERE id=9999999"""
        )
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

    def test_fetch_new_bookings(self):
        pass

    def test_extract_pid_from_custom_fields(self):
        pass

    def test_get_on_campus_pids(self):
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Booking import Booking
        from datetime import datetime, timezone
        from Database import Database
        from PID import PID
        from Secrets import secret_keys

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        db = Database(
            logger,
            s["CTE_DB_PATH"],
            s["CAMPUS_ROSTER_PATH"],
            s["BOOKEO_SECRET_KEY"],
            s["BOOKEO_API_KEY"],
        )
        pids = {1, 2, 3, 4, 5}
        pids = {PID(x, "Foo", "Bar") for x in pids}
        b = Booking(1, datetime(2019, 7, 12, 0, 0), pids)
        db._cur.execute(
            f"""INSERT INTO bookings (id, timestamp)
                VALUES ({b.id}, {b.start_datetime.astimezone(timezone.utc)})"""
        )
        db._cur.executemany(
            f"""INSERT INTO pids (pid, firstName, lastName, bookingID)
                VALUES (? ? ? {b.id})""",
            [(p.id, p.first_name, p.last_name) for p in pids],
        )
        db._conn.commit()
        db_pids = db.get_on_campus_pids(b)
        db._cur.execute(f"DELETE FROM bookings WHERE id={b.id}")
        db._cur.execute(f"DELETE FROM pids WHERE bookingID={b.id}")
        db._conn.commit()
        self.assertEqual(db_pids, pids)

    def test_is_on_campus_student(self):
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from PID import PID
        from Database import Database
        from Secrets import secret_keys

        logger = Logger("test", CRITICAL)
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
        pass

    def test_get_slackid(self):
        pass

    def test_remove_pid(self):
        pass

    def test_get_upcoming_bookings(self):
        pass


class TestSlackApp(ut.TestCase):
    def test_valid_slack_init(self):
        from datetime import time
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import SlackApp

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=21)
        qh_end = time(hour=8)

        slack = SlackApp(
            logger, s["SLACK_BOT_TOKEN"], s["MSG_QUEUE_PATH"], qh_start, qh_end
        )
        self.assertIs(slack._logger, logger)
        self.assertEqual(slack._token, s["SLACK_BOT_TOKEN"])
        self.assertEqual(slack._message_queue_filepath, s["MSG_QUEUE_PATH"])
        self.assertEqual(slack._quiet_hours_start, qh_start)
        self.assertEqual(slack._quiet_hours_end, qh_end)

    def test_invalid_slack_init(self):
        from datetime import time
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlackApp import SlackApp

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        qh_start = time(hour=21)
        qh_end = time(hour=8)

        with self.assertRaises(IOError):
            SlackApp(logger, s["SLACK_BOT_TOKEN"], "invalidpath", qh_start, qh_end)
        with self.assertRaises(TypeError):
            SlackApp(logger, s["SLACK_BOT_TOKEN"], s["MSG_QUEUE_PATH"], None, None)
        with self.assertRaises(ValueError):
            qh_start = time(hour=12)
            qh_end = time(hour=12)
            SlackApp(
                logger, s["SLACK_BOT_TOKEN"], s["MSG_QUEUE_PATH"], qh_start, qh_end
            )
        with self.assertRaises(ValueError):
            qh_start = time(hour=15)
            qh_end = time(hour=16)
            SlackApp(
                logger, s["SLACK_BOT_TOKEN"], s["MSG_QUEUE_PATH"], qh_start, qh_end
            )


class TestSlingApp(ut.TestCase):
    def test_valid_sling_init(self):
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        sling = SlingApp(logger, s["SLING_USERNAME"], s["SLING_PASSWORD"])
        self.assertIs(sling._logger, logger)

    def test_invalid_sling_init(self):
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

    def test_fetch_employee_from_id(self):
        from datetime import timedelta, timezone
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Employee import Employee
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", CRITICAL)
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
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)
        tz = timezone(timedelta(hours=-4))

        sling = SlingApp(logger, s["SLING_USERNAME"], s["SLING_PASSWORD"])
        dt = datetime(2023, 7, 29, 11, 45, tzinfo=tz)
        employee = sling.fetch_scheduled_employee(dt)
        self.assertEqual(employee.employee_id, 11896239)
        self.assertEqual(employee.first_name, "Sarah")
        self.assertEqual(employee.last_name, "Giang")

        with self.assertRaises(ValueError):
            dt = datetime(2017, 5, 14, tzinfo=tz)
            sling.fetch_scheduled_employee(dt)

    def test_renew_session(self):
        from logging import CRITICAL, Logger

        from app import get_secrets, validate_secrets
        from Secrets import secret_keys
        from SlingApp import SlingApp

        logger = Logger("test", CRITICAL)
        s = get_secrets("config.env")
        validate_secrets(s, secret_keys)

        sling = SlingApp(logger, s["SLING_USERNAME"], s["SLING_PASSWORD"])
        old_token = sling._token
        sling._renew_session()
        self.assertNotEqual(sling._token, old_token)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    sys.path.append("..")
    ut.main()
