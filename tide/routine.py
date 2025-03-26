import threading
import pickle
from loguru import logger
import time
from . import utils

RTN_SUBMITTING = 0
RTN_SUBMITTED = 1
RTN_SUCC = 2
RTN_FAIL = 3


class Routine:
    def __init__(self):
        self.id: str = ""
        self.fn_name: str = ""
        self.args: bytes = bytearray()
        self.result = None
        self.error: str = ''

        self.status = RTN_SUBMITTING

        self.submittedCond = threading.Condition()

        self.done = False
        self.doneCond = threading.Condition()

        self.data = False
        self.dataCond = threading.Condition()

    def __str__(self) -> str:
        return 'id={},fn_name={}'.format(self.id, self.fn_name)

    def exit(self, status):
        self.doneCond.acquire()
        self.done = True
        self.status = status
        self.doneCond.notify_all()
        self.doneCond.release()

    def submit_done(self):
        self.submittedCond.acquire()
        self.status = RTN_SUBMITTED
        self.submittedCond.notify_all()
        self.submittedCond.release()

    def wait_submitted(self):
        if self.status != RTN_SUBMITTING:
            return
        self.submittedCond.acquire()
        if self.status == RTN_SUBMITTING:
            self.submittedCond.wait()
        self.submittedCond.release()

    def set_data(self, data):
        self.dataCond.acquire()
        self.data = True
        if self.status == RTN_SUCC:
            # t0 = utils.time_ns()
            self.result = pickle.loads(data)
            # t1 = utils.time_ns()
            # logger.warning(f'pickle loads ret {(t1-t0)/1000000.}')
        else:
            self.error = data
        self.dataCond.notify_all()
        self.dataCond.release()

    def wait_done(self):
        if self.done:
            return
        self.doneCond.acquire()
        if not self.done:
            self.doneCond.wait()
        self.doneCond.release()
        
    def wait_data(self):
        if self.data:
            return
        self.dataCond.acquire()
        if not self.data:
            self.dataCond.wait()
        self.dataCond.release()