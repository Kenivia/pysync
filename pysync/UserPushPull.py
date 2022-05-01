from pysync.InputParser import replace_numbers
from pysync.Timer import logtime
from pysync.Functions import (
    contains_parent,
    SilentExit,
)
from pysync.Functions import match_attr
from pysync.Options_parser import load_options
from pysync.Exit import restart


def isin_override(info):
    apull, apush, aignore = load_options("APULL", "APUSH", "AIGNORE")
    if contains_parent(apull, info):
        return "pull"
    elif contains_parent(apush, info):
        return "push"
    elif contains_parent(aignore, info):
        return "ignore"
    else:
        return False


def get_default_action(change_type):
    dpull, dpush, dignore = load_options("DPULL", "DPUSH", "DIGNORE")
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
        forced_action = isin_override(info.path)
        if forced_action:
            info.action = forced_action
            info.forced = True
        else:
            info.action = get_default_action(info.change_type)

    return diff_infos


def num_shorten(num_list):
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


def print_half(infos, initing, forced, index):

    actions = ["pull", "push", "ignore"]
    for action in actions:
        this = match_attr(infos, action=action)
        if initing or forced:
            this.sort(key=lambda x: (x.action_human, x.path))
        else:
            this.sort(key=lambda x: (x.index, x.path))

        for i in this:
            if forced:
                if i.action == "ignore" and load_options("HIDE_FIGNORE"):
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


def print_change_types(infos, initing):

    # todo abbreviate folders where all content are new/deleted
    normal = match_attr(infos, forced=False,)
    print_half(normal, initing, False, 1)

    forced = match_attr(infos, forced=True)
    print_half(forced, initing, True, None)


def print_status(infos):
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
            short = num_shorten([i.index for i in cur_actions[key]])
            print("  -" + key + "(" + str(len(cur_actions[key])) + "):", " ".join(short))


def deletion_compression(diff_infos):
    """removes children of folders that are being deleted

    idea being that a deletion of folder would only happen if all children are also being deleted
    this also metigates issues when applying

    this isn't done for creating new files/modifying files for user clarity

    Args:
        diff_infos (list): list of FileInfo objects

    Returns:
        list: modified list
    """
    del_folder = []
    for i in diff_infos:
        if i.isfolder and "del" in i.action_code:
            del_folder.append(i.path)

    indexs = []
    for index, item in enumerate(diff_infos):
        if contains_parent(del_folder, item.path, accept_self=False):
            indexs.append(index)

    for i in reversed(indexs):
        del diff_infos[i]

    return diff_infos


@logtime
def user_push_pull(diff_infos):
    """Prompts the user to change which change types to push/pull
    """
    if not diff_infos:
        return
    initing = True
    text = """Use `push a` or `pull a-b` to change the action of files, e.g push 1-5
Press Enter or use `apply` to apply the following changes:"""
    while True:
        deletion_compression(diff_infos)
        print_change_types(diff_infos, initing)
        initing = False

        print("\n" + text)
        print_status(diff_infos)

        inp = input("\n>>> ").lower()
        inp = inp.strip()
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

        arguments, message = replace_numbers(arguments, len(diff_infos))
        changed = []
        all_index = {}
        for inp in arguments:
            if inp == "all":
                for i in match_attr(diff_infos, forced=False):
                    i.action = command
                    changed.append(str(i.index))

            elif inp.isnumeric():
                # * shouldn't need to check for forced here since forced don't get an index
                if inp not in all_index:
                    for i in diff_infos:
                        if i.index is not None:
                            all_index[str(i.index)] = i
                info = all_index[inp]
                info.action = command
                changed.append(str(info.index))
            else:
                print(inp, "is invalid, ignored")

        changed = num_shorten(changed)
        text = message
        if changed:
            text += "Input interpreted as: " + command + " " + " ".join(changed)
        else:
            text += "Input was not valid, nothing has been changed"
