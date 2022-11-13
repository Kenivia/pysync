import sys
import subprocess as sp
import traceback

from threading import Thread


from pysync.Commons import SilentExit, get_root


"""
This file provides functions called when the process exits
This should be safe to import just like Commons
"""


def exit_with_msg(msg=None, exception=None, raise_silent=True,):
    if exception is not None:
        traceback.print_exception(exception, exception, exception.__traceback__, file=sys.stdout)
    # * not using traceback.print_exc because sometimes we don't want to print the traceback
    if msg is not None:
        print("\n" + msg)

    on_exit(True)

    if raise_silent:
        raise SilentExit()


def on_exit(failure, timer=None):
    """starts on_exit_thread if needed, then the main thread should exit

    this function should be called as the last thing before the main thread exits
    this is to ensure that threading.main_thread().is_alive() returns False

    Args:
        failure (bool): whether or not pysync completed successfully
        timer (pysync.TimeLogger, optional): TimeLogger object from event_sequence
    """
    try:
        from pysync.OptionsParser import get_option
        if not get_option("ASK_AT_EXIT"):
            print("Exiting")
            return
    except Exception:
        print("Exiting")
        return

    t = Thread(target=on_exit_thread, args=(failure, timer,), daemon=False)
    # * very important that daemon=False
    t.start()

    # * at this point, the main thread should exit
    # * this also releases the socket bind so another pysync process can start now


def on_exit_thread(error=False, timer=None):

    line_input = "\n\n>>> "
    line_exit = "\nPress Enter to exit"
    line_restart = "\nType \"restart\" to sync again"
    line_time = "\nType \"time\" to see how long each stage took"

    cancel_text = "\nThe syncing process was cancelled" + \
        line_exit + line_restart + line_input

    complete_text = "\nThe syncing process has completed successfully" + \
        line_exit + line_time + line_restart + line_input

    part_fail_text = "\nFiles listed above failed to sync, other files completed successfully" +\
        line_exit + line_time + line_restart + line_input

    error_text = "\nThe error above has occurred " + \
        line_exit + line_restart + line_input

    if error == "some failed":
        text = part_fail_text

    elif error:
        text = error_text

    else:
        if timer is None:
            text = cancel_text
        else:
            text = complete_text

    while True:

        user_inp = input(text)
        user_inp = user_inp.lower().strip()
        if user_inp == "" or user_inp == "exit":
            return
        elif timer is not None and user_inp == "time":
            timer.print_times()
            text = line_exit + line_restart + line_input
            timer = None
        elif user_inp == "restart":
            restart()
            return
        else:
            return


def restart():
    # TODO specify terminal in Option.json
    root_path = get_root()
    thispython = sys.executable
    retval = sp.run(["dpkg", "-s", "gnome-terminal"],
                    stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    if retval.returncode == 0:
        sp_list = ["gnome-terminal", "--", thispython, root_path + "/pysync"]
        command_used = " ".join([str(i) for i in sp_list])
        sp.call(sp_list)
    else:
        retval = sp.run(["dpkg", "-s", "xfce4-terminal"],
                        stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        if retval.returncode == 0:
            sp_list = ["xfce4-terminal", "-x", thispython, root_path + "/pysync"]
            command_used = " ".join([str(i) for i in sp_list])
            sp.call(sp_list)
        else:
            print("Neither gnome-terminal nor xfce4-terminal is available, unable to restart")
            input("Press enter to exit")
            return

    print("A new instance of pysync has been started using the following command:" +
          "\n\t" + command_used +
          "\nthis process should end immediately")
