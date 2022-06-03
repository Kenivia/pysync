import os
from datetime import datetime
from send2trash import send2trash
from googleapiclient.http import MediaFileUpload
from pysync.FileInfo import FileInfo

from pysync.Functions import hex_md5_file, local_to_utc
from pysync.OptionsParser import get_option


UP_CHUNK_SIZE = 1024 ^ 2  # * -1 for uploading in one go


class LocalFileInfo(FileInfo):

    """Object containing the metadata of either a local file"""

    def __init__(self, **kwargs):

        super().__init__()
        self._path = kwargs["path"]
        self.type = kwargs["type"]
        if self.isfile:
            if kwargs["md5_now"]:
                self.calculate_md5()
            self.mtime = int(os.stat(self.path).st_mtime)

    def compare_info(self):
        """Checks if there are differences between self and self.partner

        mtime_change will only trigger if there is >3 sec difference
        md5sum won't be checked if mtime_change is already triggered

        Returns:
            bool/str: False, "content_change" or "mtime_change"
        """

        assert self.path == self.partner.path
        if self.partner.isremotegdoc:
            assert self.islocalgdoc
            return False

        if self.isfolder:
            return False

        if (self.mtime - self.partner.mtime) >= 3:
            self.change_type = "mtime_change"
            return self.change_type

        if get_option("CHECK_MD5"):
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

        """

        assert self.action is not None
        assert self.action == "pull" or self.action == "push"
        assert not self.op_completed
        if self.partner is not None:
            assert not self.partner.islocal

        if self.action_code == "up new":
            assert os.path.exists(self.path)
            assert self.parentID is not None

        elif self.action_code == "del local":
            assert os.path.exists(self.path)

        elif self.action_code == "up diff" or self.action_code == "down diff":
            assert os.path.exists(self.path)
            assert self.id is not None
        else:
            raise AssertionError("action_code was invalid(" + str(self.action_code), ")")

    def del_local(self, drive=None):

        send2trash(self.path)

    def up_new(self, drive):

        if self.isfolder:
            body = {"parents": [self.parentID],
                    "name": self.name,
                    "mimeType": 'application/vnd.google-apps.folder', }
            _file = drive.create(body=body, fields="id").execute()
            self._id = _file["id"]  # * for other op_checks & other drive_ops

        elif self.partner is not None and self.partner.isremotegdoc and self.islocalgdoc:

            file_id = self.find_id()
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
                    "\tThis file is a local gdoc file but was invalid: " +
                    self.path,
                )
        else:
            # * is an ordinary file
            body = {"parents": [self.parentID],
                    "name": self.name,
                    "modifiedTime": self.get_iso_mtime(), }
            media = MediaFileUpload(self.path, chunksize=UP_CHUNK_SIZE, resumable=True)
            drive.create(body=body,
                         media_body=media).execute()

    def up_diff(self, drive):
        # * can't be folder
        # * uploadType is automatically media/multipart, no need for resumable

        body = {"modifiedTime": self.get_iso_mtime()}
        media = MediaFileUpload(self.path, chunksize=UP_CHUNK_SIZE, resumable=True)
        drive.update(fileId=self.id,
                     body=body,
                     media_body=media).execute()

    def down_diff(self, drive):
        # * can't be folder
        response = drive.get_media(fileId=self.id).execute()
        with open(self.path, "wb") as f:
            f.write(response)
        self.write_remote_mtime(drive)

    def has_signature(self):
        if self.islocal and self.isfile:
            try:
                with open(self.path, "r") as _file:
                    if get_option("SIGNATURE") in _file.read():
                        return True
            except UnicodeDecodeError:
                return False
        else:
            return False

    def get_posix_mtime(self):
        assert self.path is not None
        return os.path.getmtime(self.path)

    def get_iso_mtime(self):
        assert self.path is not None
        mtime = self.get_posix_mtime()
        dt = datetime.fromtimestamp(mtime)
        return local_to_utc(dt).isoformat()

    @property
    def path(self):
        return self._path

    def calculate_md5(self):
        assert self._md5sum is None
        self._md5sum = hex_md5_file(self.path)

    @property
    def md5sum(self):
        assert self.isfile
        if self._md5sum is None:
            self.calculate_md5()
        return self._md5sum

    @property
    def id(self):
        if self.partner is not None:
            assert self._id == self.partner.id
        return self._id

    @property
    def isfile(self):
        return not self.isfolder

    @property
    def islocal(self):
        return True

    @property
    def isremote(self):
        return False

    @property
    def name(self):
        return os.path.split(self.path)[1]

    @property
    def islocalgdoc(self):
        if self._islocalgdoc is None:
            self._islocalgdoc = self.has_signature()
        return self._islocalgdoc

    def check_parent(self):
        return self.parentID is not None

    @property
    def parentID(self):
        if self._parentID is not None:
            return self._parentID
        if self.partner is None:
            return None
        self._parentID = self.partner.parentID
        return self.partner.parentID
