import os
import time
import traceback

import subprocess as sp
import dateutil.parser as dup
import concurrent.futures as cf


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
    local_to_utc,
    match_attr,
)
from pysync.OptionsParser import load_options
from pysync.Exit import exc_with_message
from pysync.Timer import logtime
from pysync.OptionsParser import load_options


class FileIDNotFoundError(Exception):
    pass


class GDriveQuotaExceeded(Exception):
    pass


class FileInfo():

    """Object containing the metadata of either a local or remote file"""

    def __init__(self, location, **kwargs):

        self._location = location

        self._action = None
        self._md5sum = None
        self._id = None

        self._parentID = None
        self.partner = None
        self.change_type = None

        self.link = None
        self.path = None

        self.forced = False
        self.index = None

        self._islocalgdoc = None
        self.isremotegdoc = False

        self.op_completed = False
        self.checked_good = False

        if self.islocal:
            self.path = kwargs["path"]
            self.type = kwargs["type"]  # ("folder" if os.path.isdir(self.path) else "file")
            if self.isfile:
                if kwargs["md5_now"]:
                    self.calculate_md5()
                self.mtime = int(os.stat(self.path).st_mtime)

        else:
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

    @property
    def md5sum(self):
        assert self.isfile
        if self.isremote:
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
    def isfile(self):
        return not self.isfolder

    @property
    def islocal(self):
        assert self._location == "local" or self._location == "remote"
        return self._location == "local"

    @property
    def isremote(self):
        return not self.islocal

    @property
    def isorphan(self):
        return self.parentID is None

    @property
    def parent_path(self):
        return os.path.split(self.path)[0]

    @property
    def name(self):
        return self._name if self.isremote else os.path.split(self.path)[1]

    @property
    def parentID(self):
        if self.partner is not None and self._parentID is None:
            self._parentID = self.partner.parentID
        return self._parentID

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
    def action(self):
        return self._action

    @property
    def action_code(self):
        return self.get_action_code(False)

    @property
    def action_human(self):
        return self.get_action_code(True)

    @property
    def islocalgdoc(self):
        if self._islocalgdoc is None:
            self._islocalgdoc = self.has_signature()
        return self._islocalgdoc

    def get_action_code(self, readable):

        assert self.change_type is not None
        assert self.action is not None

        if self.action == "ignore":
            out = "ignoring" if readable else "ignore"

        elif self.change_type == "local_new":
            if self.action == "push":
                out = "uploading new" if readable else "up new"
            elif self.action == "pull":
                if self.isfolder:
                    out = "deleting local folder and ALL its content" if readable else "del local"
                else:
                    out = "deleting local file" if readable else "del local"

        elif self.change_type == "remote_new":
            if self.action == "push":
                if self.isfolder:
                    out = "deleting remote folder and ALL its content" if readable else "del remote"
                else:
                    out = "deleting remote file" if readable else "del remote"
            elif self.action == "pull":
                out = "downloading new" if readable else "down new"

        elif self.change_type == "content_change" or self.change_type == "mtime_change":
            if self.action == "push":
                out = "uploading difference" if readable else "up diff"
            elif self.action == "pull":
                out = "donwloading difference" if readable else "down diff"
        else:
            raise ValueError(self.change_type + " and " + self.action + " is not valid")

        forced = "forced " if self.forced and readable else ""
        return forced + out

    def has_signature(self):

        if self.islocal and self.isfile:
            try:
                with open(self.path, "r") as _file:
                    if load_options("SIGNATURE") in _file.read():
                        return True
            except UnicodeDecodeError:
                return False
        else:
            return False

    def gen_localgdoc(self):
        return f"""xdg-open {self.link}
    # This file was created by pysync. Do not remove the line below!
    {load_options("SIGNATURE")}"""

    def find_id(self):
        text = open(self.path, "r").read()
        for line in text.split("\n"):
            if line.startswith("xdg-open https://docs.google.com/"):
                split = text.split("/")
                for index, item in enumerate(split):
                    if item == "d":  # * the id is after a /d/ sequence
                        return split[index + 1]

        raise FileIDNotFoundError()

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
        assert not self.op_completed
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
        self._parentID = parent_id

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
                    exe_file.write(self.gen_localgdoc())
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

                self.op_completed = True

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
                reason = traceback.format_exc()
                if isinstance(e, timeout):
                    message = "This file timed out"

                elif isinstance(e, ServerNotFoundError):
                    message = "Couldn't connect to server"

                elif isinstance(e, HttpError) or isinstance(e, ResumableUploadError):
                    if "userRateLimitExceeded" in repr(e):
                        message = "This file failed, rate of requests too high"
                    elif "storageQuotaExceeded" in repr(e):
                        raise GDriveQuotaExceeded(self.path)

                if message is not None:
                    print("\t" + message + retry_text(count, max_count) + self.path + "\n")
                    
                else:
                    print(
                        "\tThis file failed with the following error" + retry_text(count, max_count) + self.path +
                        "\n" + reason + "\n")
                time.sleep(0.5)

            finally:
                if max_count > 0 and count >= max_count:
                    raise RuntimeError("Max retry count exceeded")

    def assign_parent(self, all_data):

        if self.parentID is None and self.parent_path in all_data:
            if isinstance(all_data[self.parent_path], str):
                self._parentID = all_data[self.parent_path]
            else:
                self._parentID = all_data[self.parent_path].id


