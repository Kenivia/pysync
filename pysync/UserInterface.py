import time
import subprocess as sp
from functools import wraps

from pysync.ProcessedOptions import CHECK_MD5

class FuncTimer():

    def __init__(self,  func_title, time_type):
        """Timer for one function
        """

        self.reset()
        self.usertime = None
        self.func_title = func_title
        self.time_type = time_type

    def reset(self):
        self.start_time = None
        self.duration = 0

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        if self.start_time is None:
            return self.duration

        self.duration += time.perf_counter() - self.start_time
        self.start_time = None
        return self.duration


class TimeLogger():
    def __init__(self, decimal=2):
        self.dp = decimal
        self.times = []

    def comp(self, func_title=None):
        self.times.append(FuncTimer(func_title, "comp"))
        return self

    def user(self, func_title=None):
        self.times.append(FuncTimer(func_title, "user"))
        return self

    def load(self, func_title=None):
        self.times.append(FuncTimer(func_title, "load"))
        return self

    def print_times(self):
        usersum, compsum, loadsum = 0, 0, 0
        label_str = "Stages"
        usr_str = "User inputs"
        comp_str = "Computations"
        load_str = "Uploads & downloads"
        total_str = "Total time"
        all_len = [len(i.func_title if i.func_title is not None else "")
                   for i in self.times]
        all_len.extend([len(i)
                        for i in [usr_str, comp_str, load_str, total_str, label_str]])
        max_len = max(all_len) + 3
        print()
        for i in self.times:
            if i.func_title is not None:
                print(i.func_title.ljust(max_len, " "),
                      round(i.duration, self.dp))
            if i.time_type == "user":
                usersum += i.duration
            elif i.time_type == "comp":
                compsum += i.duration
            elif i.time_type == "load":
                loadsum += i.duration

        total = usersum + compsum + loadsum
        print("-"*(max_len+12))
        print(label_str.ljust(max_len, " "), "Time taken")
        print(usr_str.ljust(max_len, " "), round(usersum, self.dp))
        print(comp_str.ljust(max_len, " "), round(compsum, self.dp))
        print(load_str.ljust(max_len, " "), round(loadsum, self.dp))
        print(total_str.ljust(max_len, " "), round(total, self.dp))


def logtime(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        assert "timer" in kwargs
        timer = kwargs["timer"]
        del kwargs["timer"]
        timer.times[-1].start()

        result = func(*args, **kwargs)
        timer.times[-1].stop()
        return result
    return wrap


# def confirm(message, timer):
#     """Prompts the user for permission to continue

#     message will be printed with `[y/N]:` added on the end
#     timer - see UI.myTimer
#     raises KeyboardInterrupt when aborted
#     """
#     timer.stop()
#     user_inp = input(f"{message} [y/N]:").lower()
#     if not (user_inp == "y" or user_inp == "yes"):
#         input("Aborted")
#         raise(KeyboardInterrupt)
#     timer.start()


@logtime
def print_diff_types(diff_paths,  clear_previous=True):
    """Prints the paths in diff_paths, sorted based on the type of their modificaiton

    will clear the screen if clear_previous is True(default True)
    returns True if anything has been printed
    """

    printed = False
    if clear_previous:
        sp.run(["clear"])
    else:
        print("\n"+"_"*20+"\n")
    for change_type in sorted(list(diff_paths)):
        for info in diff_paths[change_type]:
            print(change_type, info.path)
            printed = True
        if diff_paths[change_type]:
            print()

    return printed


def assign_action(pushing, pulling, clear_previous=True):
    """sets .action of the objects in pushing & pulling to `push` and `pull` respectively

    also prints the action, type and path of the files
    clear_previous - will clear the screen if clear_previous is True(default True)
    """
    if clear_previous:
        sp.run(["clear"])
    else:
        print("\n"+"_"*20+"\n")
    printed = False
    for change_type in sorted(list(pushing)):
        for info in pushing[change_type]:
            print("push", change_type, info.path)
            info.action = "push"
            printed = True
    if printed:
        print()

    for change_type in sorted(list(pulling)):
        for info in pulling[change_type]:
            print("pull", change_type, info.path)
            info.action = "pull"


@logtime
def user_push_pull(push_keys, pull_keys, diff_infos):
    """Prompts the user to change which change types to push/pull

    push_keys and pull_keys - default push and pull keys
    diff_infos - infos returned by get_diff
    timer - see UI.myTimer
    """
    print("\nType `push <change_type> or pull <change_type> to modify actions")
    print("Type `done` or nothing to apply the changes")
    while True:
        pushing_str = ", ".join(
            [i+"("+str(len(diff_infos[i]))+")" for i in push_keys])
        pulling_str = ", ".join(
            [i+"("+str(len(diff_infos[i]))+")" for i in pull_keys])
        ask_str = ""
        if pushing_str:
            ask_str += "Pushing: " + pushing_str + "\n"
        if pulling_str:
            ask_str += "Pulling: " + pulling_str+"\n"
        # ask_str +=
        command_alias = {}
        types_alias = {}
        for i in push_keys:
            types_alias[i] = [i, i.replace("_", " ")]
        for i in pull_keys:
            types_alias[i] = [i, i.replace("_", " ")]

        command_alias["done"] = ["done", "", "d"]
        command_alias["push"] = ["push", "s"]
        command_alias["pull"] = ["pull", "l"]

        print(ask_str)
        inp = input(">>> ").lower()
        
        command = inp.split(" ")[0]
        isdone = command in command_alias["done"]
        if isdone:
            print("User modification finished")
            break
        ispush = command in command_alias["push"]
        ispull = command in command_alias["pull"]
        if not (ispush or ispull):
            print("Unrecognized command, `done`, `push`, `pull` are accepted")
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


def print_start():
    """Prints whether or not md5sum will be checked"""
    if CHECK_MD5:
        print("Will check md5sum")
    else:
        print("Will not check md5sum")
