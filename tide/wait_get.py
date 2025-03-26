from typing import List, Tuple

from . import routine, c, waiter, event


def wait(rtns: Tuple[routine.Routine]):
    need_notice_rtns = []
    for rtn in rtns:
        if rtn.done:
            continue
        rtn.wait_submitted()
        if rtn.id not in c.waiter_map:
            c.waiter_map[rtn.id] = waiter.Waiter(rtn, False)
        need_notice_rtns.append(rtn)
    if len(need_notice_rtns) == 0:
        return
    _notice_wait_get(need_notice_rtns, False)
    for rtn in rtns:
        rtn.wait_done()


def get(rtn: routine.Routine):
    if rtn.data:
        return rtn.result
    rtn.wait_submitted()
    if rtn.id not in c.waiter_map or not c.waiter_map[rtn.id].with_data:
        c.waiter_map[rtn.id] = waiter.Waiter(rtn, True)
    _notice_wait_get([rtn], True)
    rtn.wait_data()  # TODO: 失败error处理
    return rtn.result


def _notice_wait_get(rtns: List[routine.Routine], with_data: bool):
    if c.DEBUG:
        for rtn in rtns:
            rtn.wait_data()
        return
    
    ref_ids = [rtn.id for rtn in rtns]
    evt = event.Event()
    evt.type = event.EVT_WAIT_GET
    evt.ref_ids = ref_ids
    evt.with_data = with_data
    data = event.marshal_event(evt)
    c.out_mq.send(data)
    
