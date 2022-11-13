import sys

if (__package__ is None or __package__ == "") and not hasattr(sys, 'frozen'):
    # * direct call of __main__.py
    import os.path

    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

from time import sleep, time

from filelock import FileLock

from pysync.Commons import bind_socket, get_root
from pysync.GetRemote import get_dump_remote
from pysync.InitDrive import init_drive
from pysync.OptionsParser import get_option


def timer(start_time, length):
    assert length > 0

    return time() - start_time > length


def watcher():

    bind_socket("pysync_watcher_lock")

    interval = get_option("CACHE_INTERVAL")

    lock_path = get_root() + "/data/Internal/Latest_remote.pkl.lock"
    lock = FileLock(lock_path)

    drive = init_drive(user_interact=False)

    if drive is None:
        print("Failed to initialize drive, will not ask for user interaction, exiting watcher process now")
        return

    print("Watcher process has been started")
    try:
        while True:
            print("Getting remote")
            get_dump_remote(drive)
            print("Dumped remote")
            sleep(interval)

    finally:
        lock.release()
