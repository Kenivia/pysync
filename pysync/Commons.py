import os
import pathlib
import pickle as pkl
import time
import subprocess as sp

from pathlib import PurePath
from datetime import datetime, timezone

"""
This file defines miscellaneous functions that:
    - don't depend on ANY files or functions in pysync other than this file
    - complete a standalone task
    - are flexible for use in a variety of situations

"""


def readable(start, finish=time.time()):
    timestamp = datetime.fromtimestamp(start)
    ago = datetime.fromtimestamp(finish) - timestamp

    str_ago = str(ago).split(".")[0]
    str_timestamp = str(timestamp).split(".")[0]
    unix = ago.total_seconds()
    return str_ago, str_timestamp, unix


def bind_socket(socket_name):
    import socket
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    # Create an abstract socket, by prefixing it with null.
    s.bind(f'\0{socket_name}')


def check_acknowledgement():
    return os.path.isfile(get_root() + "/data/Internal/abuse_acknowledged")


def pdump(obj, path):
    pkl.dump(obj, open(path, "wb"))


def pload(path):
    return pkl.load(open(path, "rb"))


def add_zero(inp):
    assert isinstance(inp, str)
    assert len(inp) == 1 or len(inp) == 2
    if len(inp) == 1:
        inp = "0" + inp
    return inp


def get_today_name():
    _date = time.localtime()
    day = add_zero(str(_date.tm_mday))
    mon = add_zero(str(_date.tm_mon))
    year = str(_date.tm_year)
    hour = add_zero(str(_date.tm_hour))
    minu = add_zero(str(_date.tm_min))
    sec = add_zero(str(_date.tm_sec))

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
    # TODO im sure there's a better way of doing this but i can't find it
    return str(PurePath(__file__).parent.parent)


def local_to_utc(utc_dt):
    LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo
    return utc_dt.replace(tzinfo=LOCAL_TIMEZONE).astimezone(tz=timezone.utc)


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


class SilentExit(BaseException):
    pass


def match_attr(infos, **kwargs):
    # * e.g action = push, action = pull
    # * operates on a OR basis for multiple kwargs, satisfy any one of them
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
