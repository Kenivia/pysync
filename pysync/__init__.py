import os
import shutil
import socket
import subprocess as sp
import sys
import tempfile as tf
import time
import traceback
from datetime import datetime, timedelta

from filelock import FileLock

from pysync.BaseFileInfo import commit_drive_ops
from pysync.Commons import SilentExit, get_root, pdump, pload, readable
from pysync.Differ import get_diff
from pysync.Exit import exit_with_msg, on_exit
from pysync.GetLocal import get_local
from pysync.GetRemote import get_dump_remote
from pysync.InitDrive import copy_client_secret, init_drive
from pysync.OptionsParser import get_option, get_root, parse_options
from pysync.Timer import init_main_timer
from pysync.UserPrompt import (apply_forced_and_default, apply_modification,
                               choose_changes, compress_deletes, print_changes,
                               print_totals)


def decide_cache_new(inp):
    loaded = None
    print("")
    if len(inp) > 1:
        exit_with_msg(msg=f"diff takes either 0 or 1 arguments, received {len(inp)}",)
        return None, None

    if len(inp) == 1 and inp[0] != "cache" and inp[0] != "new":
        exit_with_msg(msg=f"diff takes either \"cache\" or \"new\", received {inp[0]}",)
        return None, None

    remote_pkl = get_root() + "/data/Internal/Latest_remote.pkl"
    if not os.path.isfile(remote_pkl):
        return "new", loaded
    try:
        loaded = pload(remote_pkl)
        str_ago, str_stamp, unix = readable(loaded["time"])

        if loaded["def_not_safe"]:
            print("Cached data was marked as unsafe")
            return "new", loaded

        if unix / 3600 > 2:
            print(f"Cached data too old(>2h): fetched {str_ago} ago({str_stamp})")
            return "new"
        else:
            print(f"Cached data appears ok: fetched {str_ago} ago({str_stamp})")
            cache_available = True

    except Exception:
        print("Failed to load cached data for the following reason:")
        traceback.print_exc()
        return "new", loaded

    assert cache_available

    if len(inp) == 0:
        print("pysync can fetch fresh remote data or use the cached copy to compare with")
        print("Only use the cached copy if no remote changes(e.g. creating a new google document) has been made to google drive")
        print("Fetch new data? (Y/n)\n")
        ans = input(">>> ").lower()
        if ans == "n":

            return "cache", loaded
        else:

            return "new", loaded

    else:
        print(f"Using what was given at commandline: {inp[0]}")
        return inp[0], loaded


def dump_data_diff(all_data, diff_infos, original_time=time.time(), mod_time=time.time()):
    try:
        pdump({"all_data": all_data,
               "diff_infos": diff_infos,
               "diff_time": original_time,
               "mod_time": mod_time, }, get_root() + "/data/Internal/Diff_info.pkl")
    except Exception:
        print("Failed to load the output of diff:")
        traceback.print_exc()
        return


def load_data_diff():
    try:
        loaded = pload(get_root() + "/data/Internal/Diff_info.pkl")
    except Exception as e:
        print("Failed to load the output of diff:")
        raise e

    return loaded["all_data"], loaded["diff_infos"], loaded["diff_time"], loaded["mod_time"]


