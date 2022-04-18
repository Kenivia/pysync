import os
from threading import Thread
from pysync.FileInfo import FileInfo
from pysync.Timer import logtime


def get_local_files(path,  output_dict=None, timer=None):

    if output_dict is None:
        output_dict = {}
        get_local_info_list(path, output_dict, timer)
    else:
        t = Thread(target=get_local_info_list,
                   args=(path, output_dict,),
                   kwargs={"timer": timer})
        t.start()
        return t
    return output_dict


@logtime
def get_local_info_list(path, out_dict):
    """Adds FileInfo objects to out_dict with their paths as the key
    """
    cur_list = os.listdir(path)

    for _path in cur_list:
        new_path = os.path.join(path, _path)
        if os.path.islink(new_path):
            print(new_path, "is a symbolic link, ignored")
            continue
        file_info = FileInfo("local", path=new_path, md5_now=True)
        
        # * modifies the local_dict in get_local_files
        # * same idea as process_remote
        out_dict[file_info.path] = file_info
        if os.path.isdir(new_path):
            get_local_info_list(new_path, out_dict,)