@logtime
def run_drive_ops(diff_infos, all_data, drive):
    """Run drive_op for each push/pull operation using many threads

    Will not exceed the `Max upload threads` option at any given time

    Applies the changes to folders first, then files with least depth

    Args:
        diff_infos (list): list generated by get_diff, containing FileInfo objects
        all_data (dict): dict from get_diff
        drive (googleapiclient.discovery.Resource): Resource object from service.files() in init_drive
    """

    pending = match_attr(diff_infos, action="push") + \
        match_attr(diff_infos, action="pull")
    before_paths = [i.path for i in pending]

    if pending:
        print(f"Applying {str(len(pending))} changes..")
        if load_options("PRINT_UPLOAD"):
            print("Not displaying the progress")
    else:
        print("No available changes")

    interrupt_key = "uniqueKey///"
    max_threads = load_options("MAX_UPLOAD")
    # * must be processpool, threadpool runs into memory issue
    with cf.ProcessPoolExecutor(max_workers=max_threads) as executor:
        while pending:
            pending.sort(key=lambda x: (  # * folders first, then less depth first, then alphabetitc
                not x.isfolder, len(x.path.split("/")), x.path), reverse=True)
            # * important to sort by depth first, not just .path, contrary to other sorts for printing
            # * the items are removed(from the back), thats why its reversed
            # * sorta like a queue?

            index = len(pending) - 1
            for _ in range(len(pending)):

                if interrupt_key in all_data:
                    raise all_data[interrupt_key]

                info = pending[index]
                info.assign_parent(all_data)

                if info.parentID is None or not os.path.isdir(info.parent_path):
                    continue

                future = executor.submit(info.drive_op, all_data[info.parent_path], drive)
                pending.remove(info)

                def add_all_data(fut):
                    exception = fut.exception()
                    if exception is not None:
                        all_data[interrupt_key] = exception
                    else:
                        result = fut.result()
                        if isinstance(result, str):
                            del all_data[result]
                        else:
                            all_data[result.path] = result

                future.add_done_callback(add_all_data)
                index -= 1
            # * after each iteration, the leftovers are sorted and ran again

    if interrupt_key in all_data:
        exception = all_data[interrupt_key]
        if isinstance(exception, GDriveQuotaExceeded):
            final_straw = exception.args[0]
            after_paths = [i.path for i in pending]
            done_paths = [i for i in before_paths
                          if i not in after_paths and i != final_straw]
            done_text = "\n".join(sorted(done_paths, key=lambda x: (len(x.split("/")), x)))
            exc_with_message("The following files were done before running out of space on Google drive:\n" +
                             done_text + "\n\n" +
                             f"Goole drive quota exceeded, the {str(len(done_paths))} files above were done before running out of space" +
                             "\nYour drive ran out of space while trying to upload this file: " + final_straw,
                             exception=exception)

        else:
            exc_with_message("The error above occured while applying a change",
                             exception=exception)
    print("All done")
