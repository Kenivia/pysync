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


# import os
# from pysync.pklFunctions import dump_test_pkl, pload
# def event_sequence(path):

#     stages = {"local": FuncTimer("comp", "Loading local files"),
#               "init": FuncTimer("user", "Initializing drive"),
#               "load_remote": FuncTimer("net", "Getting remote files"),
#               "comp_remote": FuncTimer("comp", "Processing remote files"),
#               "compare": FuncTimer("comp", "Comparing local and remote files"),
#               "choose": FuncTimer("user", "Choosing which types to push & pull"),
#               "apply": FuncTimer("net", "Applying changes"),
#               }
#     # * stages not neccessarily in order
#     sequence = ["init", "load_remote", "comp_remote", "compare", "choose", "apply"]
#     # * sequence is in order
#     concurrent = {"local": (0, 2)}
#     # * the key: the beginning and end indexes that it overlaps with
#     for i in concurrent:
#         stages[i].concurrent = True

#     timer = TimeLogger(stages, sequence, concurrent, decimal_points=3)

#     dumping = False

#     print("Started loading local files..")
#     drive = init_drive(timer=timer.time("init"))
#     if dumping:
#         print("dumping")
#         local_data = {}
#         thread = get_local_files(path, local_data, timer=timer.time("local"))

#         print("Started getting remote files..")
#         remote_raw_data = list_remote(drive, timer=timer.time("load_remote"))
#         date = dump_test_pkl(remote_raw_data, "remote")
#     else:
#         print("not dumping")
#         remote_raw_data = pload(
#             f"/home/kenivia/gdrive/Python/Projects/pysync/test_pkl/{sorted(os.listdir('/home/kenivia/gdrive/Python/Projects/pysync/test_pkl/'))[-1]}/remote")

#     remote_data = process_remote(remote_raw_data, timer=timer.time("comp_remote"))
#     print("Remote files done")
#     if dumping:
#         thread.join()
#         dump_test_pkl(local_data, "local", date)
#     else:
#         local_data = pload(
#             f"/home/kenivia/gdrive/Python/Projects/pysync/test_pkl/{sorted(os.listdir('/home/kenivia/gdrive/Python/Projects/pysync/test_pkl/'))[-1]}/local")
#         print("Comparing..")
#         diff_infos, all_data = get_diff(local_data, remote_data, timer=timer.time("compare"))

#         apply_forced_and_default(diff_infos, timer=timer.time("compare"))

#         user_push_pull(diff_infos, timer=timer.time("choose"))

#         pass
#         run_drive_ops(diff_infos, all_data, drive, timer=timer.time("apply"))

#     return timer
