from pysync.Timer import init_main_timer
from pysync.UserPrompt import apply_forced_and_default, choose_changes
from pysync.Differ import get_diff
from pysync.GetLocal import get_local
from pysync.GetRemote import get_remote, process_remote
from pysync.InitDrive import init_drive
from pysync.FileInfo import run_drive_ops


def event_sequence(path):

    timer = init_main_timer()

    local_data = {}
    print("Started loading local files..")
    thread = get_local(path, local_data, timer=timer.time("local"))

    drive = init_drive(timer=timer.time("init"))

    print("Started getting remote files..")
    remote_raw_data, root = get_remote(drive, timer=timer.time("load_remote"))
    remote_data = process_remote(remote_raw_data, root, timer=timer.time("comp_remote"))
    print("Remote files done")

    thread.join()

    print("Comparing..")
    diff_infos, all_data = get_diff(local_data, remote_data, timer=timer.time("compare"))
    all_data[path] = root
    apply_forced_and_default(diff_infos, timer=timer.time("compare"))

    choose_changes(diff_infos, timer=timer.time("choose"))

    run_drive_ops(diff_infos, all_data, drive, timer=timer.time("apply"))

    return timer
