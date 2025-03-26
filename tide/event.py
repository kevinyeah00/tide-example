from typing import List, Optional
from loguru import logger
import time
from . import utils

from .routine import Routine, RTN_FAIL, RTN_SUCC
from .proto.exec_ins import proto_pb2 as pb

EVT_WAIT_GET = 0
EVT_SUBMIT_ROUTINE = 2
EVT_EXIT = 3
EVT_INIT = 4


class Event:
    def __init__(self) -> None:
        self.type = 0
        self.with_data: bool = False
        self.ref_ids: List[str] = []
        self.result: bytes = bytearray()
        self.error: str = ""
        self.routine: Optional[Routine] = None
        self.status = 0

    @staticmethod
    def succ(result: bytes):
        evt = Event()
        evt.type = EVT_EXIT
        evt.status = RTN_SUCC
        evt.result = result
        return evt

    @staticmethod
    def fail(error: str):
        evt = Event()
        evt.type = EVT_EXIT
        evt.status = RTN_FAIL
        evt.error = error
        return evt


def unmarshal_event(data: bytes):
    # logger.opt(lazy=True).bind(ns=utils.time_ns()).debug("TideCtr: start unmarshaling event")
    evt_pb = pb.Event()
    evt_pb.ParseFromString(data)

    evt = Event()
    if evt_pb.type == pb.Event.Type.ROUTINE_SUBMIT:
        evt.type = EVT_SUBMIT_ROUTINE
        rtn = Routine()
        rtn.id = evt_pb.routine.id
        rtn.fn_name = evt_pb.routine.fn_name
        rtn.args = evt_pb.routine.args
        evt.routine = rtn

    elif evt_pb.type == pb.Event.Type.GET_WAIT:
        evt.type = EVT_WAIT_GET
        evt.with_data = evt_pb.with_data
        evt.ref_ids = [ref_id for ref_id in evt_pb.ref_ids]
        if evt_pb.status == pb.Event.Status.SUCC:
            evt.status = RTN_SUCC
            if evt_pb.with_data:
                evt.result = evt_pb.result
        elif evt_pb.status == pb.Event.Status.FAIL:
            evt.status = RTN_FAIL
            if evt_pb.with_data:
                evt.error = evt_pb.error
    # logger.opt(lazy=True).bind(ns=utils.time_ns(), EvtType=evt_pb.type).debug("TideCtr: finish unmarshaling event")
    return evt


def marshal_event(evt: Event):
    # logger.opt(lazy=True).bind(ns=utils.time_ns(), EvtType=evt.type).debug("TideCtr: start marshaling event")
    evt_pb = pb.Event()
    if evt.type == EVT_WAIT_GET:
        evt_pb.type = pb.Event.Type.GET_WAIT
        evt_pb.ref_ids.extend(evt.ref_ids)
        evt_pb.with_data = evt.with_data

    elif evt.type == EVT_SUBMIT_ROUTINE:
        evt_pb.type = pb.Event.Type.ROUTINE_SUBMIT
        assert evt.routine is not None, 'event routine is None'
        evt_pb.routine.id = evt.routine.id
        evt_pb.routine.fn_name = evt.routine.fn_name
        evt_pb.routine.args = evt.routine.args

    elif evt.type == EVT_EXIT:
        evt_pb.type = pb.Event.Type.EXIT
        if evt.status == RTN_SUCC:
            evt_pb.status = pb.Event.Status.SUCC
            evt_pb.result = evt.result
        else:
            evt_pb.status = pb.Event.Status.FAIL
            evt_pb.error = evt.error
    
    elif evt.type == EVT_INIT:
        evt_pb.type = pb.Event.Type.INIT
        
    data = evt_pb.SerializeToString()
    # logger.opt(lazy=True).bind(ns=utils.time_ns(), EvtType=evt_pb.type).debug("TideCtr: finish marshaling event")
    return data
