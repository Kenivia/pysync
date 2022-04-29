import sys
import traceback

from pysync.Options_parser import check_options
from pysync.EventSequence import (
    event_sequence,
    init_libraries,
)
from pysync.Options_parser import load_options
from pysync.Functions import (
    pysyncSilentExit,
)
from pysync.Exit import on_exit


def main():

    if not init_libraries({"pydrive2", "send2trash"}):
        print("pysync will now exit")
        return

    check_options()

    timer = None
    print("pysync started successfully")
    try:
        timer = event_sequence(load_options("PATH"))
        on_exit(False, timer=timer)

    except pysyncSilentExit:
        pass
    except KeyboardInterrupt:
        on_exit(False)
    except Exception:
        traceback.print_exc(file=sys.stdout)
        on_exit(True)
