from threading import Thread, active_count
import time
import traceback
import sys
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError, TransportError

from pysync.Functions import pysyncSilentExit, utc_to_local
from pysync.Timer import logtime
from pysync.Options_parser import load_options
from pysync.FileInfo import FileInfo
from pysync.Exit import on_exit


def process_creds(creds, scopes):
    if creds and creds.valid:
        return creds

    if creds and creds.refresh_token:  # * this was bugged from the tutorial..
        try:
            creds.refresh(Request())
            print("Old token refreshed")
            return creds
        except RefreshError:
            print("Couldn't refresh old token")
            pass
        except TransportError:
            traceback.print_exc(file=sys.stdout)
            print("\npysync couldn't refresh your token, please check your internet connection")
            on_exit(True)
            raise pysyncSilentExit

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

    # If there are no (valid) credentials available, let the user log in.

    creds = process_creds(creds, scopes)
    with open(token_path, 'w') as f:
        f.write(creds.to_json())

    print("The current token will expire at:", str(utc_to_local(creds.expiry)).split(".")[0])

    service = build('drive', 'v3', credentials=creds)
    return service.files()


def one_type_query(all_types, args, exclude_types=[]):

    out_args = []
    for i in all_types:
        if i not in exclude_types:
            out = (args[0], args[1], f"mimeType = \'{i}\' and trashed = false")
            out_args.append(out)
    return out_args


def kws_to_query(kws_list, equals, operator, exclude_list=[]):
    if equals:
        mimetype = ["mimeType = '" + i + "'" for i in kws_list if i not in exclude_list]
    else:
        mimetype = ["mimeType != '" + i + "'" for i in kws_list if i not in exclude_list]

    return f"{(' '+operator+' ').join(mimetype)} and trashed = false"


@logtime
def list_remote(drive):
    """Lists remote files that are not in trash"""
    all_args = []

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

    all_args.append(folder_args)
    all_args.append(gdoc_args)
    all_args.append(file_args)

    results = []
    for i in all_args:
        results.extend(list_drive_thread(i))

    # dump_test_pkl(results, "remote")
    return results


def list_drive_thread(args):

    drive, fields, query = args[0], args[1], args[2]
    out = []

    page_token = None
    while True:
        response = drive.list(
            spaces="drive",
            q=query,
            pageSize=1000,
            # fields="*",
            fields=f"nextPageToken, files({','.join(fields)})",
            pageToken=page_token,
        ).execute()

        page_token = response.get('nextPageToken', None)
        out.extend(response.get("files", []))
        if page_token is None:
            break
    return out


def get_folder_dict(files):

    folder_dict = {"root": []}
    for i in files:
        if i.isfolder:
            folder_dict[i.id] = []

    for i in files:
        found = False
        for _id in folder_dict:
            if i.parent == _id:
                folder_dict[_id]. append(i)
                found = True
                break
        if not found:
            folder_dict["root"].append(i)
    return folder_dict


def determine_paths(folder_dict, file_id, path, modifying_dict):
    """Put files into modifying_dict with its path as the key

    runs recursively

    Args:
        folder_dict (dict): dict with id of folders as key, list of dict(files) as value
        file_id (str): id of the file in question, "root" for the root folder
        path (str): the path to start at
        modifying_dict (dict): a dictionary to put the

    Raises:
        AssertionError: if a remote file and folder share the same name
    """

    file_list = folder_dict[file_id]
    seen_names = []
    for i in file_list:
        i.get_path(path)
        if i.name in seen_names:
            print("A file and a folder share the same name in the remote folder at " +
                  i.remote_path +
                  ", please rename one of them.(Capitalization may help)")
            input("press enter to exit")
            raise AssertionError("Remote file & folder same name")
        seen_names.append(i.name)
        if i.ignore_me:
            continue
        # * modifies the out_dict value in process_remote cos it's a dict and its mutable
        modifying_dict[i.path] = i
        if i.isfolder:
            new_path = os.path.join(path, i.name)
            determine_paths(folder_dict, i.id, new_path, modifying_dict)


def get_one_parent(folders, info):

    parent = "root"
    for i in folders:
        if info.parent == i.id:
            parent = i
            break
    return parent


def get_one_path(folders, info, out_dict, mapping):

    path = info.name
    parent = info

    while True:
        _id = parent.id
        if _id in mapping:
            parent = mapping[_id]
            access = True

        else:
            parent = get_one_parent(folders, parent)
            mapping[_id] = parent
            access = False

        if parent == "root":
            info.path = load_options("PATH") + "/" + path
            out_dict[info.path] = info
            return access

        path = parent.name + "/" + path


def init_one_fileinfo(args):
    return FileInfo("remote", **args)


@logtime
def process_remote(raw_files):
    """Lists the remote files and process them

    determines the local path of every file recursively

    Returns a dictionary containings FileInfo with their paths as keys
    """

    folder_list = []
    file_list = []
    for i in raw_files:
        file_info = init_one_fileinfo(i)
        if not file_info.isorphan:
            if file_info.isfolder:
                folder_list.append(file_info)
            else:
                file_list.append(file_info)

    out_dict = {load_options("PATH"): "root"}
    mapping = {}
    for i in folder_list + file_list:
        get_one_path(folder_list, i, out_dict, mapping)
    return out_dict
