import os
import subprocess as sp
from threading import Thread
from pysync.UserInterface import (
    TimeLogger,
    print_diff_types,
    print_start,
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
    ROOTPATH,
)
from pysync.Functions import HandledpysyncException


def raise_this_error(error):
    raise error


def error_report(exception_object, text, full_text=False):
    try:
        if full_text:
            print(text)
        else:
            print("The following error occured " + text)
            t = Thread(target=raise_this_error, args=(exception_object,))
            t.start()

    # print(repr(exception_object))
    finally:
        t.join()
        raise HandledpysyncException()


def cancel_report():
    raise KeyboardInterrupt


def event_flow(path):
    """Checks for differences and prompts user to apply updates

    path - the directory to update

    prompts the user to modify which keys to push and pull
    outputs the computation time(excludes time waiting for user input)
    """
    

    timer = TimeLogger(2)
    print_start()

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
        diff_dict, all_path_dict = get_diff(local_path_dict, remote_path_dict,
                                            timer=timer.comp("Comparing local and remote files"))
    except Exception as e:
        error_report(e, "while processing files:")

    printed = print_diff_types(diff_dict, False,
                               timer=timer.comp())
    if not printed:
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
        pushpull_list = decide_push_pull(diff_dict, push, pull, False,
                                         timer=timer.comp())
        # confirm("Total of "+str(len(info_list)) +" changes.\n"
        #         "Apply these changes?", timer)
        run_drive_ops(pushpull_list, all_path_dict, drive,
                      timer=timer.load("Applying changes"))
    except Exception as e:
        error_report(
            e, "The following error occured, in the main thread, while applying the sync:", True)

    return timer


def post_sync_options(timer=None, failure=False):

    while True:
        cancel_text = """The syncing process was canceled by user
Press enter to exit
Type \"restart\" to sync again

>>> """

        complete_text = """The syncing process has completed successfully
Press enter to exit
Type \"time\" to see how long each stage took
Type \"restart\" to sync again

>>> """

        failure_text = """The syncing process has failed, the error has been printed above
Press enter to exit
Type \"restart\" to sync again

>>> """

        user_inp = input(failure_text) if failure else (
            input(cancel_text) if timer is None else input(complete_text))
        cancel_text
        user_inp = user_inp.lower().strip()
        if user_inp == "":
            return
        elif user_inp == "time":
            timer.print_times()
        elif user_inp == "restart":
            restart()
            return
        else:
            return



def restart():
    retval = sp.run(["dpkg", "-s", "gnome-terminal"], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    if retval.returncode == 0:
        sp.call(["gnome-terminal", "--", "python3",  str(ROOTPATH)+"/pysync"])
    else: 
        retval = sp.run(["dpkg", "-s", "xfce4-terminal"], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        if retval.returncode == 0:
            sp.call(["xfce4-terminal", "-x", "python3",  str(ROOTPATH)+"/pysync"])
        else:
            print("Neither gnome-terminal nor xfce4-terminal is available, unable to restart")
            input("Press enter to exit")
            return
    print("A new instance of pysync has been started, this window should close immediately")
