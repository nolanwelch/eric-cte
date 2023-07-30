import logging


class Event:
    EMPLOYEE_CONFIRMED = 0
    EMPLOYEE_UNCONFIRMED = 1

    def __init__(self, type: int):
        self._type = type

    def handle(self, ids: list[str]):
        """Handle this Event and send output to the given ids"""
        # TODO: Write the handle method
        match self._type:
            case Event.EMPLOYEE_CONFIRMED:
                pass
            case Event.EMPLOYEE_UNCONFIRMED:
                pass
            # ...
            case _:
                logging.error("The event is not of a recognized type")
