import datetime
from Employee import Employee


class Booking:
    # TODO: Flesh out this class with all necessary fields. All fields should be public (no name mangling)
    def __init__(self, id: int, start_datetime: datetime.datetime):
        self.id = id
        self.start_datetime = start_datetime
