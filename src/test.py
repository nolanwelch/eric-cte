import os
import unittest as ut

from app import get_secrets, validate_secrets
from Booking import Booking
from Database import Database
from Employee import Employee
from Event import Event
from PID import PID
from SlackApp import SlackApp
from SlingApp import SlingApp
from datetime import datetime

# https://machinelearningmastery.com/a-gentle-introduction-to-unit-testing-in-python/


class TestSecrets(ut.TestCase):
    pass


class TestBooking(ut.TestCase):
    def test_valid_booking(self):
        now = datetime.now()
        booking = Booking(123456789, now, [])
        self.assertEqual(booking.id, 123456789)
        self.assertEqual(booking.start_datetime, now)
        self.assertEqual(booking.on_campus_pids, [])

    def test_invalid_booking(self):
        now = datetime.now()
        with self.assertRaises(ValueError):
            Booking(-1, now, [])
        with self.assertRaises(TypeError):
            Booking(123456789, None, [])


class TestEmployee(ut.TestCase):
    def test_valid_employee(self):
        employee = Employee("Foo", "Bar", 123456789)
        self.assertEqual(employee.first_name, "Foo")
        self.assertEqual(employee.last_name, "Bar")
        self.assertEqual(employee.employee_id, 123456789)

    def test_invalid_employee(self):
        with self.assertRaises(ValueError):
            Employee("", "Bar", 123456789)
        with self.assertRaises(ValueError):
            Employee("Foo", "", 123456789)
        with self.assertRaises(ValueError):
            Employee("Foo", "Bar", -1)


class TestEvent(ut.TestCase):
    pass


class TestPID(ut.TestCase):
    def test_valid_pid(self):
        pid = PID(123456789, "Foo", "Bar")
        self.assertEqual(pid.id, 123456789)
        self.assertEqual(pid.first_name, "Foo")
        self.assertEqual(pid.last_name, "Bar")

    def test_invalid_pid(self):
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
    pass


class TestSlackApp(ut.TestCase):
    pass


class TestSlingApp(ut.TestCase):
    pass


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    os.chdir("..")
    ut.main()
