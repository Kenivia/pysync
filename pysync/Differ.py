import random
import concurrent.futures as cf

from pysync.ProcessedOptions import (
    MAX_COMPUTE_THREADS,
    PATH,
)
from pysync.Timer import logtime


def one_diff(args):
    path, local_dict, remote_dict = args[0], args[1], args[2]
    if path == PATH:
        return False, remote_dict[path]

    in_local = path in local_dict
    in_remote = path in remote_dict
    change_type = False
    if in_remote and in_local:
        obj = local_dict[path]
        obj.partner = remote_dict[path]
        change_type = obj.compare_info()

    elif in_local:
        obj = local_dict[path]
        obj.change_type = change_type = "local_new"

    elif in_remote:

        obj = remote_dict[path]
        obj.change_type = change_type = "remote_new"
    else:
        raise ValueError

    return change_type, obj


@logtime
def get_diff(local_dict, remote_dict):
    """Finds which change type a file should have and sort them into dictionaries

    assigns the change type to .change_type of the FileInfo object
    returns a dictionary with 4 keys, corresponding to the type of modification detected
    """

    diff_infos = []
    all_keys = set(local_dict).union(set(remote_dict))
    _map = [(path, local_dict, remote_dict)
            for path in all_keys]
    random.shuffle(_map)
    all_path_dict = {}
    with cf.ProcessPoolExecutor(max_workers=MAX_COMPUTE_THREADS) as executor:
        chunksize = int(len(all_keys)/MAX_COMPUTE_THREADS)
        for change_type, obj in executor.map(one_diff, _map, chunksize=chunksize):
            if isinstance(obj, dict):
                all_path_dict[PATH] = obj
            else:
                all_path_dict[obj.path] = obj
            if change_type:
                diff_infos.append(obj)

    return diff_infos, all_path_dict
