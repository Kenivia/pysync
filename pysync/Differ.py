import random
import concurrent.futures as cf

from pysync.Options_parser import load_options
from pysync.Timer import logtime


def one_diff(args):
    """Determines the change type of one file

    This is implemented this way to allow files to be compared in parallel
    intended to be called using concurrent.future

    Args:
        args (tuple):   1) path to the file
                        2) dict of local FileInfo objects from get_local_files
                        3) dict of remote FileInfo objects from process_remote

    Raises:
        ValueError: if the path is not in either dictionary

    Returns:
        str:  change_type - "local_new", "remote_new", "content_change" or "mtime_change"
        pysync.FileInfo: FileInfo object from either dictionaries, local is preferred
        if the path is PATH, returns False and a dict with information about PATH
    """
    path, local_data, remote_data = args[0], args[1], args[2]
    if path == load_options("PATH"):
        return False, remote_data[path]

    in_local = path in local_data
    in_remote = path in remote_data
    change_type = False
    if in_remote and in_local:
        obj = local_data[path]
        obj.partner = remote_data[path]
        change_type = obj.compare_info()

    elif in_local: # TODO how to determine whether it's remote del or local new 
        obj = local_data[path]
        obj.change_type = change_type = "local_new"

    elif in_remote:

        obj = remote_data[path]
        obj.change_type = change_type = "remote_new"
    else:
        raise ValueError

    return change_type, obj


@logtime
def get_diff(local_data, remote_data):
    """Determines the difference between the two

    Args:
        local_data (dict): dict of local FileInfo objects from get_local_files
        remote_data (dict): dict of remote FileInfo objects from process_remote

    Returns:
        list: list of FileInfo objects that require change
        dict: union of local_data and remote data
    """

    diff_infos = []
    all_keys = set(local_data).union(set(remote_data))
    _map = [(path, local_data, remote_data)
            for path in all_keys]
    random.shuffle(_map)
    all_data = {}
    max_threads = load_options("MAX_COMPUTE")
    with cf.ThreadPoolExecutor(max_workers=max_threads) as executor:
        for change_type, obj in executor.map(one_diff, _map):
            if isinstance(obj, str):
                all_data[load_options("PATH")] = obj
            else:
                all_data[obj.path] = obj
            if change_type:
                
                diff_infos.append(obj)

    return diff_infos, all_data
