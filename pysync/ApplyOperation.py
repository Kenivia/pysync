import concurrent.futures as cf
import os
from pysync.Exit import exc_with_message
from pysync.FileInfo import GDriveQuotaExceeded

from pysync.Functions import match_attr
from pysync.Timer import logtime
from pysync.Options_parser import load_options


def assign_parent(info, all_data):

    if info.parentID is None and info.parent_path in all_data:
        # * this doesn't consider whether or not `info` has parentID already but thats fine
        if isinstance(all_data[info.parent_path], str):
            info.parentID = all_data[info.parent_path]
        else:
            info.parentID = all_data[info.parent_path].id


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
    # * must be processpool, threadpool runs into memory issue with python
    with cf.ProcessPoolExecutor(max_workers=max_threads) as executor:
        while pending:
            pending.sort(key=lambda x: (  # * folders first, then less depth first, then alphabetitc
                not x.isfolder, len(x.path.split("/")), x.path), reverse=True)
            # * important to sort by depth first, contrary to other sorts for printing
            # * the items are removed, thats why its reversed
            # * sorta like a queue?

            index = len(pending) - 1
            for _ in range(len(pending)):

                if interrupt_key in all_data:
                    raise all_data[interrupt_key]

                info = pending[index]
                assign_parent(info, all_data)
                if info.action == "ignore":
                    pending.remove(info)
                    continue
                elif info.parentID is None or not os.path.isdir(info.parent_path):
                    continue

                future = executor.submit(info.drive_op, all_data[info.parent_path], drive)
                pending.remove(info)

                def add_all_data(fut):
                    exception = fut.exception()
                    if isinstance(exception, GDriveQuotaExceeded):
                        # * not very clean way to do this but works
                        all_data[interrupt_key] = exception
                        return

                    result = fut.result()
                    if isinstance(result, str):
                        del all_data[result]
                    else:
                        all_data[result.path] = result

                future.add_done_callback(add_all_data)
                index -= 1
            # * after each iteration, the leftovers are sorted and ran again

    if interrupt_key in all_data:
        final_straw = all_data[interrupt_key].args[0]
        after_paths = [i.path for i in pending]
        done_paths = [i for i in before_paths if i not in after_paths and
                      i != final_straw]
        done_text = "\n".join(sorted(done_paths, key=lambda x: (len(x.split("/")), x)))
        exc_with_message("The following files were done before running out of space on Google drive:\n" +
                         done_text + "\n\n" +
                         f"Goole drive quota exceeded, the {str(len(done_paths))} files above were done before running out of space"+
                         "\nYour drive ran out of space while trying to upload this file: " + final_straw
                         , exception=all_data[interrupt_key])
    print("All done")
