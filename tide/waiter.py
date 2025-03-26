from . import routine

class Waiter:
    def __init__(self, rtn: routine.Routine, with_data: bool):
        self.rtn = rtn
        self.with_data = with_data