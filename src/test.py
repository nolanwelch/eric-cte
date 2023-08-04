import os
import unittest as ut


# https://machinelearningmastery.com/a-gentle-introduction-to-unit-testing-in-python/


class TestSecrets(ut.TestCase):
    def test_valid_secrets_path(self):
        from app import get_secrets

        secrets = get_secrets("config.env")
        self.assertIsInstance(secrets, dict)

    def test_invalid_secrets_path(self):
        from app import get_secrets

        with self.assertRaises(OSError):
            get_secrets("invalidpath")

    def test_valid_secrets_values(self):
        from app import validate_secrets

        try:
            validate_secrets({"foo": "bar", "test": "case"}, ["foo", "test"])
        except Exception as e:
            self.fail(f"validate_secrets raised {e} for a valid input")
        try:
            validate_secrets({"foo": "bar", "test": "case"}, ["foo"])
        except Exception as e:
            self.fail(f"validate_secrets raised {e} for input with extra dict pairs")

    def test_invalid_secrets_values(self):
        from app import validate_secrets

        with self.assertRaises(KeyError):
            validate_secrets({"foo": "bar"}, ["foo", "test"])
        with self.assertRaises(ValueError):
            validate_secrets({"foo": "bar", "test": ""}, ["foo", "test"])


class TestBooking(ut.TestCase):
    def test_valid_init(self):
        from Booking import Booking
        from datetime import datetime

        now = datetime.now()
        booking = Booking(123456789, now, [])
        self.assertEqual(booking.id, 123456789)
        self.assertEqual(booking.start_datetime, now)
        self.assertEqual(booking.on_campus_pids, [])

    def test_invalid_init(self):
        from Booking import Booking
        from datetime import datetime

        now = datetime.now()
        with self.assertRaises(ValueError):
            Booking(-1, now, [])
        with self.assertRaises(TypeError):
            Booking(123456789, None, [])


class TestEmployee(ut.TestCase):
    def test_valid_init(self):
        from Employee import Employee

        employee = Employee("Foo", "Bar", 123456789)
        self.assertEqual(employee.first_name, "Foo")
        self.assertEqual(employee.last_name, "Bar")
        self.assertEqual(employee.employee_id, 123456789)

    def test_invalid_init(self):
        from Employee import Employee

        with self.assertRaises(ValueError):
            Employee("", "Bar", 123456789)
        with self.assertRaises(ValueError):
            Employee("Foo", "", 123456789)
        with self.assertRaises(ValueError):
            Employee("Foo", "Bar", -1)


class TestEvent(ut.TestCase):
    pass


class TestPID(ut.TestCase):
    def test_valid_init(self):
        from PID import PID

        pid = PID(123456789, "Foo", "Bar")
        self.assertEqual(pid.id, 123456789)
        self.assertEqual(pid.first_name, "Foo")
        self.assertEqual(pid.last_name, "Bar")

    def test_invalid_init(self):
        from PID import PID

        with self.assertRaises(ValueError):
            PID(-1, "Foo", "Bar")
        with self.assertRaises(ValueError):
            PID(123456789, "", "Bar")
        with self.assertRaises(ValueError):
            PID(123456789, "Foo", "")


class TestSingleton(ut.TestCase):
    def test_unique_instance(self):
        from Singleton import Singleton

        class TestClass(metaclass=Singleton):
            pass

        instance_1 = TestClass()
        instance_2 = TestClass()
        self.assertIs(instance_1, instance_2)


class TestDatabase(ut.TestCase):
    def test_valid_init(self):
        from logging import Logger

        try:
            pass
        except Exception as e:
            self.fail(f"Database.__init__() raised {e} for a valid input")

    def test_invalid_init(self):
        from logging import Logger

        logger = Logger("test")


class TestSlackApp(ut.TestCase):
    pass


class TestSlingApp(ut.TestCase):
    pass


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    os.chdir("..")
    ut.main()
