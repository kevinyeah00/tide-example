import os
import pickle
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import time
import sys
from . import utils

from loguru import logger

logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{extra} - <level>{message}</level>"
)

logger.remove()
logger.add(sys.stderr, level="DEBUG", format=logger_format)
logger = logger.opt(lazy=True)


from . import event_process, c, routine, stringx, event, wait_get


def _register_fn(func, target_loc):
    global registry
    fn_name = func.__name__
    if fn_name not in c.registry:
        c.registry[fn_name] = {}
    c.registry[fn_name][target_loc] = func
    logger.bind(FnName=fn_name).info('TideCtr: register a function')


def fn(target_loc='any'):
    def decorator(func):
        _register_fn(func, target_loc)
        return func
    return decorator


def main():
    def decorator(func):
        c.main_fn = func
        return func
    return decorator


def init():
    def decorator(func):
        c.init_fn = func
        return func
    return decorator


def run():
    in_mq = os.environ.get('TIDE_IN_MQ')
    out_mq = os.environ.get('TIDE_OUT_MQ')
    mode = os.environ.get('TIDE_MODE')
    debug = os.environ.get('TIDE_DEBUG') == '1'
    logger.bind(InMQ=in_mq, OutMQ=out_mq, Mode=mode, Debug=debug).info("tide: start running")

    if debug:
        c.DEBUG = True
        _run_debug()
        return

    event_process.conn_mq(in_mq, out_mq)
    if c.init_fn is not None:
        c.init_fn()
    evt = event.Event()
    evt.type = event.EVT_INIT
    data = event.marshal_event(evt)
    c.out_mq.send(data)
    
    if mode == 'entry':
        thr = Thread(target=event_process.listen_event)
        thr.start()
        _run_entry()
    else:
        event_process.listen_event()


def _run_debug():
    if c.init_fn is not None:
        c.init_fn()
    assert c.main_fn is not None, 'main_fn is None'
    c.main_fn()


def _run_entry():
    logger.info("Tide: run entry")
    assert c.main_fn is not None, 'main_fn is None'
    try:
        c.main_fn()
        evt = event.Event()
        evt.type = event.EVT_EXIT
        evt.status = routine.RTN_SUCC
        data = event.marshal_event(evt)
        c.out_mq.send(data)
    except Exception as e:
        evt = event.Event()
        evt.type = event.EVT_EXIT
        evt.status = routine.RTN_FAIL
        evt.error = str(e)
        data = event.marshal_event(evt)
        c.out_mq.send(data)
            

def wait(*rtns: routine.Routine):
    wait_get.wait(rtns)
    t1 = utils.time_ns()
    ref_ids = [rtn.id for rtn in rtns]
    logger.bind(RoutineIds=ref_ids, ns=t1).debug('TideCtr: finish waitting')
    

def get(rtn: routine.Routine):
    logger.bind(RoutineId=rtn.id).debug('TideCtr: start getting')
    result = wait_get.get(rtn)
    t1 = utils.time_ns()
    logger.bind(RoutineId=rtn.id, ns=t1).debug('TideCtr: finish getting')
    return result


import traceback
thr_pool = ThreadPoolExecutor()
def offload(*args, **kwargs):
    t0 = utils.time_ns()
    def emit_thread(rtn: routine.Routine, args, kwargs):
        func = args[0]
        args = args[1:]
        fn_name = func.__name__
        t0 = utils.time_ns()
        fn_args = pickle.dumps((args, kwargs))
        t1 = utils.time_ns()
        logger.bind(FnName=fn_name, Length=utils.convert_bytes(len(fn_args))).warning(f'pickle dumps args {(t1-t0)/1000000.}')
        rtn.fn_name = fn_name
        rtn.args = fn_args
        
        if c.DEBUG:
            rtn.submit_done()
            logger.bind(FnName=fn_name, ns=utils.time_ns(), RoutineId=rtn.id).debug('TideCtr: finish offloading')
            fn = c.registry[rtn.fn_name]['any']
            t0 = utils.time_ns()
            args, kwargs = list(pickle.loads(rtn.args))
            t1 = utils.time_ns()
            logger.warning(f'pickle loads args {(t1-t0)/1000000.}')
            try:
                ret = fn(*args, **kwargs)
                # t0 = utils.time_ns()
                result = pickle.dumps(ret)
                # t1 = utils.time_ns()
                # logger.bind(Length=len(result)/1024.).warning(f'pickle dumps ret {(t1-t0)/1000000.}')
                rtn.exit(routine.RTN_SUCC)
                rtn.set_data(result)
            except Exception as e:
                print(traceback.format_exc())
                print('Error: ', rtn.fn_name)
                # print(e)
                rtn.exit(routine.RTN_FAIL)
                rtn.error = str(e)
            return
        
        evt = event.Event()
        evt.type = event.EVT_SUBMIT_ROUTINE
        evt.routine = rtn
        data = event.marshal_event(evt)
        c.out_mq.send(data)
        rtn.submit_done()
        logger.bind(FnName=fn_name, DataSize=len(fn_args), ns=utils.time_ns(), RoutineId=rtn.id).debug('TideCtr: finish offloading')

    rtn = routine.Routine()
    rtn.id = stringx.generate_id()
    thr_pool.submit(emit_thread, rtn, args, kwargs)
    logger.bind(FnName=args[0].__name__, ns=t0, RoutineId=rtn.id).debug('TideCtr: start offloading')
    return rtn