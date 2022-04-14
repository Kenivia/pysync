from pysync.InputParser import (
    replace_numbers
)
from pysync.Timer import logtime
from pysync.Functions import (
    contains_parent,
    match_attr,
    pysyncSilentExit,
    to_ing,
    num_shorten,
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


def print_half(infos, initing, forced, index):

    actions = ["pull", "push", "ignore"]
    for action in actions:
        this = match_attr(infos, action=action)
        if initing:
            this.sort(key=lambda x: x.change_type)
        else:
            this.sort(key=lambda x: (x.index))

        for i in this:
            if forced:
                print(i.change_type, i.path)
            else:
                if initing:
                    i.index = index
                    print(index, i.action_human, i.path)
                else:
                    print(i.index, i.action_human,  i.path)
                index += 1


def print_change_types(infos, initing=False):
    """Prints the paths in diff_paths, sorted based on the type of their modificaiton

    """
    #todo abbreviate folders where all content are new/deleted
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

    for key in cur_actions:
        short = num_shorten([i.index for i in cur_actions[key]])
        print(key + "("+str(len(cur_actions[key])) + "):", " ".join(short))


@logtime
def user_push_pull(diff_infos):
    """Prompts the user to change which change types to push/pull

    """
    initing = True
    text = """Use `push a` or `pull a-b` to change the action of files, e.g push 1-5
Press Enter or use `apply` to apply the changes."""
    while True:
        print_change_types(diff_infos, initing)
        initing = False

        print("\n" + text)
        print_status(diff_infos)

        inp = input("\n>>> ").lower()
        inp = inp.strip()
        if inp == "":
            print("Applying changes")
            return

        inp = inp.replace(",", " ")
        inp = inp.split(" ")
        inp = [i for i in inp if i]  # * remove blanks

        command = inp[0]
        arguments = inp[1:]
        if command == "apply":
            if len(arguments) > 0:
                print("apply doesn't take arguments, ignored")
            print("Applying changes")
            return

        valid_actions = ["push", "pull", "ignore", "restart", "exit"]
        if not command in valid_actions:
            text = "Unrecognized action, valid actions are: " + \
                ", ".join(valid_actions)
            continue

        if command == "exit":
            print("restart doesn't take arguments, ignored")
            raise pysyncSilentExit

        if command == "restart":
            restart()
            print("restart doesn't take arguments, ignored")
            raise pysyncSilentExit

        arguments, message = replace_numbers(arguments, len(diff_infos))
        print(arguments)
        changed = []
        for item in arguments:
            if item == "all":
                for i in match_attr(diff_infos, forced=False):
                    i.action = command
                    changed.append(str(i.index))

            elif item.isnumeric():
                # * shouldn't need to check for forced here since forced don't get an index
                infos = match_attr(diff_infos, index=int(item))
                assert len(infos) == 1
                info = infos[0]
                info.action = command
                changed.append(str(info.index))
            else:
                print(item, "is invalid, ignored")

        changed = num_shorten(changed)
        text = message
        if changed:
            text += "Command interpreted as: " + \
                command + " " + " ".join(changed)
        else:
            text += "Command was not valid, nothing has been changed"
