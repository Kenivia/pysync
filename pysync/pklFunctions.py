import pickle as pkl
import time as ti
import os
import subprocess as sp

from pysync.OptionParser import load_options


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
    folderpath = load_options("ROOT") + "/test_pkl/{}/".format(datetime)
    if not os.path.isdir(folderpath):
        sp.run(["mkdir", folderpath])

    pdump(obj, folderpath + name)
    return datetime
