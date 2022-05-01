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
    try:
        import socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Create an abstract socket, by prefixing it with null.
        s.bind('\0pysync_process_lock')
    except socket.error:
        print("an instance of pysync is already running. Exiting")
        sys.exit(0)
        
    check_options()

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
