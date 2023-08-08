from datetime import datetime

from PID import PID


class Booking:
    def __init__(
        self,
        id: int,
        start_datetime: datetime,
        on_campus_pids: list[PID],
    ):
        if id < 0:
            raise ValueError("Booking ID cannot be negative")
        elif start_datetime is None or not isinstance(start_datetime, datetime):
            raise TypeError("start_datetime must be a datetime")
        self.id = id
        self.start_datetime = start_datetime
        self.on_campus_pids = on_campus_pids

    def __eq__(self, other):
        return isinstance(other, Booking) and other.id == self.id
