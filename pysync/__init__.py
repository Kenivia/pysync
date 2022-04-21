from pysync.Functions import init_libraries
from pysync.Options_parser import check_options


def main():

    if not init_libraries({"pydrive2", "send2trash"}):
        print("pysync will now exit")
        return

    check_options()

    from pysync.EventSequence import event_sequence
    from pysync.Options_parser import load_options
    from pysync.Functions import (
        error_report,
        pysyncSilentExit,
    )
    from pysync.Exit import on_exit

    timer = None
    print("pysync started successfully")
    try:
        timer = event_sequence(load_options("PATH"))
        on_exit(timer=timer, failure=False)

    except pysyncSilentExit:
        pass
    except KeyboardInterrupt:
        on_exit(failure=False)
    except Exception as e:
        error_report(e, "The following error occured:",
                     full_text=True)
        on_exit(failure=True)
