from pysync.Timer import logtime


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
    all_data = {}
    local = set(local_data.keys())
    remote = set(remote_data.keys())

    in_both = local & remote
    only_local = local - remote
    only_remote = remote - local

    for path in only_local:
        f = local_data[path]
        f.change_type = "local_new"

        diff_infos.append(f)
        all_data[path] = f

    for path in only_remote:
        f = remote_data[path]
        if isinstance(f, str):
            continue
        f.change_type = "remote_new"

        diff_infos.append(f)
        all_data[path] = f

    for path in in_both:
        f = local_data[path]
        f.partner = remote_data[path]
        if f.compare_info():
            diff_infos.append(f)
        all_data[path] = f

    return diff_infos, all_data
