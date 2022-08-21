from pysync.Timer import logtime


@logtime
def get_diff(local_data, remote_data):
    """Determines the difference between the two

    Args:
        local_data (dict): dict of LocalFileInfo objects from get_local_files
        remote_data (dict): dict of GdriveFileInfo objects from process_remote

    Returns:
        list: list of FileInfo objects that require change
        dict: union of local_data and remote data
    """

    diff_infos = []
    all_data = {}
    local = set(local_data.keys())
    remote = set(remote_data.keys())

    in_both = local & remote
    only_local = local - remote
    only_remote = remote - local
    
    for path in only_local:
        f = local_data[path]
        f.change_type = "local_new"

        diff_infos.append(f)
        all_data[path] = f
    
    for path in only_remote:
        f = remote_data[path]
        if isinstance(f, str): # * root
            continue
        f.change_type = "remote_new"

        diff_infos.append(f)
        all_data[path] = f
    
    for path in in_both:
        f = local_data[path]
        f.partner = remote_data[path]
        if f.compare_info():
            diff_infos.append(f)
        all_data[path] = f
    
    return diff_infos, all_data


def predict_action(processed_log, diff_infos):
    """
    The goal is to help establish whether to push or pull a file

    Note that this is not meant to find WHICH files need change, it helps to find WHAT to do
        i.e. FileModifiedEvent will not trigger a file to be pushed.
        

    pysync will work based on the assumption that having a watcher record is a luxury, and
    when pysync isn't sure, will avoid deleting files. When a file modification is ambiguous, 
    pysync will upload the local copy.


    Here is a list of possible outcomes

    remote new:
        - A local deletion was recorded(FileDeletedEvent, DirDeletedEvent) without a creation event
            - The remote modification time is before the deletion
            - so `del remote`

            - OR, the remote modification time is after the deletion
            - ambiguous, so use default(down new)

        - NO local file deletion was recorded
            - At the remote file's mtime, watcher was running
            - so `down new`

            - At the remote file's mtime, watcher was not running for one reason or another
            - ambiguous, so use default(down new)

    local new
        - A local file creation was recorded(FileCreatedEvent, DirCreatedEvent) without a deletion event
            - so `up new`

        - NO local file creation was recorded
            - at the local file's creation time, watcher was running
            - so `del local`

            - at the local file's creation time, watcher was not running
            - ambiguous, so use default(up new)


    mtime diff or content diff

    pysync will not use the content of the file to guess which one is newer

        - local mtime is higher
            - at least one local file modification was recorded(FileModifiedEvent)
            - so `up diff`
            
            - no local file modification was recorded
            - ambiguous, so use default(up new)

        - remote mtime is higher
            - no local file modification was recorded
            - so `down diff`
            
            - at least one local file modification was recorded(FileModifiedEvent)
            - ambiguous, so use default(up new)
        
        - local mtime and remote mtime are very close(1 sec?) but md5sum is different
            - ambiguous, so use default(up new)

    NOTE 
    FileMovedEvent and DirMovedEvent will be treated as a deletion and a creation
    The events must be after the last update completed


    """
    