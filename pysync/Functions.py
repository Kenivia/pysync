import os
import pathlib
import hashlib as hl
import pickle as pkl
import time as ti
import subprocess as sp

from pathlib import PurePath
from datetime import (
    datetime,
    timezone,
)

"""
This file defines miscellaneous functions that:
    - don't depend on ANY files or functions in pysync other than this file
    - complete a standalone task
    - are flexible for use in a variety of situations

"""


def pdump(obj, path):
    pkl.dump(obj, open(path, "wb"))


def pload(path):
    return pkl.load(open(path, "rb"))


def AddZero(inp):
    assert isinstance(inp, str)
    assert len(inp) == 1 or len(inp) == 2
    if len(inp) == 1:
        inp = "0" + inp
    return inp


def get_today_name():
    _date = ti.localtime()
    day = AddZero(str(_date.tm_mday))
    mon = AddZero(str(_date.tm_mon))
    year = str(_date.tm_year)
    hour = AddZero(str(_date.tm_hour))
    minu = AddZero(str(_date.tm_min))
    sec = AddZero(str(_date.tm_sec))

    date = year + "." + mon + "." + day
    time = hour + "." + minu + "." + sec
    return date + "-" + time


def dump_test_pkl(obj, name, datetime=None):
    if datetime is None:
        datetime = get_today_name()
    folderpath = get_root() + "/test_pkl/{}/".format(datetime)
    if not os.path.isdir(folderpath):
        sp.run(["mkdir", folderpath])

    pdump(obj, folderpath + name)
    return datetime


def get_root():
    return str(PurePath(__file__).parent.parent)


def local_to_utc(utc_dt):
    LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo
    return utc_dt.replace(tzinfo=LOCAL_TIMEZONE).astimezone(tz=timezone.utc)


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


class SilentExit(Exception):
    pass


def match_attr(infos, **kwargs):
    # * doesn't support multiple values
    # * e.g action = push, action = pull because there's no way of knowing
    # * whether it should be AND or OR or whatever
    # * instead, it should be done case by case
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
    hash_md5 = hl.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


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
