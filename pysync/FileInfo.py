import os
import time
import subprocess as sp
import dateutil.parser as dup


from datetime import datetime
from send2trash import send2trash
from socket import timeout
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import (
    HttpError,
    ResumableUploadError,
    )
from httplib2 import ServerNotFoundError

from pysync.Functions import (
    hex_md5_file,
    contains_parent,
    local_to_utc,
)
from pysync.Options_parser import load_options


class FileIDNotFoundError(Exception):
    pass


class GDriveQuotaExceeded(Exception):
    pass


def gen_exe(url, signatures):
    text = f"""xdg-open {url}
# This file was created by pysync. Do not remove the line below!
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
        self.parentID = None  # * checked by isorphan
        self.action = None  # * checked  by op_checks
        self.partner = None  # * checked by id and parent_id
        self.change_type = None  # * checked by op_checks
        self._md5sum = None  # * checked by md5sum
        self._id = None  # * checked by id
        self.link = None  # * checked by op_checks
        self.isremotegdoc = False  # * checked by op_checks
        self.path = None  # * checked by remote_path
        self.forced = False  # * used in UserPushPull
        self.index = None  # * used in UserPushPull
        self.islocal_gdoc = False  # * used in compare_info

        self._location = location  # * whether local or remote
        self.op_already_done = False  # * set by drive_op, checked by op_checks
        self.checked_good = False  # * set by op_checks, checked by drive_op

        if self.islocal:
            self.path = kwargs["path"]
            self.type = "folder" if os.path.isdir(self.path) else "file"
            if not self.isfolder:
                if kwargs["md5_now"]:
                    self.calculate_md5()
                self.mtime = int(os.stat(self.path).st_mtime)
            self.islocal_gdoc = self.signature_present()

        else:
            self._id = kwargs["id"]
            self._name = kwargs["name"]
            self.type = "folder" if kwargs["mimeType"] == "application/vnd.google-apps.folder" else "file"
            self.mtime = int(dup.parse(kwargs["modifiedTime"]).timestamp())
            if "parents" in kwargs:
                assert len(kwargs["parents"]) == 1
                self.parentID = kwargs["parents"][0]
            # TODO make a "shared" folder for orphans(because they're all shared files i think)

            if not self.isfolder:
                self._md5sum = kwargs["md5Checksum"] if "md5Checksum" in kwargs else None
                if "application/vnd.google-apps." in kwargs["mimeType"]:
                    self.isremotegdoc = True
                    self.link = kwargs["webViewLink"]

    def compare_info(self):
        """Checks if there are differences between self and self.partner

        mtime_change will only trigger if there is >3 sec difference
        md5sum won't be checked if mtime_change is already triggered

        Returns:
            bool/str: False, "content_change" or "mtime_change"
        """

        assert self.islocal
        assert self.path == self.partner.path
        if self.islocal_gdoc:
            # * modifying local gdoc will not make a difference
            # * local gdoc must have a corresponding remote gdoc file
            assert self.partner.isremotegdoc
            return False

        if self.isfolder:
            return False

        if (self.mtime - self.partner.mtime) >= 3:
            self.change_type = "mtime_change"
            return self.change_type

        if load_options("CHECK_MD5"):
            # assert self.md5sum is not None and self.partner.md5sum is not None
            if self.md5sum != self.partner.md5sum:
                self.change_type = "content_change"
                return self.change_type

        return False

    def op_checks(self):
        """performs various checks before applying

        Args:
            all_data (dict): FileInfo objects from get_diff

        Raises:
            AssertionError: something went wrong

        Returns:
            str: "not_ready", "ignored" or "ready"
        """

        assert self.action is not None
        assert self.action == "pull" or self.action == "push"
        assert not self.op_already_done
        if self.partner is not None:
            assert not self.partner.islocal
        if self.isremotegdoc:
            assert self.link is not None

        if self.action_code == "up new":
            assert os.path.exists(self.path)
            assert self.parentID is not None

        elif self.action_code == "del local":
            assert os.path.exists(self.path)

        elif self.action_code == "del remote":
            assert self.id is not None
            assert not os.path.exists(self.path)

        elif self.action_code == "down new":
            assert self.id is not None
            assert not os.path.exists(self.path)
            assert os.path.isdir(self.parent_path)

        elif self.action_code == "up diff" or self.action_code == "down diff":
            assert os.path.exists(self.path)
            assert self.id is not None
        else:
            raise AssertionError("action_code was invalid(" + str(self.action_code), ")")

    def del_remote(self, drive):
        # * doesn't matter if its folder or file
        drive.update(body={"trashed": True},
                     fileId=self.id).execute()

    def del_local(self):
        send2trash(self.path)

    def up_new(self, parent, drive):

        if isinstance(parent, str):
            # * this is for when new folders are created so parentID might be empty
            # * root
            parent_id = parent
        else:
            parent_id = parent.id
        self.parentID = parent_id

        if self.isfolder:
            body = {"parents": [self.parentID],
                    "name": self.name,
                    "mimeType": 'application/vnd.google-apps.folder', }
            _file = drive.create(body=body, fields="id").execute()
            self._id = _file["id"]  # * for other op_checks & other drive_ops

        elif self.islocal_gdoc:

            file_id = get_id_exe(open(self.path, "r").read())
            _file = drive.get(fileId=file_id,
                              fields="trashed, parents").execute()

            if _file["trashed"]:
                print(self.path, "is untrashed")
                body = {"trashed": False, }
                old_parent = _file["parents"][0]
                drive.update(
                    body=body,
                    fileId=file_id,
                    addParents=self.parentID,
                    removeParents=old_parent).execute()
            else:
                print(
                    "\tThis local pysync gdoc file was invalid: " +
                    self.path,
                )
        else:
            # * is an ordinary file
            body = {"parents": [self.parentID],
                    "name": self.name,
                    "modifiedTime": self.get_formatted_mtime(), }
            media = MediaFileUpload(self.path, chunksize=-1, resumable=True)
            drive.create(body=body,
                         media_body=media).execute()

    def down_new(self, drive):

        if self.isfolder:
            os.mkdir(self.path)
        else:
            if not self.isremotegdoc:
                # TODO abuse? but otherwise works
                response = drive.get_media(fileId=self.id,  # acknowledgeAbuse=True
                                           ).execute()
                with open(self.path, "wb") as f:
                    f.write(response)
                self.write_remote_mtime(drive)
            else:
                with open(self.path, "w") as exe_file:
                    exe_file.write(gen_exe(self.link, load_options("SIGNATURE")))
                    sp.run(["chmod", "+x", self.path])
                self.write_remote_mtime(drive)

    def up_diff(self, drive):
        # * can't be folder
        # * uploadType is automatically media/multipart, no need for resumable

        body = {"modifiedTime": self.get_formatted_mtime()}
        media = MediaFileUpload(self.path, chunksize=-1, resumable=True)
        drive.update(fileId=self.id,
                     body=body,
                     media_body=media).execute()

    def down_diff(self, drive):
        # * can't be folder
        response = drive.get_media(fileId=self.id).execute()
        with open(self.path, "wb") as f:
            f.write(response)
        self.write_remote_mtime(drive)

    def drive_op(self, parent, drive):
        """Applies the operation specified by self.change_type and self.action

        self.op_checks must be ran before this

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
            - this is around 1 second later than what Google will say, hence the 3 seconds leeway in compare_info

        Args:
            parent (str/pysync.FileInfo.FileInfo): the parent FileInfo or id of root folder
            drive (googleapiclient.discovery.Resource): Resource object from service.files() in init_drive

        Raises:
            RuntimeError: max retry count has been exceeded

        """
        self.op_checks()

        deletion = False
        count = 0
        max_count = load_options("MAX_RETRY")
        while True:
            try:
                if self.action_code == "del remote":
                    self.del_remote(drive)
                    deletion = True

                elif self.action_code == "del local":
                    self.del_local()
                    deletion = True

                elif self.action_code == "up new":
                    self.up_new(parent, drive)

                elif self.action_code == "down new":
                    self.down_new(drive)

                elif self.action_code == "up diff":
                    self.up_diff(drive)

                elif self.action_code == "down diff":
                    self.down_diff(drive)

                if count > 0:
                    print(f"Retry #" + str(count) + " was successful: " + self.path)

                self.op_already_done = True

                if deletion:
                    return self.path
                else:
                    return self

            except Exception as e:
                def retry_text(_count, _max_count):
                    if _max_count > 0 and _count >= _max_count:
                        return ", " + f"tried {_max_count} times, giving up" + ": "
                    else:
                        return ", " + f"retrying({_count}/{_max_count})" + ": "

                count += 1
                message = None
                reason = repr(e)
                if isinstance(e, timeout):
                    message = "This file timed out"

                elif isinstance(e, ServerNotFoundError):
                    message = "Couldn't connect to server"

                elif isinstance(e, HttpError) or isinstance(e,ResumableUploadError):
                    if "userRateLimitExceeded" in repr(e):
                        message = "This file failed, rate of requests too high"
                    elif "storageQuotaExceeded" in repr(e):
                        raise GDriveQuotaExceeded(self.path)

                if message is not None:
                    print("\t" + message + retry_text(count, max_count) + self.path + "\n")
                else:
                    print(
                        "\tThis file failed with the following error" + retry_text(count, max_count) + self.path +
                        "\n\t\t" + reason + "\n")
                time.sleep(0.5)

            finally:
                if max_count > 0 and count >= max_count:
                    raise RuntimeError("Max retry count exceeded")

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
        return self.parentID is None

    @property
    def parent_path(self):
        return os.path.split(self.path)[0]

    @property
    def name(self):
        return self._name if not self.islocal else os.path.split(self.path)[1]

    @property
    def parent_id(self):

        if self.partner is not None and self.parentID is None:
            self.parentID = self.partner.parentID
        return self.parentID

    def signature_present(self):

        if self.islocal and not self.isfolder:
            try:
                with open(self.path, "r") as _file:
                    if load_options("SIGNATURE") in _file.read():
                        return True
            except UnicodeDecodeError:
                return False
        else:
            return False

    @property
    def ignore_me(self):
        return contains_parent(load_options("AIGNORE"), self.path)

    def get_path(self, path):
        assert self._location == "remote"
        self.path = os.path.join(path, self.name)

    def calculate_md5(self):
        assert self._md5sum is None and self.islocal
        self._md5sum = hex_md5_file(self.path)

    @property
    def remote_path(self):
        """returns its path as it would appear in gdrive(without PATH in front of it)"""
        local_path = load_options("PATH")
        assert self.path is not None
        assert self.path.startswith(local_path)
        return self.path[len(local_path):]

    @property
    def action_human(self):

        out = "forced " if self.forced else ""
        if self.action == "ignore":
            return out + "ignoring"

        if self.change_type == "local_new":
            if self.action == "push":
                return out + "uploading new"

            elif self.action == "pull":
                if self.isfolder:
                    return out + "deleting local folder and ALL its content"
                else:
                    return out + "deleting local file"

        elif self.change_type == "remote_new":
            if self.action == "push":
                if self.isfolder:
                    return out + "deleting remote folder and ALL its content"
                else:
                    return out + "deleting remote file"

            elif self.action == "pull":
                return out + "downloading new"

        elif self.change_type == "content_change" or self.change_type == "mtime_change":
            if self.action == "push":
                return out + "uploading difference"

            elif self.action == "pull":
                return out + "downloading difference"

    @property
    def action_code(self):

        if self.action == "ignore":
            return "ignore"

        if self.change_type == "local_new":
            if self.action == "push":
                return "up new"
            elif self.action == "pull":
                return "del local"

        elif self.change_type == "remote_new":
            if self.action == "push":
                return "del remote"
            elif self.action == "pull":
                return "down new"

        elif self.change_type == "content_change" or self.change_type == "mtime_change":
            if self.action == "push":
                return "up diff"
            elif self.action == "pull":
                return "down diff"

        raise ValueError

    def __hash__(self):

        out = {}
        for key in self.__dict__:
            if key == "partner":
                out[key] = self.partner.id
            item = self.__dict__[key]
            if isinstance(item, dict):
                out[key] = frozenset(item)
            elif isinstance(item, list):
                out[key] = tuple(item)
            else:
                out[key] = item

        return hash(frozenset(out))

    def get_posix_mtime(self):

        assert self.path is not None
        return os.path.getmtime(self.path)

    def get_formatted_mtime(self):

        assert self.path is not None
        mtime = self.get_posix_mtime()
        dt = datetime.fromtimestamp(mtime)
        return local_to_utc(dt).isoformat()

    def write_remote_mtime(self, drive):

        assert self.path is not None
        _file = drive.get(fileId=self.id, fields="modifiedTime",).execute()
        mtime = int(dup.parse(_file["modifiedTime"]).timestamp())
        os.utime(self.path, (mtime, mtime))
