import datetime


class Booking:
    # TODO: Flesh out this class with all necessary fields.
    def __init__(self, id: int, start_time: datetime.datetime):
        self.id = id
        self.start_time = start_time

    def set_employee_id(self, id: int):
        self.employee_id = id
