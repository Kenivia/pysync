

def replace_numbers(inp, upperbound):
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
