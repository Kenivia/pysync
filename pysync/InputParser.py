from pysync.ProcessedOptions import (
    DEFAULT_IGNORE,
    DEFAULT_PULL,
    DEFAULT_PUSH
)


def change_type_to_action(diff_dict, action_dict, change_type, action):
    """give the Info the appropriate action based on the change_type"""
    action_dict[action].extend(diff_dict[change_type])
    for i in diff_dict[change_type]:
        i.action = action


def replace_numbers(inp, upperbound):
    message = ""
    out = []
    for item in inp:
        if item.isnumeric():
            if int(item) >= 1 and int(item) <= upperbound:
                if str(item) not in out:
                    out.append(str(item))
            else:
                message += item + " is out of range, ignored. It must be between 1 and " + str(upperbound) + "\n"

        elif "-" in item and item.split("-")[0].isnumeric() and item.split("-")[1].isnumeric():
            lower = int(item.split("-")[0])
            upper = int(item.split("-")[1])
            if lower >= 1 and upper <= upperbound:
                temp = 0
                for i in range(lower, upper+1):
                    if str(i) not in out:
                        out.append(str(i))
                    temp += 1
            else:
                message += item + " is out of range, ignored. It must be between 1 and " + str(upperbound) + "\n"
        else:
            out.append(item)
            # * doesn't touch non-numerical things

    return out, message
