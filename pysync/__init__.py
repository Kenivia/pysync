
from pysync.Functions import init_libraries


def main():

    if not init_libraries():
        print("pysync will now exit")
        return

    try:
        import pysync.ProcessedOptions
    except Exception as e:
        from pysync.Functions import error_report
        from pysync.UserInterface import pre_exit_optoins
        error_report(e, "while parsing Options.py:", raise_exception=False)
        pre_exit_optoins(failure=True)
        return

    from pysync.EventFlow import event_flow, error_report
    from pysync.ProcessedOptions import PATH
    from pysync.Functions import HandledpysyncException
    from pysync.UserInterface import pre_exit_optoins

    timer = None
    print("pysync started successfully")
    try:
        timer = event_flow(PATH)
        pre_exit_optoins(timer=timer, failure=False)

    except KeyboardInterrupt:
        pre_exit_optoins(failure=False)

    except HandledpysyncException:
        pre_exit_optoins(failure=True)

    except Exception as e:
        error_report(e, "The following error occured unexpectedly:",
                     full_text=True, raise_exception=False)
        pre_exit_optoins(failure=True)
