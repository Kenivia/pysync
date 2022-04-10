import sys
import subprocess as sp
from pysync.ProcessedOptions import ROOTPATH,ASK_BEFORE_EXIT


def on_exit(timer=None, failure=False):

    if not ASK_BEFORE_EXIT:
        print("pysync will now exit")
        return
    
    line_input = "\n\n>>> "
    line_exit = "\nPress enter to exit"
    line_restart = "\nType \"restart\" to sync again"
    line_time = "\nType \"time\" to see how long each stage took"

    cancel_text = "\nThe syncing process was cancelled by the user" + \
        line_exit + line_restart + line_input

    complete_text = "\nThe syncing process has completed successfully" + \
        line_exit + line_time + line_restart + line_input

    handled_error_text = "\nThe error above has occurred " + \
        line_exit + line_restart + line_input

    text = handled_error_text if failure else (
        cancel_text if timer is None else complete_text)
    while True:

        user_inp = input(text)
        user_inp = user_inp.lower().strip()
        if user_inp == "":
            return
        elif user_inp == "time":
            timer.print_times()
            text = line_exit + line_restart + line_input
        elif user_inp == "restart":
            restart()
            return
        else:
            return


def restart():
    thispython = sys.executable
    retval = sp.run(["dpkg", "-s", "gnome-terminal"],
                    stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    if retval.returncode == 0:
        sp.call(["gnome-terminal", "--", thispython,  str(ROOTPATH)+"/pysync"])
    else:
        retval = sp.run(["dpkg", "-s", "xfce4-terminal"],
                        stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        if retval.returncode == 0:
            sp.call(["xfce4-terminal", "-x", thispython, str(ROOTPATH)+"/pysync"])
        else:
            print(
                "Neither gnome-terminal nor xfce4-terminal is available, unable to restart")
            input("Press enter to exit")
            return
    print("A new instance of pysync has been started, this window should close immediately")
