
from pysync.Functions import init_libraries


def main():

    if not init_libraries():
        print("pysync will now exit")
        return

    try:
        import pysync.ProcessedOptions
    except Exception as e:
        from pysync.Functions import error_report
        from pysync.UserPushPull import pre_exit_options
        error_report(e, "while parsing Options.py:", raise_exception=False)
        on_exit(failure=True)
        return

    from pysync.EventFlow import event_flow, error_report
    from pysync.ProcessedOptions import PATH
    from pysync.Functions import HandledpysyncException
    from pysync.Exit import on_exit

    timer = None
    print("pysync started successfully")
    try:
        timer = event_flow(PATH)
        on_exit(timer=timer, failure=False)

    except KeyboardInterrupt:
        on_exit(failure=False)

    except HandledpysyncException:
        on_exit(failure=True)

    except Exception as e:
        error_report(e, "The following error occured unexpectedly:",
                     full_text=True, raise_exception=False)
        on_exit(failure=True)
