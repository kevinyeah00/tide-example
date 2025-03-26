import posix_ipc
import pickle
import time
from . import utils

from loguru import logger
logger = logger.opt(lazy=True)

from . import event, c, routine


def conn_mq(in_mq_name, out_mq_name):
    c.in_mq = posix_ipc.MessageQueue('/'+in_mq_name, mode=0o666, write=False, 
                                     max_message_size=1<<24, max_messages=65535)
    c.out_mq = posix_ipc.MessageQueue('/'+out_mq_name, mode=0o666, read=False, 
                                      max_message_size=1<<24, max_messages=65535)


def listen_event():
    logger.info("Tide: enter event loop")
    while True:
        try:
            process_one_msg()
        except Exception as e:
            print(e)


def process_one_msg():
    assert c.in_mq is not None
    msg, _ = c.in_mq.receive()
    evt = event.unmarshal_event(msg)

    if evt.type == event.EVT_SUBMIT_ROUTINE:
        handle_submit_rtn(evt)
    elif evt.type == event.EVT_WAIT_GET:
        handle_wait_get(evt)


def handle_submit_rtn(evt: event.Event):
    assert evt.routine is not None, 'routine is None'
    rtn = evt.routine
    if rtn.fn_name not in c.registry:
        evt_resp = event.Event.fail('no such function')
        send_evt_pb(evt_resp)
        return

    try:
        logger.bind(RoutineId=rtn.id, FnName=rtn.fn_name, ns=utils.time_ns()).debug('TideCtr: receive a routine')
        fn = c.registry[rtn.fn_name]['any']
        logger.bind(RoutineId=rtn.id, FnName=rtn.fn_name, ns=time.time_ns()).debug('TideCtr: execute this routine')
        args, kwargs = list(pickle.loads(rtn.args))
        logger.bind(RoutineId=rtn.id, FnName=rtn.fn_name, ns=time.time_ns()).debug('TideCtr: get all args and start computing')
        # logger.bind(RoutineId=rtn.id, FnName=rtn.fn_name, ns=time.time_ns()).debug('TideCtr: execute this routine')
        ret = fn(*args, **kwargs)
        logger.bind(RoutineId=rtn.id, FnName=rtn.fn_name, ns=time.time_ns()).debug('TideCtr: finish computing')
        result = pickle.dumps(ret)
        logger.bind(RoutineId=rtn.id, FnName=rtn.fn_name, ns=time.time_ns()).debug('TideCtr: finish pickle')
        evt_resp = event.Event.succ(result)
    except Exception as e:
        logger.bind(RoutineId=rtn.id, FnName=rtn.fn_name, ns=utils.time_ns()).error(str(e))
        evt_resp = event.Event.fail(str(e))
    send_evt_pb(evt_resp)
    logger.bind(RoutineId=rtn.id, FnName=rtn.fn_name, ns=utils.time_ns()).debug('TideCtr: finish routine')


def handle_wait_get(evt: event.Event):
    for ref_id in evt.ref_ids:
        w = c.waiter_map[ref_id]
        w.rtn.exit(evt.status)
        if evt.with_data:
            w.rtn.set_data(evt.result if evt.status == routine.RTN_SUCC else evt.error)


def send_evt_pb(evt: event.Event):
    data = event.marshal_event(evt)
    # logger.bind(ns=utils.time_ns(), EvtType=evt.type).debug('TideCtr: start sending to MQ')
    c.out_mq.send(data)
    # logger.bind(ns=utils.time_ns(), EvtType=evt.type).debug('TideCtr: finish sending to MQ')
