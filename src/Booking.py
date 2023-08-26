from datetime import datetime

from PID import PID


class Booking:
    def __init__(
        self,
        id: int,
        start: datetime,
        on_campus_pids: list[PID],
        last_change: datetime,
        email,
    ):
        if id < 0:
            raise ValueError("Booking ID cannot be negative")
        elif not isinstance(start, datetime):
            raise TypeError("start must be a datetime")
        elif not isinstance(last_change, datetime):
            raise TypeError("last_change must be a datetime")
        self.id = id
        self.start = start
        self.on_campus_pids = on_campus_pids
        self.last_change = last_change
        self.email = email

    def __eq__(self, other):
        return isinstance(other, Booking) and other.id == self.id
