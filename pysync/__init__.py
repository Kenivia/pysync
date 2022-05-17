import sys
import traceback

from pysync.Exit import on_exit, exc_with_message
from pysync.Functions import SilentExit
from pysync.OptionsParser import get_option
from pysync.EventSequence import event_sequence
from pysync.OptionsParser import check_options


def main():
    try:
        import socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Create an abstract socket, by prefixing it with null.
        s.bind('\0pysync_process_lock')
    except socket.error:
        input("an instance of pysync is already running. Press enter to exit")
        return

    try:
        check_options()
    except Exception:
        traceback.print_exc(file=sys.stdout)
        print("\nThe error above occured while parsing Options.json. Exiting")
        return

    print("pysync started successfully")
    try:
        timer = event_sequence(get_option("PATH"))
        on_exit(False, timer=timer)

    except SilentExit:
        return
    except KeyboardInterrupt:
        on_exit(False)
    except Exception:
        exc_with_message(message=None, raise_silent=False)