def main(args):
    path = get_option("PATH")
    try:
        if args.watcher:
            from pysync.Watcher import watcher
            watcher()

        elif isinstance(args.diff, list):

            local_data = {}
            print("Started loading local files...")
            thread = get_local(path, local_data)

            used, loaded = decide_cache_new(args.diff)

            if used == "new" and len(args.diff) == 1 and args.diff[0] == "cache":
                print("Warning: Command line said to use cache, but that was not possible")

            drive = init_drive()

            if used == "new":
                print("\nFetching new data")

                remote_data, root = get_dump_remote(drive)

            elif used == "cache":
                print("\nUsing cached data")

                remote_data = loaded["rdata"]
                root = loaded["root"]

            print("Remote files done")

            thread.join()

            print("Comparing...")
            diff_infos, all_data = get_diff(local_data, remote_data)

            all_data[path] = root  # * This is needed for find_parent in run_drive_ops

            apply_forced_and_default(diff_infos)

            compress_deletes(diff_infos)
            print_changes(diff_infos, True)

            print("\n\nThese changes are pending:")
            print_totals(diff_infos)
            print("Use \"pysync --modify\" to modify the proposed changes")
            print("Use \"pysync --commit\" to apply these changes. There will be no further confirmations!")

            dump_data_diff(all_data, diff_infos)

        elif isinstance(args.modify, list):
            all_data, diff_infos, diff_time, mod_time = load_data_diff()
            diff_ago, diff_stamp, diff_unix = readable(diff_time)

            print(f"Modifying the output of diff from {diff_ago} ago({diff_stamp}")

            if diff_unix / 60 > 60:
                print("It has been more than 1 hour since the \"diff\", please run diff again")
                if os.path.isfile(get_root() + "/data/Internal/Diff_info.pkl"):
                    os.remove(get_root() + "/data/Internal/Diff_info.pkl")
                return

            modified = apply_modification(diff_infos, args.modify)
            
            dump_data_diff(all_data, modified, diff_time, time.time())

            if diff_unix / 60 > 10:
                print("""Warning! It's been more than 10 minutes since the \"diff\" command ran
    Changes made after it may be overwritten!""")
            print("Use \"pysync --commit\" to apply these changes. There will be no further confirmations!")

        elif args.commit:
            

            drive = init_drive()
            all_data, diff_infos, diff_time, mod_time = load_data_diff()
            
            
            remote_pkl = get_root() + "/data/Internal/Latest_remote.pkl"
            if os.path.isfile(remote_pkl):
                os.remove(remote_pkl)
            diff_pkl = get_root() + "/data/Internal/Diff_info.pkl"
            if os.path.isfile(diff_pkl):
                os.remove(diff_pkl)
            else:
                print("\"--diff\" must be ran before running commit")
                return

            compress_deletes(diff_infos)
            print_changes(diff_infos, True)
            print("\n\nCommitting the changes above")
            print_totals(diff_infos)

            diff_ago, diff_stamp, diff_unix = readable(diff_time)
            mod_ago, mod_stamp, mod_unix = readable(mod_time)
            print(f"Committing the output of diff from {diff_ago} ago({diff_stamp}")
            print(f"Committing the output of modify from {mod_ago} ago({mod_stamp}")
            if diff_unix / 60 > 10:
                input("""Warning! It's been more than 10 minutes since the \"diff\" command ran
    Changes made after it may be overwritten!
    Press Enter to commit""")
            if mod_unix / 60 > 5:
                input("""Warning! It's been more than 5 minutes since the \"mod\" command ran
    Are you sure this is what you intended to commit?
    Press Enter to commit""")

            commit_drive_ops(diff_infos, all_data, drive)

        elif isinstance(args.init, list):
            if len(args.init) == 1:
                copy_client_secret(args.init[0])
            if len(args.init) == 0 or len(args.init) == 1:
                init_drive()
                return
            exit_with_msg(msg=f"init takes either 0 or 1 arguments, received {len(args.init)}",)
            return

        elif args.fetch:

            drive = init_drive()

            get_dump_remote(drive)

        elif args.option:
            options_path = get_root() + "/data/Options.json"
            if shutil.which("gedit") is not None:

                print(f"Opening using gedit: {options_path}")
                print("You may wish to change \"View\"->\"Highlight Mode\" to \"javascript\" to stop gedit from highlighting the comments as errors")
                sp.Popen(["gedit", options_path])
                print("Opened")
            else:
                print("gedit is not available, using nano")
                sp.call(["nano", options_path])
    except SilentExit:
        return
    except KeyboardInterrupt:
        on_exit(False)
    except Exception as e:
        message = None
        exit_with_msg(msg=message, exception=e, raise_silent=False)
