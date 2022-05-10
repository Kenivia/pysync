import os
from threading import (
    Thread,
    main_thread,
)
import concurrent.futures as cf

from pysync.FileInfo import FileInfo
from pysync.Timer import logtime
from pysync.OptionParser import load_options


def get_local(path, output_dict, timer=None):
    """put FileInfo objects into output_dict and calculate their md5sum.
    """

    t = Thread(target=real_get_local, args=(path, output_dict,),
               kwargs={"timer": timer})
    t.start()
    return t


def filter_link(inp):
    out = []
    for i in inp:
        if os.path.islink(i):
            print(i + " is a symlink, ignored")
        else:
            out.append(i)
    return out


@logtime
def real_get_local(path, out_dict):
    """Adds FileInfo objects to out_dict with their paths as the key
    """
    all_file, all_folder = [],[]
    for parent, dirs, files in os.walk(path):

        all_file.extend(filter_link([os.path.join(parent, names) for names in files]))
        all_folder.extend([os.path.join(parent, names) for names in dirs])


    max_threads = load_options("MAX_COMPUTE")
    with cf.ThreadPoolExecutor(max_workers=max_threads) as executor:

        for info in executor.map(lambda path:
                                 FileInfo("local", type="file", path=path, md5_now=True),
                                 all_file):
            out_dict[info.path] = info

        for info in executor.map(lambda path:
                                 FileInfo("local", type="folder", path=path),
                                 all_folder):
            out_dict[info.path] = info
