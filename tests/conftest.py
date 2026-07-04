import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging

original_log = logging.Logger._log


def _log_with_kwargs(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **kwargs):
    if kwargs:
        extra_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
        msg = f"{msg} [{extra_str}]"
    return original_log(self, level, msg, args, exc_info, extra, stack_info, stacklevel)


logging.Logger._log = _log_with_kwargs
