import os
from threading import Thread
import concurrent.futures as cf

from pysync.LocalFileInfo import LocalFileInfo
from pysync.OptionsParser import get_option


def get_local(path, output_dict, timer=None):

    t = Thread(target=real_get_local, args=(path, output_dict,),
               kwargs={"timer": timer})
    t.start()
    return t


def filter_link(inp):
    out = []
    for i in inp:
        path = i[0]
        if os.path.islink(path):
            print(path + " is a symlink, ignored")
            # * can't be bothered making this comply with `Print absolute path`
        else:
            out.append(i)
    return out



def real_get_local(path, out_dict):
    """Adds FileInfo objects to out_dict with their paths as the key"""
    # TODO interrupt this with Signal?

    file_paths, folder_paths = [], []
    for parent, dirs, files in os.walk(path):
        file_paths.extend(filter_link(
            [(os.path.join(parent, names), "file") for names in files]))
        folder_paths.extend(
            [(os.path.join(parent, names), "folder") for names in dirs])

    max_threads = get_option("MAX_COMPUTE")
    with cf.ThreadPoolExecutor(max_workers=max_threads) as executor:
        for info in executor.map(lambda inp:
                                 LocalFileInfo(
                                     type=inp[1], path=inp[0], check_md5=get_option("CHECK_MD5")),
                                 file_paths + folder_paths):
            out_dict[info.path] = info
    # print("Finished loading local files")
#
