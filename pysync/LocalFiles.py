import os

from pysync.FileInfo import FileInfo
from pysync.UserInterface import logtime


@logtime
def get_local_files(path):
    local_dict = {}
    get_local_info_list(path, local_dict,)
    return local_dict


def get_local_info_list(path, out_dict):
    """Adds FileInfo objects to out_dict with their paths as the key

    ignores files that should be ignored
    """
    cur_list = os.listdir(path)

    for _path in cur_list:
        new_path = os.path.join(path, _path)
        file_info = FileInfo("local", path=new_path, md5_now=False)
        if file_info.ignore_me:
            continue

        # * modifies out_dict in compare_local_file
        out_dict[file_info.path] = file_info
        if os.path.isdir(new_path):
            get_local_info_list(new_path, out_dict,)
