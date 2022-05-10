import concurrent.futures as cf

from socket import timeout

from pysync.Timer import logtime
from pysync.OptionParser import load_options
from pysync.FileInfo import FileInfo
from pysync.Exit import exc_with_message


def kws_to_query(kws_list, equals, operator, exclude_list=[]):
    if equals:
        mimetype = ["mimeType = '" + i + "'" for i in kws_list if i not in exclude_list]
    else:
        mimetype = ["mimeType != '" + i + "'" for i in kws_list if i not in exclude_list]

    return f"({(' '+operator+' ').join(mimetype)}) and trashed = false and 'me' in owners"


@logtime
def get_remote(drive):
    """Lists remote files that are not in trash and are owned by me"""
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
        for item in executor.map(get_remote_thread, all_args):
            results.extend(item)

    return results, get_root_id(drive)


def get_root_id(drive):

    root = drive.get(fileId="root",
                     fields="id").execute()
    return root["id"]


def get_remote_thread(args):

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
        except timeout:
            # ? i can probably make it so that you resume the listing after internet is back? thats kinda confusing tho
            exc_with_message(
                "Timed out while listing remote files, please check your internet connection")

        page_token = response.get('nextPageToken', None)
        out.extend(response.get("files", []))
        if page_token is None:
            break
    return out


def get_one_parent(folders, root, info):

    parent = root
    for i in folders:
        if info.parentID == i.id:
            parent = i
            break
    return parent


def get_one_path(folders, root, info, out_dict, mapping):

    path = info.name
    parent = info
    try:
        while True:
            _id = parent.id
            if _id in mapping:
                parent = mapping[_id]

            else:
                parent = get_one_parent(folders, root, parent)
                mapping[_id] = parent

            if parent == root:
                info.path = load_options("PATH") + "/" + path

                assert info.path not in out_dict  # * duplicated name

                out_dict[info.path] = info
                return info.parentID
            path = parent.name + "/" + path

    except AssertionError:
        exc_with_message(
            "A remote name is occupied by multiple files and folders: " +
            info.remote_path) + "\nThis error may occur by mistake when files are trashed very recently"


def init_one_fileinfo(args):
    return FileInfo("remote", **args)


@logtime
def process_remote(raw_files, root):
    """Converts google drive responses into FileInfo objects

    Returns a dictionary containings FileInfo with their paths as keys
    """

    folder_list = []
    file_list = []
    assert isinstance(root, str)

    for i in raw_files:
        file_info = init_one_fileinfo(i)
        if not file_info.isorphan:
            if file_info.isfolder:
                folder_list.append(file_info)
            else:
                file_list.append(file_info)
        else:
            # TODO handle orphan files, which are all sharedWithMe
            pass

    out_dict = {load_options("PATH"): root}
    mapping = {}
    for i in folder_list + file_list:
        get_one_path(folder_list, root, i, out_dict, mapping)

    return out_dict
