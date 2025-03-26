import posix_ipc
from typing import List, Dict

from . import waiter

DEBUG = False

registry = {}
main_fn = None
init_fn = None

in_mq: posix_ipc.MessageQueue = None
out_mq: posix_ipc.MessageQueue = None

waiter_map: Dict[str, waiter.Waiter] = {}