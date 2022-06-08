from pysync.Differ import get_diff
from pysync.Exit import on_exit, exit_with_message
from pysync.FileInfo import run_drive_ops
from pysync.Functions import SilentExit
from pysync.GetLocal import get_local
from pysync.GetRemote import get_remote, process_remote
from pysync.InitDrive import init_drive
from pysync.OptionsParser import get_option, check_options
from pysync.Timer import init_main_timer
from pysync.UserPrompt import apply_forced_and_default, choose_changes


COPYRIGHT_TEXT = """pysync Copyright 2022 Kenivia
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it under certain conditions.
For more information, see the file LICENSE and https://www.gnu.org/licenses/\n\n"""


def real_main(path, timer):

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


def main():
    try:
        import socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Create an abstract socket, by prefixing it with null.
        s.bind('\0pysync_process_lock')
    except socket.error:
        input("an instance of pysync is already running. Press enter to exit")
        return

    check_options()
    # * this is ran outside the try clause because some modules might not work if the options are not set correctly
    # * instead it has its own error catcher 
    
    print(COPYRIGHT_TEXT)
    print()
    try:
        timer = init_main_timer()
        real_main(get_option("PATH"), timer)
        on_exit(False, timer=timer)

    except SilentExit:
        return
    except KeyboardInterrupt:
        on_exit(False)
    except Exception as e:
        exit_with_message(message=None, exception=e, raise_silent=False)
