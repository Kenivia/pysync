from pysync.Options_parser import check_options
from pysync.EventSequence import (
    event_sequence,
    init_libraries,
)
from pysync.Options_parser import load_options
from pysync.Functions import SilentExit
from pysync.Exit import (
    on_exit,
    exc_with_message,
)


def main():

    if not init_libraries({"send2trash"}):
        print("pysync will now exit")
        return

    check_options()

    timer = None
    print("pysync started successfully")
    try:
        timer = event_sequence(load_options("PATH"))
        on_exit(False, timer=timer)

    except SilentExit:
        return 0
    except KeyboardInterrupt:
        on_exit(False)
        return 130
    except Exception:
        exc_with_message()
        
