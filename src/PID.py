class PID:
    def __init__(self, id: int, first_name: str, last_name: str):
        if id < 0:
            raise ValueError("PIDs cannot be negative")
        elif "" in (first_name, last_name):
            raise ValueError("Name cannot be empty")
        self.id = id
        self.first_name = first_name
        self.last_name = last_name

    def __eq__(self, other):
        return (
            isinstance(other, PID)
            and other.id == self.id
            and other.last_name == self.last_name
        )

    def __repr__(self):
        return f"PID({self.id}, {self.first_name}, {self.last_name})"
