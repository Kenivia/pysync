import os
from threading import Thread
import concurrent.futures as cf

from pysync.FileInfo import FileInfo
from pysync.Timer import logtime
from pysync.Options_parser import load_options


def get_local_files(path, output_dict, timer=None):
    """put FileInfo objects into output_dict, then calculate their md5sum.
    
    there was a conscious decision to classify this function as "comp" in the timer.
    this function involves 1) constructing FileInfo objects and 2) calculating md5sum
    both 1) and 2) may be cpu bound OR io bound, depending on the system,
    so it isn't fair to say that it's one or the other.
    
    so end of the day i can't be bothered making a new category for something so murky
    """

    t = Thread(target=_get_local,
               args=(path, output_dict,),
               kwargs={"timer": timer})
    t.start()
    return t


@logtime
def _get_local(path, out_dict):

    get_local_info_list(path, out_dict)
    
    print("Processing local files..")
    # * This calculates md5sum using many threads
    max_threads = load_options("MAX_COMPUTE")
    with cf.ThreadPoolExecutor(max_workers=max_threads) as executor:
        for key in out_dict:
            if not out_dict[key].isfolder:
                executor.submit(out_dict[key].calculate_md5)
    print("Local files done")


def get_local_info_list(path, out_dict):
    """Adds FileInfo objects to out_dict with their paths as the key
    """
    cur_list = os.listdir(path)

    for _path in cur_list:
        new_path = os.path.join(path, _path)
        if os.path.islink(new_path):
            print(new_path, "is a symbolic link, ignored")
            continue
        file_info = FileInfo("local", path=new_path, md5_now=False)

        # * modifies the local_dict in get_local_files
        # * same idea as process_remote
        out_dict[file_info.path] = file_info
        if os.path.isdir(new_path):
            get_local_info_list(new_path, out_dict,)
