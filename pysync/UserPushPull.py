from pysync.InputParser import (
    replace_type_alias,
    replace_numbers
)
from pysync.Timer import logtime
from pysync.Functions import (
    contains_parent,
    match_attr,
    pysyncSilentExit,
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
from pysync.Exit import restart



def print_half(infos, initing, forced, index):

    actions = ["pull", "push", "ignore"]
    for action in actions:
        this = match_attr(infos, action=action)
        if this:
            if forced:
                print("\n" + "FORCED " + to_ing(action))
            else:
                print("\n" + to_ing(action))
        if initing:
            this.sort(key=lambda x: x.change_type)
        else:
            this.sort(key=lambda x: (x.change_type, x.index))

        for i in this:
            if forced:
                print(i.change_type, i.path)
            else:
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
    index = print_half(normal, initing, False, 1)

    forced = match_attr(infos, forced=True)
    print_half(forced, initing, True, None)


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
    text = """Use `push <change type> or pull <change type> to modify actions(Underscores are not necessary)
Use `push <number>` to change the action of a single file
Press Enter or use `apply` to apply the above changes."""
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
        arguments = inp[1:]
        if command == "apply":
            if len(arguments) > 0:
                text = " Apply doesn't take more arguments, ignored"
            return

        valid_actions = ["push", "pull", "ignore", "restart"]
        if not command in valid_actions:
            text = "Unrecognized action, valid actions are: " + \
                ", ".join(valid_actions)
            continue
        if command == "restart":
            restart()
            raise pysyncSilentExit
        arguments, message = replace_numbers(arguments, len(diff_infos))
        arguments = replace_type_alias(arguments)
        

        changed = []
        for item in arguments:
            if item in DEFAULT_PUSH + DEFAULT_PULL + DEFAULT_IGNORE:
                for i in match_attr(diff_infos, change_type=item, forced=False):
                    i.action = command
                    changed.append(str(i.index))
                
            elif item == "all":
                for i in match_attr(diff_infos, forced=False):
                    i.action = command
                    changed.append(str(i.index))
                    
            elif item.isnumeric():
                for i in match_attr(diff_infos, index=int(item)): # * shouldn't need to check for forced here
                    assert not i.forced
                    i.action = command
                    changed.append(str(i.index))
                    
        text = message
        if changed:
            text += "Command interpreted as: " + command + " " + " ".join(changed)
        else:
            text += "Command was not valid, nothing has been changed"
