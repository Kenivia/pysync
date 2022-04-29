import subprocess as sp
import sys
import pkg_resources

from pysync.Timer import (
    TimeLogger,
    FuncTimer,
)
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







from pysync.pklFunctions import pload


def init_libraries(required):
    """installs required packages using pip if they are not present

    Args:
        required (set): a set containing the packages in string

    Returns:
        bool: if things are installed properly
    """
    required = {'pydrive2', 'send2trash', }
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = list(required - installed)

    if missing:
        missingtext = ", ".join(missing)
        command_list = [sys.executable, '-m', 'pip', 'install', *missing]
        print("The following packages are required by pysync:")
        print("\t" + missingtext)
        print("The following command will be ran:")
        print("\t" + " ".join(command_list))
        inp = input("Proceed (y/N)? ")
        if inp.lower() == "y":
            print("")
            completed = sp.run(command_list)
            if completed.returncode != 0:
                print("An error occured while running the command above")
                return False
            print("")  # * looks better
            return True
        else:
            print("Installation was cancelled by the user")
            return False
    else:
        return True


def event_sequence(path):

    stages = {"local": FuncTimer("comp", "Loading local files"),
              "init": FuncTimer("user", "Initializing drive"),
              "load_remote": FuncTimer("net", "Getting remote files"),
              "comp_remote": FuncTimer("comp", "Processing remote files"),
              "compare": FuncTimer("comp", "Comparing local and remote files"),
              "choose": FuncTimer("user", "Choosing which types to push & pull"),
              "apply": FuncTimer("net", "Applying changes"),
              }
    # * stages not neccessarily in order
    sequence = ["init", "load_remote", "comp_remote", "compare", "choose", "apply"]
    # * sequence is in order
    concurrent = {"local": (0, 2)}
    # * the key: the beginning and end indexes that it overlaps with
    for i in concurrent:
        stages[i].concurrent = True

    timer = TimeLogger(stages, sequence, concurrent, decimal_points=3)

    local_data = {}
    print("Started loading local files..")
    thread = get_local_files(path, local_data, timer=timer.time("local"))

    drive = init_drive(timer=timer.time("init"))

    print("Started getting remote files..")
    # remote_raw_data = pload(
    #     "/home/kenivia/gdrive/Python/Projects/pysync/test_pkl/2022.04.28-22.42.36/remote")
    remote_raw_data = list_remote(drive, timer=timer.time("load_remote"))
    remote_data = process_remote(remote_raw_data, timer=timer.time("comp_remote"))
    print("Remote files done")

    thread.join()

    print("Comparing..")
    diff_infos, all_data = get_diff(local_data, remote_data, timer=timer.time("compare"))

    apply_forced_and_default(diff_infos, timer=timer.time("compare"))

    user_push_pull(diff_infos, timer=timer.time("choose"))

    run_drive_ops(diff_infos, all_data, drive, timer=timer.time("apply"))

    return timer
