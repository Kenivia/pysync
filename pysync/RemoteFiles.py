import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from send2trash import send2trash

from pysync.Timer import logtime
from pysync.ProcessedOptions import PATH, ROOTPATH
from pysync.FileInfo import FileInfo



def write_yaml():
    """This is probably unncessesary but might be useful just in case"""
    yamlpath = ROOTPATH.joinpath("settings.yaml")
    content = """client_config_backend: file
client_config_file: {0}/data/client_secrets.json


save_credentials: True
save_credentials_backend: file
save_credentials_file: {0}/data/saved_creds.json""".format(ROOTPATH)

    if os.path.isfile(yamlpath):
        send2trash(str(yamlpath))
    
    with open(yamlpath,"w") as f:
        f.write(content)

@logtime
def init_drive():
    """Initializes the google drive and returns an UNPICKLABLE object"""
    
    os.chdir(ROOTPATH)
    # * pydrive seems to only read settings.yaml if it's located at cwd
    write_yaml() # * optional
    
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)


@logtime
def list_remote(drive):
    """Lists remote files that are not in trash"""
    print("Listing remote files, this should take around 30 seconds")
    file_list = drive.ListFile({"q": "trashed=false"}).GetList()
    print(len(file_list), "files listed, processing..")
    out = []

    for i in file_list:
        _file = FileInfo("remote", **i)
        if not _file.isorphan:
            out.append(_file)
    
    return out


def find_children(info_list, parent_id):
    """Finds all children of a given folder id

    Ignores orphan files
    Returns the list of FileInfo and a dictionary representing the root folder
    """
    # todo integrate IGNORE lists here so the user don't have to see them
    out = []
    root = None
    for i in info_list:
        if i.isorphan:
            continue
        if parent_id == "root":
            if i.parent_isroot:
                root = i.parent  # * conveniently find the root
                out.append(i)
        else:
            if i.parent_id == parent_id:
                out.append(i)

    return out, root


def get_folder_dict(files):
    folder_dict = {"root": []}
    for i in files:
        if i.isfolder:
            folder_dict[i.id] = []

    root = None
    for i in files:
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
    """Assigns non-orphan files in info_list their respective paths recursively

    info_list - a list containing all the FileInfo objects
    file_id - the current file_id, `root` for the root folder
    path - the local base path
    modifies out_dict into a dictionary of FileInfo with their paths as keys


    returns: a dictionary representing the root folder
    """
    file_list = folder_dict[file_id]
    titles = []
    for i in file_list:
        i.get_path(path)
        if i.title in titles:
            print("A file and a folder share the same name in the remote folder at " +
                  i.remote_path +
                  ", please rename one of them.(Capitalization may help)")
            input("press enter to exit")
            raise AssertionError("Remote file & folder same name")
        titles.append(i.title)
        if i.ignore_me:
            continue
        # * modifies the out_dict value in process_remote cos it's a dict and its muatble
        modifying_dict[i.path] = i
        if i.isfolder:
            new_path = os.path.join(path, i.title)
            determine_paths(folder_dict, i.id, new_path, modifying_dict)


@logtime
def process_remote(files):
    """Lists the remote files and process them

    determines the local path of every file recursively 

    Returns a dictionary containing FileInfo with their paths as keys
    """

    old_len = len(files)

    root, folder_dict = get_folder_dict(files)
    out_dict = {PATH: root}
    determine_paths(folder_dict, "root", PATH, out_dict)
    print(old_len - len(list(out_dict)), "files were invalid or ignored")
    return out_dict
