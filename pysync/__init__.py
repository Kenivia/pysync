import sys

from pysync.Exit import (
    on_exit,
    exc_with_message,
)
from pysync.Functions import SilentExit
from pysync.Options_parser import load_options
from pysync.EventSequence import event_sequence
from pysync.Options_parser import check_options


def main():

    check_options()

    timer = None
    print("pysync started successfully")
    try:
        timer = event_sequence(load_options("PATH"))
        on_exit(False, timer=timer)

    except SilentExit:
        sys.exit(0)
    except KeyboardInterrupt:
        on_exit(False)
        sys.exit(130)
    except Exception:
        exc_with_message(message=None, raise_silent=False)
