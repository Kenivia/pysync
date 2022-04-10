import os
import pathlib
import datetime as dt
import hashlib as hl
import subprocess as sp
import sys
import pkg_resources
from threading import Thread


"""
This file defines miscellaneous functions that:
    - don't depend on any other files in pysync
    - complete a standalone task            
    - are flexible for use in a variety of situations
    
"""


class pysyncSilentExit(Exception):
    pass


def to_ing(inp):
    return inp[0:-1].upper() + "ING" if inp.upper() == "IGNORE" else inp.upper() + "ING"


def match_attr(infos, **kwargs):
    out = []
    for i in infos:
        matched = True
        for key in kwargs:
            if getattr(i, key) != kwargs[key]:
                matched = False
                break
        if matched:
            out.append(i)
    return out


def raise_this_error(error):
    # * for use as the target for Thread
    raise error


def error_report(exception_object, text, full_text=False, raise_exception=True):
    try:
        if full_text:
            print(text)
        else:
            print("The following error occured " + text)
        t = Thread(target=raise_this_error, args=(exception_object,))
        t.start()

    finally:
        t.join()
        if raise_exception:
            raise HandledpysyncException()


# def cancel_report():
#     raise KeyboardInterrupt


def init_libraries():

    required = {'pydrive2', 'send2trash', }
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = list(required - installed)

    if missing:
        missingtext = ", ".join(missing)
        command_list = [sys.executable, '-m', 'pip', 'install', *missing]
        print("The following packages are required by pysync:")
        print("\t" + missingtext)
        print("The following command will be ran:")
        print("\t" + " ".join(command_list))
        inp = input("Proceed (y/N)? ")
        if inp.lower() == "y":
            print("")
            completed = sp.run(command_list)
            if completed.returncode != 0:
                print("An error occured while running the command above")
                return False
            print("")  # * looks better
            return True
        else:
            print("Installation was cancelled by the user")
            return False
    else:
        return True


class HandledpysyncException(Exception):
    pass


def contains_parent(parents_list, inp):
    """Returns True if parents_list contain(or equal to) a parent of inp
    designed for use with ALWAYS_PULL etc"""
    for i in parents_list:
        if pathlib.Path(i) in pathlib.Path(inp).parents or inp == i:
            return True
    return False


def human_time(start, now=None):
    """Calculates the difference between two times or changes one into human readable"""
    if now is not None:
        value = dt.datetime.fromtimestamp(now)\
            - dt.datetime.fromtimestamp(start)
    else:
        if start >= 0:
            value = dt.datetime.fromtimestamp(start)\
                - dt.datetime.fromtimestamp(0)

    value = str(value)
    value = value.split(".")[0]
    return value


def flatten_dict(inp):
    """Flattens a dictionary of lists into a 1 dimensional list"""
    out = []
    for i in sorted(list(inp)):
        out.extend(inp[i])
    return out


def hex_md5_file(path):
    return hl.md5(open(path, 'rb').read()).hexdigest()


def append_slash(path):
    return path if path.endswith("/") else path + "/"


def remove_slash(path):
    return path[:-1] if path.endswith("/") else path


def relative_depth(parent_path, child_path):
    child_path = append_slash(child_path)
    parent_path = append_slash(parent_path)
    return len(child_path.split("/")) - len(parent_path.split("/"))


def union_dicts(dict1, dict2):
    """Unions two dictionaries like a set

    WARNING this modifies dict1 into the new, combined dictionary
    also returns that dictionary 
    """
    all_dict = dict1
    for i in dict2:
        if i not in all_dict:
            all_dict[i] = dict2[i]
    return all_dict


# def get_pkl(path):
#     return pkl.load(open(path, "rb"))


def abs_path(inp):
    """Converts a path into absolute path

    takes care of: "..", ".", "~" and no prefix
    the path will behave just like in terminals
    This is different to os.path.abspath, which just adds cwd to the front
    """
    if inp.startswith(".."):
        return "/".join(os.getcwd().split("/")[0:-1]) + inp[2:]
    elif inp.startswith("."):
        return os.getcwd() + inp[1:]

    elif inp.startswith("~"):
        return str(os.path.expanduser("~")) + inp[1:]

    elif not inp.startswith("/"):
        return os.getcwd() + "/" + inp
    else:
        return inp


def gen_exe(url, signatures):
    text = f"""xdg-open {url}
#This file was created by pysync. Do not remove the line below!
{signatures}"""
    return text


class FileIDNotFoundError(Exception):
    pass


def get_id_exe(text):
    for line in text.split("\n"):
        if line.startswith("xdg-open https://docs.google.com/"):
            split = text.split("/")
            for index, item in enumerate(split):
                if item == "d":  # * the id is after a /d/ sequence
                    return split[index+1]
    raise FileIDNotFoundError()


def assert_start(start, inp_list):
    for i in inp_list:
        assert i.startswith(start)
