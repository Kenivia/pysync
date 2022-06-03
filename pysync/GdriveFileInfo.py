import os

import subprocess as sp
import dateutil.parser as dup

from googleapiclient.errors import HttpError
from pysync.Functions import check_acknowledgement

from pysync.OptionsParser import get_option
from pysync.FileInfo import FileInfo, FileIDNotFoundError


class GdriveFileInfo(FileInfo):

    """Object containing the metadata of either a remote google drive file"""

    def __init__(self, **kwargs):

        super().__init__()

        self._id = kwargs["id"]
        self._name = kwargs["name"]
        self.type = "folder" if kwargs["mimeType"] == "application/vnd.google-apps.folder" else "file"
        self.mtime = int(dup.parse(kwargs["modifiedTime"]).timestamp())
        if "parents" in kwargs:
            assert len(kwargs["parents"]) == 1
            self._parentID = kwargs["parents"][0]
        # TODO make a "shared" folder for orphans(because they're all shared files i think)

        if self.isfile:
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

        assert self.partner is None
        if self.isremotegdoc:
            assert self.link is not None

        if self.action_code == "del remote":
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

    def down_new(self, drive):

        if self.isfolder:
            os.mkdir(self.path)
        else:
            if not self.isremotegdoc:
                # TODO abuse? but otherwise works
                try:
                    response = drive.get_media(fileId=self.id).execute()
                except HttpError as e:
                    if not "cannotDownloadAbusiveFile" in repr(e):
                        raise e
                    if check_acknowledgement():
                        response = drive.get_media(fileId=self.id, acknowledgeAbuse=True).execute()
                        with open(self.path, "wb") as f:
                            f.write(response)
                        self.write_remote_mtime(drive)
                    else:
                        print("This file was not downloaded because it was marked as 'abuse':")
                        print(self.path)

            else:
                with open(self.path, "w") as exe_file:
                    exe_file.write(self.gen_localgdoc())
                    sp.run(["chmod", "+x", self.path])
                self.write_remote_mtime(drive)

    def gen_localgdoc(self):
        return f"""xdg-open {self.link}
    # This file was created by pysync. Do not remove the line below!
    {get_option("SIGNATURE")}"""

    def find_id(self):
        text = open(self.path, "r").read()
        for line in text.split("\n"):
            if line.startswith("xdg-open https://docs.google.com/"):
                split = text.split("/")
                for index, item in enumerate(split):
                    if item == "d":  # * the id is after a /d/ sequence
                        return split[index + 1]

        raise FileIDNotFoundError()

    def write_remote_mtime(self, drive):
        assert self.path is not None
        _file = drive.get(fileId=self.id, fields="modifiedTime",).execute()
        mtime = int(dup.parse(_file["modifiedTime"]).timestamp())
        os.utime(self.path, (mtime, mtime))

    @property
    def path(self):
        if self._path is not None:
            return self._path
        assert self.parent is not None
        parent_path = get_option("PATH") if isinstance(self.parent, str) else self.parent.path
        self._path = parent_path + "/" + self.name
        return self._path

    @property
    def md5sum(self):

        return self._md5sum

    @property
    def id(self):
        if self._id is not None:
            return self._id
        return None

    @property
    def islocal(self):
        return False

    @property
    def isremote(self):
        return True

    @property
    def isorphan(self):
        return self.parentID is None

    @property
    def name(self):
        return self._name

    def check_parent(self):
        return os.path.isdir(self.parent_path)

    @property
    def parentID(self):
        return self._parentID
