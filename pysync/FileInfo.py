import os
import dateutil.parser as dup
from send2trash import send2trash
import time
import subprocess as sp


from pysync.Functions import (
    hex_md5_file,
    contains_parent,
)
from pysync.ProcessedOptions import (
    CHECK_MD5,
    EXE_SIGNATURE,
    ALWAYS_IGNORE,
    PATH,
)


class OperationNotReady(Exception):
    """Raised by check_ready"""
    pass


class OperationIgnored(Exception):
    """Raised by check_ready"""
    pass


class FileIDNotFoundError(Exception):
    pass


def gen_exe(url, signatures):
    text = f"""xdg-open {url}
#This file was created by pysync. Do not remove the line below!
{signatures}"""
    return text


def get_id_exe(text):
    for line in text.split("\n"):
        if line.startswith("xdg-open https://docs.google.com/"):
            split = text.split("/")
            for index, item in enumerate(split):
                if item == "d":  # * the id is after a /d/ sequence
                    return split[index + 1]
    raise FileIDNotFoundError()


class FileInfo():

    """Object containing the metadata of either a local or remote file"""

    def __init__(self, location, **kwargs):
        self.parent = None  # * checked by isorphan
        self.action = None  # * checked  by check_ready
        self.partner = None  # * checked by id and parent_id
        self.change_type = None  # * checked by check_ready
        self._md5sum = None  # * checked by md5sum
        self._id = None  # * checked by id
        self.link = None  # * checked by check_ready
        self.isremotegdoc = False  # * checked by check_ready
        self.path = None  # * checked by remote_path
        self.forced = False  # * used in UserPushPull
        self.index = None  # * used in UserPushPull

        self._location = location  # * whether local or remote
        self.operation_done = False  # * set by drive_op, checked by check_ready
        self.checked_good = False  # * set by check_ready, checked by drive_op

        if self.islocal:
            self.path = kwargs["path"]
            self.type = "folder" if os.path.isdir(self.path) else "file"
            if not self.isfolder:
                if kwargs["md5_now"]:
                    self.calculate_md5()
                self.mtime = int(os.stat(self.path).st_mtime)

        else:
            self._id = kwargs["id"]
            self._title = kwargs["title"]
            self.type = "folder" if kwargs["mimeType"] == "application/vnd.google-apps.folder" else "file"
            if kwargs["parents"]:
                assert len(kwargs["parents"]) == 1
                self.parent = kwargs["parents"][0]
                self.parent_isroot = self.parent["isRoot"]
            if not self.isfolder:
                self._md5sum = kwargs["md5Checksum"] if "md5Checksum" in kwargs else None
                self.mtime = int(dup.parse(kwargs["modifiedDate"]).timestamp())
                if "application/vnd.google-apps." in kwargs["mimeType"]:
                    self.isremotegdoc = True
                    self.link = kwargs["alternateLink"]

    def compare_info(self):
        """Checks if there are differences between self and self.partner

        mtime_change will only trigger if there is no md5sum change and >3 sec difference

        Returns:
            bool/str: False, "content_change" or "mtime_change"
        """

        assert self.islocal
        assert self.path == self.partner.path
        if self.islocalgdoc:
            # * modifying local gdoc will not make a difference
            # * local gdoc must have a corresponding remote gdoc file
            assert self.partner.isremotegdoc
            return False

        if self.isfolder:
            return False

        if CHECK_MD5:
            # assert self.md5sum is not None and self.partner.md5sum is not None
            content_diff = self.md5sum != self.partner.md5sum
            if content_diff:
                self.change_type = "content_change"
                return self.change_type

        if (self.mtime - self.partner.mtime) >= 3:
            self.change_type = "mtime_change"
            return self.change_type

        return False

    def check_ready(self, all_data):
        """performs various checks before applying

        Args:
            all_data (dict): FileInfo objects from  get_diff

        Raises:
            OperationIgnored: the action is "ignore
            OperationNotReady: a file's parent directory doesn't exist yet(remote or local)
            AssertionError: something went wrong
        """
        assert self.action is not None
        if self.action == "ignore":
            # * will not  set checked_good to True, running drive_op will fail
            raise OperationIgnored
        assert self.action == "pull" or self.action == "push"
        assert not self.operation_done
        if self.partner is not None:
            assert not self.partner.islocal
        if self.isremotegdoc:
            assert self.link is not None

        if self.change_type == "local_new":
            assert os.path.exists(self.path)
            if self.action == "push":
                if self.parent_path not in all_data:
                    raise OperationNotReady(
                        "remote folder " + self.parent_path + " doesn't exist yet")
                if isinstance(all_data[self.parent_path], dict):
                    parent_id = all_data[self.parent_path]["id"]
                else:
                    parent_id = all_data[self.parent_path].id
                if parent_id is None:
                    raise OperationNotReady(
                        "remote folder " + self.parent_path + " doesn't exist yet")

            elif self.action == "pull":
                pass

        elif self.change_type == "remote_new":
            assert self.id is not None
            assert not os.path.exists(self.path)
            if self.action == "push":
                pass
            elif self.action == "pull":
                if not os.path.isdir(self.parent_path):
                    raise OperationNotReady(
                        "local parent folder " + self.parent_path + " doesn't exist yet")

        elif self.change_type == "content_change" or self.change_type == "mtime_change":
            assert os.path.exists(self.path)
            assert self.id is not None
        else:
            raise AssertionError

        self.checked_good = True

    def drive_op(self, all_data, drive):
        """Applies the operation specified by self.change_type and self.action

        self.checked_possible must be ran before this
        
        There are several scenarios:
        change_type       action      outcome

        local_new       push        file uploaded to gdrive
        local_new       pull        local file deleted
        remote_new      push        deletes the remote file
        remote_new      pull        creates the folder/download the file
        content_change  push        upload the local file and overwrite the remote copy
        content_change  pull        download the remote file and overwrite the local copy
        mtime_change will yield the same behaviour as content_change
        
        for changes, 

        if a file/folder was deleted, it will delete its entry in all_data
        if a file is created/updated, it will add `self` to all_data with key `self.path`

        if a new remote file is a google document e.g. google sheets, google docs
        then an executable text file will be created in the local copy that opens the document in a browser

        the modification time of the local file will be set when the upload finishes
            - this is around 1 second later than what will Google will say, hence the 3 seconds leeway in compare_info

        Args:
            all_info (dict): FileInfo objects from  get_diff
            drive (pydrive2.drive.GoogleDrive): drive object from init_drive

        Raises:
            RuntimeError: drive_op has already ran for this file

        """
      
        assert self.checked_good
        if self.operation_done:
            raise RuntimeError("already done", self.path)

        deletion = False
        if self.change_type == "local_new":
            if self.action == "push":
                if isinstance(all_data[self.parent_path], dict):
                    parent_id = all_data[self.parent_path]["id"]
                else:
                    parent_id = all_data[self.parent_path].id
                self.parent = {"id": parent_id}
                args = {"parents": [{"id": self.parent_id}],
                        "title": os.path.split(self.path)[1],
                        }
                if self.isfolder:
                    args["mimeType"] = 'application/vnd.google-apps.folder'
                    _file = drive.CreateFile(args)
                    _file.Upload()
                    self._id = _file["id"]
                elif self.islocalgdoc:

                    args["id"] = get_id_exe(open(self.path, "r").read())
                    _file = drive.CreateFile(args)

                    _file.FetchMetadata(fields="labels")
                    if _file["labels"]["trashed"]:
                        print("was trashed", args["parents"])
                        _file.UnTrash()
                        _file.Upload()
                    _file["parents"] = [{"kind": "drive#parentReference",
                                         "id": args["parents"][0]["id"]}]
                    _file.Upload()

                else:
                    _file = drive.CreateFile(args)
                    _file.SetContentFile(self.path)
                    _file.Upload()
            elif self.action == "pull":
                send2trash(self.path)
                deletion = True

        elif self.change_type == "remote_new":

            if self.action == "push":
                # * doesn't matter if its folder or file
                _file = drive.CreateFile({"id": self.id, })
                _file.Trash()
                deletion = True
            elif self.action == "pull":
                if self.isfolder:
                    os.mkdir(self.path)
                else:
                    _file = drive.CreateFile({"id": self.id, })

                    if not self.isremotegdoc:
                        _file.GetContentFile(self.path, remove_bom=True)
                    else:
                        with open(self.path, "w") as exe_file:
                            exe_file.write(gen_exe(self.link, EXE_SIGNATURE))
                            sp.run(["chmod", "+x", self.path])
                    mtime = int(dup.parse(_file["modifiedDate"]).timestamp())
                    os.utime(self.path, (mtime, mtime))

        elif self.change_type == "content_change" or self.change_type == "mtime_change":
            # * can't be folder
            _file = drive.CreateFile({"id": self.id, })

            if self.action == "push":
                _file.SetContentFile(self.path)
            elif self.action == "pull":
                _file.GetContentFile(self.path, remove_bom=True)
            _file.Upload()
            finish_time = time.time()
            os.utime(self.path, (finish_time, finish_time))
            

        self.operation_done = True
        if deletion:
            del all_data[self.path]
        else:
            all_data[self.path] = self

    @property
    def md5sum(self):
        assert not self.isfolder
        if not self.islocal:
            return self._md5sum
        if self._md5sum is None:
            self.calculate_md5()
        return self._md5sum

    @property
    def id(self):
        if self._id is not None:
            return self._id
        if self.partner is not None:
            return self.partner.id
        return None

    @property
    def isfolder(self):
        assert self.type == "folder" or self.type == "file"
        return self.type == "folder"

    @property
    def islocal(self):
        assert self._location == "local" or self._location == "remote"
        return self._location == "local"

    @property
    def isorphan(self):
        return self.parent is None

    @property
    def parent_path(self):
        return os.path.split(self.path)[0]

    @property
    def title(self):
        return self._title if not self.islocal else os.path.split(self.path)[1]

    @property
    def parent_id(self):
        if self.partner is not None and self.parent is None:
            self.parent = self.partner.parent
        return self.parent["id"]

    @property
    def islocalgdoc(self):
        if self.islocal and not self.isfolder:
            try:
                with open(self.path, "r") as _file:
                    if EXE_SIGNATURE in _file.read():
                        return True
            except UnicodeDecodeError:
                return False
        else:
            return False

    @property
    def ignore_me(self):
        return contains_parent(ALWAYS_IGNORE, self.path)

    def get_path(self, path):
        assert self._location == "remote"
        self.path = os.path.join(path, self.title)

    def calculate_md5(self):
        assert self._md5sum is None and self.islocal
        self._md5sum = hex_md5_file(self.path)

    @property
    def remote_path(self):
        """returns its path as it would appear in gdrive(without PATH in front of it)"""
        assert self.path is not None
        assert self.path.startswith(PATH)
        return self.path[len(PATH):]

    @property
    def action_human(self):
        out = "Forced " if self.forced else ""
        if self.action == "ignore":
            return out + "ignoring"

        if self.change_type == "local_new":
            if self.action == "push":
                return out + "uploading new"
            elif self.action == "pull":
                return out + "deleting local file"

        elif self.change_type == "remote_new":
            if self.action == "push":
                return out + "deleting remote file"
            elif self.action == "pull":
                return out + "downloading new"

        elif self.change_type == "content_change" or self.change_type == "mtime_change":
            if self.action == "push":
                return out + "uploading difference"
            elif self.action == "pull":
                return out + "downloading difference"
