import datetime
from PID import PID


class Booking:
    def __init__(
        self,
        id: int,
        start_datetime: datetime.datetime,
        on_campus_pids: list[PID],
    ):
        if id < 0:
            raise ValueError("Booking ID cannot be negative")
        elif start_datetime is None:
            raise TypeError("Starting datetime cannot be None")
        self.id = id
        self.start_datetime = start_datetime
        self.on_campus_pids = on_campus_pids
