import sys
import subprocess as sp

from pysync.ProcessedOptions import ROOTPATH
from pysync.Timer import logtime

"""
pysync doesn't have a real UI to talk about so this file also contains
some functions associated with the user
"""


def pre_exit_optoins(timer=None, failure=False):

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


def assign_action(pushing, pulling):
    """
    sets .action of the objects in pushing & pulling to `push` and `pull` respectively
    """

    for change_type in sorted(list(pushing)):
        for info in pushing[change_type]:
            # print("push", change_type, info.path)
            info.action = "push"

    for change_type in sorted(list(pulling)):
        for info in pulling[change_type]:
            # print("pull", change_type, info.path)
            info.action = "pull"


def print_diff_types(diff_paths):
    """Prints the paths in diff_paths, sorted based on the type of their modificaiton

    will clear the screen if clear_previous is True(default True)
    returns True if anything has been printed
    """

    print("\n"+"_"*20+"\n")
    for change_type in sorted(list(diff_paths)):
        for info in diff_paths[change_type]:
            print(change_type, info.path)
        if diff_paths[change_type]:
            print()


@logtime
def user_push_pull(push_keys, pull_keys, diff_infos):
    """Prompts the user to change which change types to push/pull

    push_keys and pull_keys - default push and pull keys
    diff_infos - infos returned by get_diff
    timer - see UI.myTimer
    """

    while True:
        print_diff_types(diff_infos)
        print("\tUse `push <change_type> or pull <change_type> to modify actions")
        print("\tUnderscores are not necessary, e.g local_new = local new")
        print("\tPress Enter or use `apply` to apply the above changes.")
        print("")

        pushing_str = ", ".join(
            [i+"("+str(len(diff_infos[i]))+")" for i in push_keys])
        pulling_str = ", ".join(
            [i+"("+str(len(diff_infos[i]))+")" for i in pull_keys])
        ask_str = ""
        if pushing_str:
            ask_str += "\tPushing: " + pushing_str + "\n"
        if pulling_str:
            ask_str += "\tPulling: " + pulling_str+"\n"

        command_alias = {}
        types_alias = {}
        for i in push_keys:
            types_alias[i] = [i, i.replace("_", " ")]
        for i in pull_keys:
            types_alias[i] = [i, i.replace("_", " ")]
        command_alias["apply"] = ["apply", "",]
        command_alias["push"] = ["push", ]
        command_alias["pull"] = ["pull",]

        print(ask_str)
        inp = input(">>> ").lower()

        command = inp.split(" ")[0]
        isapply = command in command_alias["apply"]
        if isapply:
            print("User modification finished")
            break
        ispush = command in command_alias["push"]
        ispull = command in command_alias["pull"]
        if not (ispush or ispull):
            print("Unrecognized command, `apply`, `push`, `pull` are accepted")
            continue
        assert not (ispush and ispull)

        _type = " ".join(inp.split(" ")[1:])
        for i in types_alias:
            if _type in types_alias[i]:
                change_type = i
                break
        else:
            print("Unrecognized input, only items in Pushing and Pulling are accepted")
            continue

        push_keys.remove(change_type) if change_type in push_keys else None
        pull_keys.remove(change_type) if change_type in pull_keys else None
        push_keys.append(
            change_type) if ispush else pull_keys.append(change_type)

    return push_keys, pull_keys
