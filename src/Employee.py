class Employee:
    def __init__(self, first_name: str, last_name: str, employee_id: int):
        if employee_id < 0:
            raise ValueError("Employee ID cannot be negative")
        elif "" in (first_name, last_name):
            raise ValueError("Name cannot be empty")
        self.first_name = first_name
        self.last_name = last_name
        self.employee_id = employee_id

    def __eq__(self, other):
        return isinstance(other, Employee) and other.employee_id == self.employee_id
