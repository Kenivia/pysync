import random
import concurrent.futures as cf
import copy

from pysync.ProcessedOptions import (
    EMPTY_OUTPUT,
    MAX_COMPUTE_THREADS,
    PATH,
)
from pysync.UserInterface import logtime


def one_diff(args):
    path, local_dict, remote_dict = args[0], args[1], args[2]
    if path == PATH:
        return False, remote_dict[path]

    in_local = path in local_dict
    in_remote = path in remote_dict
    diff_type = False
    if in_remote and in_local:
        obj = local_dict[path]
        obj.partner = remote_dict[path]
        diff_type = obj.compare_info()

    elif in_local:
        obj = local_dict[path]
        obj.diff_type = diff_type = "local_new"

    elif in_remote:

        obj = remote_dict[path]
        # if not obj.isremotegdoc: # * this line will ignore google docs
        obj.diff_type = diff_type = "remote_new"
    else:
        raise ValueError

    return diff_type, obj


@logtime
def get_diff(local_dict, remote_dict):
    """Finds which change type a file should have and sort them into dictionaries

    assigns the change type to .diff_type of the FileInfo object
    returns a dictionary with 4 keys, corresponding to the type of modification detected
    """

    out = copy.deepcopy(EMPTY_OUTPUT)
    all_keys = set(local_dict).union(set(remote_dict))
    _map = [(path, local_dict, remote_dict)
            for path in all_keys]
    random.shuffle(_map)
    all_infos = {}
    with cf.ProcessPoolExecutor(max_workers=MAX_COMPUTE_THREADS) as executor:
        chunksize = int(len(all_keys)/MAX_COMPUTE_THREADS)
        for diff_type, obj in executor.map(one_diff, _map, chunksize=chunksize):
            # for i in all_res:
            if isinstance(obj, dict):
                all_infos[PATH] = obj
            else:
                all_infos[obj.path] = obj
            if diff_type:
                out[diff_type].append(obj)

    return out, all_infos
