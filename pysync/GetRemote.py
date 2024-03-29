import concurrent.futures as cf
from socket import timeout
from time import time
from filelock import FileLock

from pysync.OptionsParser import get_option, get_root
from pysync.RemoteFileInfo import RemoteFileInfo
from pysync.Exit import exit_with_msg
from pysync.Commons import pdump


def kws_to_query(kws_list, equals, operator, exclude_list=[]):
    if equals:
        mimetype = ["mimeType = '" + i + "'" for i in kws_list if i not in exclude_list]
    else:
        mimetype = ["mimeType != '" + i + "'" for i in kws_list if i not in exclude_list]

    return f"({(' '+operator+' ').join(mimetype)}) and trashed = false and 'me' in owners"


def get_remote(drive):
    """Lists remote files that are not in trash and are owned by me

    Args:
        drive (googleapiclient.discovery.Resource): Resource object from service.files() in init_drive

    Returns:
        list: list of dictionaries
    """
    folder_mtype = ["application/vnd.google-apps.folder"]
    gdoc_mtype = [
        'application/vnd.google-apps.document',
        'application/vnd.google-apps.form',
        'application/vnd.google-apps.map',
        'application/vnd.google-apps.presentation',
        'application/vnd.google-apps.spreadsheet',
        'application/vnd.google.colaboratory',
    ]

    folder_args = (drive, [
        'id',
        'name',
        'mimeType',
        'parents',
        'modifiedTime',
    ], kws_to_query(folder_mtype, True, "N/A")
    )
    gdoc_args = (drive, [
        'id',
        'name',
        'mimeType',
        'parents',
        'md5Checksum',
        'webViewLink',
        'modifiedTime',
    ], kws_to_query(gdoc_mtype, True, "or")
    )

    file_args = (drive, [
        'id',
        'name',
        'mimeType',
        'parents',
        'md5Checksum',
        'modifiedTime',
    ], kws_to_query(gdoc_mtype + folder_mtype, False, "and")
    )  # TODO maybe find a way to split this request

    all_args = []
    all_args.append(folder_args)
    all_args.append(gdoc_args)
    all_args.append(file_args)

    results = []

    max_threads = len(all_args) + 1
    with cf.ProcessPoolExecutor(max_workers=max_threads) as executor:
        root_future = executor.submit(get_root_id, drive)
        for item in executor.map(get_remote_proc, all_args):
            results.extend(item)
        root = root_future.result()

    return process_remote(results, root), root


def get_root_id(drive):

    # TODO make this a special object that inherits from BaseFileInfo
    root = drive.get(fileId="root",
                     fields="id").execute()
    return root["id"]


def get_remote_proc(args):

    drive, fields, query = args[0], args[1], args[2]
    out = []

    page_token = None
    while True:
        try:
            response = drive.list(
                spaces="drive",
                q=query,
                pageSize=1000,
                fields=f"nextPageToken, files({','.join(fields)})",
                pageToken=page_token,
            ).execute()
        except timeout as e:
            # ? i can probably make it so that you resume the listing after internet is back? thats kinda confusing tho
            exit_with_msg(msg="Timed out while listing remote files, please check your internet connection",
                              exception=e)

        page_token = response.get('nextPageToken', None)
        out.extend(response.get("files", []))
        if page_token is None:
            break
    return out


def process_remote(raw_files, root):
    """Converts google drive responses into GdriveFileInfo objects

    The difficult part is to find the absolute paths of the files as gdrive only tells you a file's parent

    Args:
        raw_files (list): list of dictionaries from get_remote
        root (str): id of the root folder from get_remote

    Returns:
        dict: GdriveFileInfo with their paths as keys
    """

    folder_list = []
    file_list = []
    assert isinstance(root, str)

    for i in raw_files:
        file_info = RemoteFileInfo(**i)
        if not file_info.isorphan:
            if file_info.isfolder:
                folder_list.append(file_info)
            else:
                file_list.append(file_info)
        else:
            # TODO handle orphan files, which should all be sharedWithMe
            pass

    out_dict = {get_option("PATH"): root}
    id_map = {root: root}
    for i in folder_list + file_list:
        id_map[i.id] = i

    for i in id_map:
        if i == root:
            continue
        id_map[i].parent = id_map[id_map[i].parentID]

    for i in id_map:
        if i == root:
            continue
        out_dict[id_map[i].path] = id_map[i]

    return out_dict


def dump_remote(remote_data, root, pickle_path):

    lock_path = pickle_path + ".lock"
    lock = FileLock(lock_path)

    with lock:
        pdump({"rdata": remote_data,
               "root": root,
               "time": time(),
               "def_not_safe": False}, pickle_path)
        print(f"Dumped remote data at {pickle_path}")


def get_dump_remote(drive):
    pickle_path = get_root() + "/data/Internal/Latest_remote.pkl"
    remote_data, root = get_remote(drive)
    dump_remote(remote_data, root, pickle_path)
    return remote_data, root
