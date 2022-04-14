from pysync.Timer import TimeLogger
from pysync.UserPushPull import (
    apply_forced_and_default,
    user_push_pull,
)
from pysync.Differ import get_diff
from pysync.LocalFiles import get_local_files
from pysync.RemoteFiles import (
    init_drive,
    list_remote,
    process_remote
)
from pysync.ApplyOperation import run_drive_ops
from pysync.Functions import (
    error_report,
    pysyncSilentExit
)


def event_sequence(path):
    """Checks for differences and prompts user to apply updates

    path - the directory to update

    prompts the user to modify which keys to push and pull
    outputs the computation time(excludes time waiting for user input)
    """

    timer = TimeLogger(2)
    try:
        drive = init_drive(timer=timer.user("Initializing drive"))

    except Exception as e:
        error_report(e, "during drive initialization:")

    try:
        remote_list = list_remote(drive,
                                  timer=timer.load("Listing remote files"))

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
        diff_infos, all_path_dict = get_diff(local_path_dict, remote_path_dict,
                                             timer=timer.comp("Comparing local and remote files"))

    except Exception as e:
        error_report(e, "while processing files:")

    if not diff_infos:
        print("Everthing is up to date")
        return timer

    try:
        apply_forced_and_default(diff_infos)
        user_push_pull(diff_infos,
                       timer=timer.user("Choosing which types to push & pull"))

    except pysyncSilentExit:
        raise pysyncSilentExit
    except Exception as e:
        error_report(e, "while inputing action")

    try:

        run_drive_ops(diff_infos, all_path_dict, drive,
                      timer=timer.load("Applying changes"))
    except Exception as e:
        error_report(
            e, "The following error occured, in the main thread, while applying the sync:", True)

    return timer
