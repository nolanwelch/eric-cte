class PID:
    def __init__(self, id: int, first_name: str, last_name: str):
        if id < 0:
            raise ValueError("PIDs cannot be negative")
        elif "" in (first_name, last_name):
            raise ValueError("Name cannot be empty")
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
