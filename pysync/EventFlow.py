from pysync.Timer import TimeLogger
from pysync.UserInterface import (
    print_diff_types,
    user_push_pull,
)
from pysync.Differ import get_diff
from pysync.LocalFiles import get_local_files
from pysync.RemoteFiles import (
    init_drive,
    list_remote,
    process_remote
)
from pysync.ApplyOperation import (
    decide_push_pull,
    run_drive_ops,
)
from pysync.ProcessedOptions import (
    DEFAULT_PULL,
    DEFAULT_PUSH,

)
from pysync.Functions import (
    cancel_report,
    error_report
)


def event_flow(path):
    """Checks for differences and prompts user to apply updates

    path - the directory to update

    prompts the user to modify which keys to push and pull
    outputs the computation time(excludes time waiting for user input)
    """

    timer = TimeLogger(2)
    try:
        drive = init_drive(timer=timer.user("Initializing drive"))
    except KeyboardInterrupt:
        cancel_report()
    except Exception as e:
        error_report(e, "during drive initialization:")

    try:
        remote_list = list_remote(drive,
                                  timer=timer.load("Listing remote files"))
    except KeyboardInterrupt:
        cancel_report()
    except Exception as e:
        error_report(e, "while downloading remote files:")

    try:
        local_path_dict = get_local_files(path,
                                          timer=timer.comp("Processing local files"))
    except Exception as e:
        error_report(e, "while reading local files:")

    try:
        remote_path_dict = process_remote(remote_list,
                                          timer=timer.comp("Processing remote files"))
        diff_dict, all_path_dict, no_change = get_diff(local_path_dict, remote_path_dict,
                                            timer=timer.comp("Comparing local and remote files"))
    except Exception as e:
        error_report(e, "while processing files:")

    if no_change:
        print("Everthing is up to date")
        return timer

    try:
        push, pull = user_push_pull(DEFAULT_PUSH.copy(), DEFAULT_PULL.copy(), diff_dict,
                                    timer=timer.user("Choosing which types to push & pull"))
    except KeyboardInterrupt:
        cancel_report()
    except Exception as e:
        error_report(e, "while inputting action")

    try:
        pushpull_list = decide_push_pull(diff_dict, push, pull, 
                                         timer=timer.comp())
        # confirm("Total of "+str(len(info_list)) +" changes.\n"
        #         "Apply these changes?", timer)
        run_drive_ops(pushpull_list, all_path_dict, drive,
                      timer=timer.load("Applying changes"))
    except Exception as e:
        error_report(
            e, "The following error occured, in the main thread, while applying the sync:", True)

    return timer
