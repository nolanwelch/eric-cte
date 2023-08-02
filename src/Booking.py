import datetime
from PID import PID


class Booking:
    # TODO: Flesh out this class with all necessary fields. All fields should be public (no name mangling)
    def __init__(
        self,
        id: int,
        start_datetime: datetime.datetime,
        customer_name: str,
        on_campus_pids: list[PID],
    ):
        self.id = id
        self.start_datetime = start_datetime
        self.customer_name = customer_name
        self.on_campus_pids = on_campus_pids
