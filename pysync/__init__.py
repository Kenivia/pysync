from pysync.Functions import init_libraries


def main():

    if not init_libraries({"pydrive2", "send2trash"}):
        print("pysync will now exit")
        return

    try:
        import pysync.ProcessedOptions

    except Exception as e:
        from pysync.Functions import error_report
        from pysync.Exit import on_exit
        error_report(e, "while parsing Options.py:", raise_exception=False)
        on_exit(failure=True)
        return

    from pysync.EventSequence import event_sequence
    from pysync.ProcessedOptions import PATH
    from pysync.Functions import (
        error_report,
        pysyncSilentExit,
    )
    from pysync.Exit import on_exit

    timer = None
    print("pysync started successfully")
    try:
        timer = event_sequence(PATH)
        on_exit(timer=timer, failure=False)

    except pysyncSilentExit:
        pass
    except KeyboardInterrupt:
        on_exit(failure=False)
    except Exception as e:
        error_report(e, "The following error occured:",
                     full_text=True, raise_exception=False)
        on_exit(failure=True)
