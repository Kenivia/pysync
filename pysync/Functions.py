import os
import pathlib
import datetime as dt
import hashlib as hl

from threading import Thread


"""
This file defines miscellaneous functions that:
    - don't depend on ANY other files or functions in pysync
    - complete a standalone task
    - are flexible for use in a variety of situations

"""


class pysyncSilentExit(Exception):
    pass


def error_report(exception_object, text, full_text=False):
    """raises the error(prints the traceback) without exiting"""
    def raise_this_error(error):
        # * for use as the target for Thread
        raise error
    try:
        if full_text:
            print(text)
        else:
            print("The following error occured " + text)
        t = Thread(target=raise_this_error, args=(exception_object,))
        t.start()

    finally:
        t.join()


def match_attr(infos, **kwargs):
    # * doesn't support multiple values
    # * e.g action = push, action = pull because there's no way of knowing
    # * whether it should be AND or OR or whatever
    # * should probably do it case by case
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




def contains_parent(parents_list, inp, accept_self=True):
    """Returns True if:
    - parents_list is a list and contain a parent of inp
    - OR parent_list is a str and is a parent of inp

    if accept_self is true, inp itself is considered a parent of itself

    """
    if isinstance(parents_list, str):
        if pathlib.Path(parents_list) in pathlib.Path(inp).parents:
            return True
        if accept_self and inp == parents_list:
            return True
        return False
    else:
        for i in parents_list:
            if pathlib.Path(i) in pathlib.Path(inp).parents:
                return True
            if accept_self and inp == i:
                return True
        return False


def hex_md5_file(path):
    return hl.md5(open(path, 'rb').read()).hexdigest()


def append_slash(path):
    return path if path.endswith("/") else path + "/"


def remove_slash(path):
    return path[:-1] if path.endswith("/") else path


def abs_path(inp):
    """Converts inp into an absolute path

    takes care of: "..", ".", "~" and when there's no prefix
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


def assert_start(start, inp_list):
    for i in inp_list:
        assert i.startswith(start)
