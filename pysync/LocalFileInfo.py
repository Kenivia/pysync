import os
import hashlib as hl

from send2trash import send2trash
from datetime import datetime
from googleapiclient.http import MediaFileUpload

from pysync.BaseFileInfo import BaseFileInfo, FileIDNotFoundError
from pysync.Commons import local_to_utc
from pysync.OptionsParser import get_option


UP_CHUNK_SIZE = -1  # * -1 for uploading in one go, specifying a chunksized doesn't seem to work


def hex_md5_file(path):
    hash_md5 = hl.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class LocalFileInfo(BaseFileInfo):

    """Object containing the metadata of a local file"""

    def __init__(self, **kwargs):

        super().__init__()
        self._path = kwargs["path"]
        self.type = kwargs["type"]
        if self.isfile:
            if kwargs["check_md5"]:
                self.calculate_md5()
            else:
                self.mtime = round(self.get_raw_local_mtime())

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

        if self._md5sum is not None:
            if self.md5sum != self.partner.md5sum:
                self.change_type = "content_change"
                return self.change_type
        else:
            assert self.mtime is not None
            if (self.mtime - self.partner.mtime) >= 3:
                self.change_type = "mtime_change"
                return self.change_type

        return False

    def op_checks(self):
        """performs various checks before applying changes

        Raises:
            AssertionError: something went wrong
        """

        assert self.action is not None
        assert self.action == "pull" or self.action == "push"
        assert not self.op_attempted
        assert not self.op_success

        if self.partner is not None:
            assert not self.partner.islocal

        if self.action_code == "up new":
            self.assert_msg(os.path.exists(self.path),
                            msg="Tried to upload file, but it no longer exists locally")
            assert self.parentID is not None

        elif self.action_code == "del local":
            self.assert_msg(os.path.exists(self.path),
                            msg="Tried to delete file, but it no longer exists locally")

        elif self.action_code == "up diff" or self.action_code == "down diff":
            self.assert_msg(os.path.exists(self.path),
                            msg="Tried to update file, but it no longer exists locally")
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

        elif self.islocalgdoc:

            file_id = self.find_id()
            _file = drive.get(fileId=file_id,
                              fields="trashed, parents").execute()

            # if _file["trashed"]:
            body = {"trashed": False, }
            old_parent = _file["parents"][0]
            drive.update(
                body=body,
                fileId=file_id,
                addParents=self.parentID,
                removeParents=old_parent).execute()
            # ? Here, i think technically we dont even have to remove old parent? just add new ones?
            # ? But having more than one parent will cause issues with get_remove
            # ? Since currently we take the 1st parent
            # ? idk just sounds like a can of worms

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
        self.copy_remote_mtime(drive)

    def find_id(self):
        text = open(self.path, "r").read()
        for line in text.split("\n"):
            if line.startswith("xdg-open https://docs.google.com/"):
                split = text.split("/")
                for index, item in enumerate(split):
                    if item == "d":  # * the id is after a /d/ sequence
                        return split[index + 1]

        raise FileIDNotFoundError()

    def has_signature(self):
        if self.isfile and os.path.getsize(self.path) < 300:
            # * these files made by pysync are around 260 bytes
            try:
                with open(self.path, "r") as _file:
                    if get_option("SIGNATURE") in _file.read():
                        return True
            except UnicodeDecodeError:
                return False
        else:
            return False

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
            if self._id is not None:
                assert self._id == self.partner.id
            else:
                self._id = self.partner.id
        return self._id

    @property
    def islocalgdoc(self):
        if self._islocalgdoc is None:
            self._islocalgdoc = self.has_signature()
        return self._islocalgdoc

    def check_parent(self):
        if self.action_code == "up new":
            return self.parentID is not None
        return True

    @property
    def parentID(self):
        if self._parentID is not None:
            return self._parentID
        if self.partner is None:
            return None
        self._parentID = self.partner.parentID
        return self.partner.parentID

    def get_raw_local_mtime(self):
        assert self.path is not None
        return os.path.getmtime(self.path)

    def get_iso_mtime(self):
        assert self.path is not None
        mtime = self.get_raw_local_mtime()
        dt = datetime.fromtimestamp(mtime)
        return local_to_utc(dt).isoformat().replace("+00:00", "Z")

    @property
    def path(self):
        return self._path

    @property
    def islocal(self):
        return True

    @property
    def isremote(self):
        return False

    @property
    def name(self):
        return os.path.split(self.path)[1]
