import unittest as ut

import app as a

# https://machinelearningmastery.com/a-gentle-introduction-to-unit-testing-in-python/


class TestSecrets(ut.TestCase):
    pass


class TestBooking(ut.TestCase):
    pass


class TestEmployee(ut.TestCase):
    pass


class TestEvent(ut.TestCase):
    pass


class TestPID(ut.TestCase):
    pass


class TestSingleton(ut.TestCase):
    pass


class TestDatabase(ut.TestCase):
    pass


class TestSlackApp(ut.TestCase):
    pass


class TestSlingApp(ut.TestCase):
    pass


if __name__ == "__main__":
    a.os.chdir(a.os.path.dirname(a.os.path.realpath(__file__)))
    a.os.chdir("..")
    ut.main()
