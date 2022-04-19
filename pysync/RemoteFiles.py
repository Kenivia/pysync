import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from send2trash import send2trash

from pysync.Timer import logtime
from pysync.ProcessedOptions import PATH, ROOTPATH
from pysync.FileInfo import FileInfo


def write_yaml():
    """This is probably unncessesary but might be useful just in case"""
    yamlpath = ROOTPATH + "/settings.yaml"
    content = """client_config_backend: file
client_config_file: {0}/data/client_secrets.json


save_credentials: True
save_credentials_backend: file
save_credentials_file: {0}/data/saved_creds.json""".format(ROOTPATH)

    if os.path.isfile(yamlpath):
        send2trash(str(yamlpath))

    with open(yamlpath, "w") as f:
        f.write(content)


@logtime
def init_drive():
    """Initializes the google drive and returns an UNPICKLABLE object"""

    os.chdir(ROOTPATH)
    # * pydrive seems to only read settings.yaml if it's located at cwd
    write_yaml()  # * optional?

    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)


@logtime
def list_remote(drive):
    """Lists remote files that are not in trash"""
    print("Getting remote files..")
    file_list = drive.ListFile({"q": "trashed=false"}).GetList()
    file_list = [dict(i) for i in file_list]
    print(len(file_list), "files listed, processing..")
    return list(file_list)


def get_folder_dict(files):
    folder_dict = {"root": []}
    for i in files:
        if i.isfolder:
            folder_dict[i.id] = []

    root = None
    for i in files:
        print(i.title)
        for _id in folder_dict:
            if i.parent_isroot:
                root = i.parent
                folder_dict["root"].append(i)
                break
            elif i.parent_id == _id:
                folder_dict[_id].append(i)
                break
    return root, folder_dict


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
    seen_titles = []
    for i in file_list:
        i.get_path(path)
        if i.title in seen_titles:
            print("A file and a folder share the same name in the remote folder at " +
                  i.remote_path +
                  ", please rename one of them.(Capitalization may help)")
            input("press enter to exit")
            raise AssertionError("Remote file & folder same name")
        seen_titles.append(i.title)
        if i.ignore_me:
            continue
        # * modifies the out_dict value in process_remote cos it's a dict and its mutable
        modifying_dict[i.path] = i
        if i.isfolder:
            new_path = os.path.join(path, i.title)
            determine_paths(folder_dict, i.id, new_path, modifying_dict)


@logtime
def process_remote(raw_files):
    """Lists the remote files and process them

    determines the local path of every file recursively

    Returns a dictionary containing FileInfo with their paths as keys
    """

    info_list = []
    for i in raw_files:
        _file = FileInfo("remote", **i)
        if not _file.isorphan:
            info_list.append(_file)

    root, folder_dict = get_folder_dict(info_list)
    out_dict = {PATH: root}
    determine_paths(folder_dict, "root", PATH, out_dict)

    return out_dict
