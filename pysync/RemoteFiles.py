import os.path

from socket import timeout
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError, TransportError


from pysync.Timer import logtime
from pysync.Options_parser import load_options
from pysync.FileInfo import FileInfo
from pysync.Exit import exc_with_message


def process_creds(creds, scopes):
    if creds and creds.valid:
        return creds

    if creds and creds.refresh_token:  # * this was bugged from the tutorial..
        try:
            creds.refresh(Request())
            print("Old token refreshed successfully")
            return creds

        except RefreshError:
            print("Couldn't refresh old token")
            pass

        except TransportError:
            exc_with_message(
                "pysync couldn't refresh your token, please check your internet connectio")

    print("Requesting a new token")
    flow = InstalledAppFlow.from_client_secrets_file(
        load_options("ROOT") + "/data/client_secrets.json", scopes)
    creds = flow.run_local_server(port=0)
    return creds


@logtime
def init_drive():
    """Initializes the google drive and returns an UNPICKLABLE object"""

    creds = None
    scopes = ['https://www.googleapis.com/auth/drive']

    token_path = load_options("ROOT") + "/data/token.json"
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    creds = process_creds(creds, scopes)
    with open(token_path, 'w') as f:
        f.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    return service.files()


def kws_to_query(kws_list, equals, operator, exclude_list=[]):
    if equals:
        mimetype = ["mimeType = '" + i + "'" for i in kws_list if i not in exclude_list]
    else:
        mimetype = ["mimeType != '" + i + "'" for i in kws_list if i not in exclude_list]

    return f"({(' '+operator+' ').join(mimetype)}) and trashed = false and 'me' in owners"


@logtime
def list_remote(drive):
    """Lists remote files that are not in trash and are owned by me"""
    folder_kws = ["application/vnd.google-apps.folder"]
    gdoc_kws = [
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
    ], kws_to_query(folder_kws, True, "N/A")
    )
    gdoc_args = (drive, [
        'id',
        'name',
        'mimeType',
        'parents',
        'md5Checksum',
        'webViewLink',
        'modifiedTime',
    ], kws_to_query(gdoc_kws, True, "or")
    )

    file_args = (drive, [
        'id',
        'name',
        'mimeType',
        'parents',
        'md5Checksum',
        'modifiedTime',
    ], kws_to_query(gdoc_kws + folder_kws, False, "and")
    )
    all_args = []
    all_args.append(folder_args)
    all_args.append(gdoc_args)
    all_args.append(file_args)

    results = []
    for i in all_args:
        results.extend(list_drive_thread(i))

    root = drive.get(fileId="root",
                     fields="id").execute()
    results.append(root["id"])

    return results


def list_drive_thread(args):

    drive, fields, query = args[0], args[1], args[2]
    out = []

    page_token = None
    while True:
        try:
            response = drive.list(
                spaces="drive",
                q=query,
                pageSize=1000,
                # fields="*",
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
            info.remote_path)+ "\nThis also sometimes occurs when files are trashed very recently"


def init_one_fileinfo(args):
    return FileInfo("remote", **args)


@logtime
def process_remote(raw_files):
    """Lists the remote files and process them

    Returns a dictionary containings FileInfo with their paths as keys
    """

    folder_list = []
    file_list = []
    root = raw_files[-1]

    for i in raw_files[0:-1]:
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
