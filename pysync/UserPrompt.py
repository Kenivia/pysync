import pathlib
from pysync.Timer import logtime
from pysync.Functions import contains_parent, SilentExit, match_attr
from pysync.OptionsParser import get_option
from pysync.Exit import restart


# def get_forced_depth(flist, path):
#     max_depth = -1
#     for i in flist:
#         if i == path or pathlib.Path(i) in pathlib.Path(path).parents:
#             depth = len(i.split("/"))
#             if depth > max_depth:
#                 max_depth = depth

#     return max_depth

# def get_forced(path):
#     apull, apush, aignore = get_option("APULL", "APUSH", "AIGNORE")
#     temp = {}

#     temp[get_forced_depth(apush, path)] = "push"
#     temp[get_forced_depth(apull, path)] = "pull"
#     temp[get_forced_depth(aignore, path)] = "ignore"
#     # * in a tie, ignore perfered over pull over push
#     return False if max(temp) < 0 else temp[max(temp)]

def get_forced(info):
    # ! This currently doesn't work correctly when a forced path is contained within another forced path
    
    apull, apush, aignore = get_option("APULL", "APUSH", "AIGNORE")
    if contains_parent(apull, info):
        return "pull"
    elif contains_parent(apush, info):
        return "push"
    elif contains_parent(aignore, info):
        return "ignore"
    else:
        return False


def get_default_action(change_type):
    dpull, dpush, dignore = get_option("DPULL", "DPUSH", "DIGNORE")
    if change_type in dpull:
        return "pull"
    elif change_type in dpush:
        return "push"
    elif change_type in dignore:
        return "ignore"
    else:
        raise ValueError


@logtime
def apply_forced_and_default(diff_infos):

    for info in diff_infos:
        forced_action = get_forced(info.path)
        if forced_action:
            info._action = forced_action
            info.forced = True
        else:
            info._action = get_default_action(info.change_type)

    return diff_infos


def add_hyphens(num_list):
    """Opposite of replace_numbers

    Args:
        num_list (list): list of numbers

    Returns:
        list: abbreviated version of num_list e.g 5,6,7 -> 5-7
    """
    num_list = sorted([int(i) for i in num_list])
    # * doesn't have to take in string, can take int too
    all_segments = []
    cur_segment = []
    for i in num_list:
        if not cur_segment or cur_segment[-1] + 1 == i:
            cur_segment.append(i)
        else:
            all_segments.append(cur_segment)
            cur_segment = [i]
    all_segments.append(cur_segment)

    out = []
    for i in all_segments:
        if len(i) >= 3:
            out.append(str(i[0]) + "-" + str(i[-1]))
        else:
            out.extend([str(i) for i in i])
    return out


def replace_hyphen(inp, upperbound):
    """convert user input into a list of numbers(in strings)

    e.g 2-6 -> 2, 3, 4, 5, 6

    doesn't change non-numerical items in the list

    Args:
        inp (list): list of strings
        upperbound (int): the highest index displayed on screen

    Returns:
        list: list of converted strings
        str: error/warning messages
    """
    message = ""
    out = []
    for item in inp:
        if item.isnumeric():
            if int(item) >= 1 and int(item) <= upperbound:
                if str(item) not in out:
                    out.append(str(item))
            else:
                message += item + " is out of range, ignored. It must be between 1 and " + \
                    str(upperbound) + "\n"

        elif "-" in item and item.split("-")[0].isnumeric() and item.split("-")[1].isnumeric():
            lower = int(item.split("-")[0])
            upper = int(item.split("-")[1])
            if lower >= 1 and upper <= upperbound:
                temp = 0
                for i in range(lower, upper + 1):
                    if str(i) not in out:
                        out.append(str(i))
                    temp += 1
            else:
                message += item + " is out of range, ignored. It must be between 1 and " + \
                    str(upperbound) + "\n"
        else:
            out.append(item)
            # * doesn't touch non-numerical things

    return out, message


