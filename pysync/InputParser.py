

from pysync.ProcessedOptions import (
    DEFAULT_IGNORE,
    DEFAULT_PULL,
    DEFAULT_PUSH
)


def replace_type_alias(inp):
    # * should be ran after replace_numbers
    types_alias = []
    for i in DEFAULT_PUSH + DEFAULT_PULL + DEFAULT_IGNORE:
        types_alias.append(i.replace("_", " "))

    out = []

    for index, item in enumerate(inp):
        if item.isnumeric():
            out.append(item)
        if item in DEFAULT_PUSH + DEFAULT_PULL + DEFAULT_IGNORE:
            out.append(item)
        else:
            if index + 1 == len(inp):
                break
            if item + " " + inp[index+1] in types_alias:
                out.append(item + "_" + inp[index+1])
            # del inp[index+1], inp[index]  # * must be in this order

    return out


def change_type_to_action(diff_dict, action_dict, change_type, action):

    action_dict[action].extend(diff_dict[change_type])
    for i in diff_dict[change_type]:
        i.action = action
    


def replace_numbers(inp, upperbound):
    out = []
    for item in inp:
        if item.isnumeric():
            if int(item) >= 1 and int(item) <= upperbound:
                if str(item) not in out:
                    out.append(str(item))
            else:
                print(
                    item, "is out of range, ignored. It must be between 1 and "+str(upperbound))

        elif "-" in item and item.split("-")[0].isnumeric() and item.split("-")[0].isnumeric():
            lower = int(item.split("-")[0])
            upper = int(item.split("-")[1])
            if lower >= 1 and upper <= upperbound:
                temp = 0
                for i in range(lower, upper+1):
                    if str(i) not in out:
                        out.append(str(i))
                    temp += 1
            else:
                print(
                    item, "is out of range, ignored. It must be between 1 and "+str(upperbound))
        else:
            out.append(item)
            # * doesn't touch non-numerical things

    return out


# print(replace_type_alias(["push", "content", "change"]))
