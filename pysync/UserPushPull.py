from attr import attr
from pysync.InputParser import (
    change_type_to_action,
    replace_type_alias,
    replace_numbers
)
from pysync.Timer import logtime
from pysync.Functions import (
    contains_parent,
    flatten_dict,
    match_attr,
    to_ing,
)
from pysync.ProcessedOptions import (
    ALWAYS_PULL,
    ALWAYS_PUSH,
    ALWAYS_IGNORE,
    DEFAULT_PULL,
    DEFAULT_PUSH,
    DEFAULT_IGNORE,

)


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


@logtime
def decide_push_pull(diff_dict, push_keys, pull_keys):
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
            check_override([ALWAYS_PULL, ALWAYS_PUSH, ALWAYS_IGNORE],
                           [pulling, pushing, pushing], change_type, diff_dict, info)

        if change_type in push_keys:
            pushing[change_type] = diff_dict[change_type]
        elif change_type in pull_keys:
            pulling[change_type] = diff_dict[change_type]

    assign_action(pushing, pulling)
    out = flatten_dict(pushing)
    out.extend(flatten_dict(pulling))
    return out


def print_half(infos, initing, index):

    actions = ["pull", "push", "ignore"]
    for action in actions:
        this = match_attr(infos, action=action)
        if this:
            print("\n" + to_ing(action))
        if initing:
            this.sort(key=lambda x: x.change_type)
        else:
            this.sort(key=lambda x: (x.change_type, x.index))

        for i in this:
            if initing:
                i.index = index
                print(index, i.change_type, i.path)
            else:
                print(i.index, i.change_type, i.path)
            index += 1
    return index


def print_change_types(infos, initing=False):
    """Prints the paths in diff_paths, sorted based on the type of their modificaiton

    """
    normal = match_attr(infos, forced=False, )
    index = print_half(normal, initing, 0)

    forced = match_attr(infos, forced=True)
    print_half(forced, initing, index)


def in_override(info):
    if contains_parent(ALWAYS_PULL, info):
        return "pull"
    elif contains_parent(ALWAYS_PUSH, info):
        return "push"
    elif contains_parent(ALWAYS_IGNORE, info):
        return "ignore"
    else:
        return False


def get_action(change_type):
    if change_type in DEFAULT_IGNORE:
        return "ignore"
    if change_type in DEFAULT_PULL:
        return "pull"
    if change_type in DEFAULT_PUSH:
        return "push"


def apply_forced_and_default(diff_infos):

    for info in diff_infos:
        forced_action = in_override(info.path)
        if forced_action:
            info.action = forced_action
            info.forced = True
        else:
            info.action = get_action(info.change_type)

    return diff_infos


@logtime
def user_push_pull(diff_infos):
    """Prompts the user to change which change types to push/pull

    """
    initing = True
    text = """\tUse `push <change type> or pull <change type> to modify actions(Underscores are not necessary)
\tUse `push <number>` to change the action of a single file
\tPress Enter or use `apply` to apply the above changes."""
    while True:
        print_change_types(diff_infos, initing)
        initing = False

        print("\n" + text)

        inp = input("\n>>> ").lower()
        if inp == "":
            return
        inp = inp.replace(",", " ")
        inp = inp.split(" ")

        command = inp[0]
        agruments = inp[1:]
        if command == "apply":
            if len(agruments) > 0:
                text = "\t Apply doesn't take more arguments, ignored"
            return

        valid_actions = ["push", "pull", "ignore"]
        if not command in valid_actions:
            text = "\tUnrecognized command, valid commands are: " + \
                ", ".join(valid_actions)
            continue
        agruments = replace_numbers(agruments, len(diff_infos))
        agruments = replace_type_alias(agruments)
        

        changed = []
        for item in agruments:
            if item in DEFAULT_PUSH + DEFAULT_PULL + DEFAULT_IGNORE:
                for i in match_attr(diff_infos, change_type=item):
                    i.action = command
                    changed.append(str(i.index))

            elif item.isnumeric():
                for i in match_attr(diff_infos, index=int(item)):
                    i.action = command
                    changed.append(str(i.index))
        
        print("Now " + to_ing(command).lower() +" " + ", ".join(changed))
