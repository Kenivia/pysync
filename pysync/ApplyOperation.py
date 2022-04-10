import time
from threading import (
    Thread,
    active_count,
)

from pysync.UserInterface import (
    assign_action,
    logtime,
)
from pysync.ProcessedOptions import (
    MAX_PUSH_THREADS,
    IGNORE,
    ALWAYS_PULL,
    ALWAYS_PUSH,
    RECHECK_INTERVAL,
    PRINT_PROGRESS,
)
from pysync.Functions import (
    contains_parent,
    flatten_dict
)
from pysync.FileInfo import OperationNotReadyError


def check_override(override_lists, push_pulls, change_type, diff_infos, info):
    """Checks if an info file should be overridden and places it in the appropriate list"""
    count = 0
    # * this is so obscure and complicated i don't want to talk about it but it works
    for i in override_lists:
        if contains_parent(i, info.path):
            push_pulls[count]["override"].append(info)
            diff_infos[change_type].remove(info)
            break
        count += 1


@logtime
def decide_push_pull(diff_dict, push_keys, pull_keys, clear_screen=False):
    """Determines whether a FileInfo object should be pushed or pulled

    Prompts the user using user_push_pull
    diff_infos - returned by get_diff
    timer - see UI.myTimer
    clear_screen - clears the screen if True

    returns a list containing all the FileInfo that needs an operation
    """

    pushing = {"override": []}
    pulling = {"override": []}
    for change_type in sorted(list(diff_dict)):
        for info in diff_dict[change_type]:
            check_override([ALWAYS_PULL, ALWAYS_PUSH, IGNORE],
                           [pulling, pushing, pushing], change_type, diff_dict, info)

        if change_type in push_keys:
            pushing[change_type] = diff_dict[change_type]
        elif change_type in pull_keys:
            pulling[change_type] = diff_dict[change_type]

    assign_action(pushing, pulling, clear_screen)
    out = flatten_dict(pushing)
    out.extend(flatten_dict(pulling))
    return out


@logtime
def run_drive_ops(info_list, path_dict, drive):
    """Run drive_op for each item in info_list in threads

    Will not exceed MAX_PUSH_THREADS at any given time
    After reaching the limit, the function attempts to start another thread every RECHECK_INTERVAL seconds

    prints information to the user as it progress
    """

    intial_thread_count = active_count()
    all_threads = []

    while info_list:
        info_list.sort(key=lambda x: (  # * folders first, then less depth first
            not x.isfolder, len(x.path.split("/"))), reverse=True)
        index = len(info_list)-1
        for _ in range(len(info_list)):
            if active_count() - intial_thread_count >= MAX_PUSH_THREADS:
                time.sleep(RECHECK_INTERVAL)
                break
            item = info_list[index]
            try:
                item.check_possible(path_dict)
                if PRINT_PROGRESS:
                    print(len(info_list), item.action + "ing", item.diff_type,  item.path)
                t = Thread(target=item.drive_op, args=(path_dict, drive))
                t.start()
                all_threads.append(t)
                info_list.remove(item)

            except OperationNotReadyError:
                pass

            index -= 1
    print("Waiting for threads to finish")
    [i.join() for i in all_threads]