def print_half(infos, initing, forced, index):
    # * honestly have no idea how this is working and i dont intend on changing that
    actions = ["pull", "push", "ignore"]
    for action in actions:
        this = match_attr(infos, action=action)
        if initing or forced:
            this.sort(key=lambda x: (x.action_human, x.path))
        else:
            this.sort(key=lambda x: (x.index, x.path))

        for i in this:
            if forced:
                if i.action == "ignore" and get_option("HIDE_FIGNORE"):
                    pass
                else:
                    print(i.action_human, i.path)
            else:
                if initing:
                    i.index = index
                    print(index, i.action_human, i.path)
                else:
                    print(i.index, i.action_human, i.path)
                index += 1


def print_changes(infos, initing):

    normal = match_attr(infos, forced=False,)
    print_half(normal, initing, False, 1)

    forced = match_attr(infos, forced=True)
    print_half(forced, initing, True, None)


def print_totals(infos):

    cur_actions = {}
    for i in infos:
        if i.action_human not in cur_actions:
            cur_actions[i.action_human] = [i]
        else:
            cur_actions[i.action_human].append(i)

    for key in sorted(cur_actions):
        if key.startswith("forced"):
            print("  -" + key + "(" + str(len(cur_actions[key])) + ")")
        else:
            short = add_hyphens([i.index for i in cur_actions[key]])
            print("  -" + key + "(" + str(len(cur_actions[key])) + "):", " ".join(short))


def compress_deletes(diff_infos):
    """removes children of folders that are being deleted

    idea being that a deletion of folder would only happen if all children are also being deleted
    this also mitigate issues when applying

    this isn't done for creating new files/modifying files for user clarity

    Args:
        diff_infos (list): list of FileInfo objects

    Returns:
        list: modified list
    """
    del_folder = []
    for i in diff_infos:
        if i.isfolder and "del" in i.action_code:
            found = False
            for z in del_folder:
                if i.path.startswith(z):
                    found = True
                    break
            if not found:
                del_folder = [z for z in del_folder if not z.startswith(i.path)]
                del_folder.append(i.path)

    indexs = []
    for index, item in enumerate(diff_infos):
        for i in del_folder:
            if item.path.startswith(i) and item.path != i:
                indexs.append(index)

    for i in reversed(indexs):
        del diff_infos[i]

    return diff_infos


@logtime
def choose_changes(diff_infos):
    """Prompts the user to change which change types to push/pull
    """
    if not diff_infos:
        return
    initing = True
    text = """Use `push a` or `pull a-b` to change the action of files, e.g push 1-5
Press Enter or use `apply` to apply the following changes:"""
    while True:
        compress_deletes(diff_infos)
        print_changes(diff_infos, initing)
        initing = False

        print("\n" + text)
        print_totals(diff_infos)

        inp = input("\n>>> ").lower().strip()
        if inp == "":
            return

        inp = inp.replace(",", " ")
        inp = inp.split(" ")
        inp = [i for i in inp if i]  # * remove blanks

        command = inp[0]
        arguments = inp[1:]

        valid_actions = ["push", "pull", "ignore", "apply", "restart", "exit"]
        if not command in valid_actions:
            text = "Unrecognized action, valid actions are: " + \
                ", ".join(valid_actions)
            continue

        if command == "apply":
            if len(arguments) > 0:
                print("apply doesn't take arguments, ignored")
            return

        if command == "exit":
            if len(arguments) > 0:
                print("exit doesn't take arguments, ignored")
            raise SilentExit

        if command == "restart":
            restart()
            if len(arguments) > 0:
                print("restart doesn't take arguments, ignored")
            raise SilentExit

        arguments, message = replace_hyphen(arguments, len(diff_infos))
        changed = []
        all_index = {}
        for i in diff_infos:
            if i.index is not None:
                all_index[str(i.index)] = i
        for inp in arguments:
            if inp == "all":
                for i in match_attr(diff_infos, forced=False):
                    i._action = command
                    changed.append(str(i.index))
                continue

            elif inp.isnumeric():
                # * shouldn't need to check for forced here since forced don't get an index
                if inp not in all_index:
                    message += inp + " is invalid, ignored\n"
                    continue
                info = all_index[inp]
                info._action = command
                changed.append(str(info.index))

            else:
                message += inp + " is invalid, ignored\n"

        changed = add_hyphens(changed)
        text = message
        if changed:
            text += "Input interpreted as: " + command + " " + " ".join(changed)
        else:
            text += "Input was not valid, nothing has been changed"
