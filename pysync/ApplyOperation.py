import time
from threading import (
    Thread,
    active_count,
)
from pysync.Timer import logtime
from pysync.ProcessedOptions import (
    MAX_PUSH_THREADS,
    ALWAYS_IGNORE,
    ALWAYS_PULL,
    ALWAYS_PUSH,
    RECHECK_INTERVAL,
    PRINT_PROGRESS,
)
from pysync.Functions import (
    contains_parent,
    flatten_dict
)
from pysync.FileInfo import OperationNotReadyError




@logtime
def run_drive_ops(info_list, path_dict, drive):
    """Run drive_op for each item in info_list in threads

    Will not exceed MAX_PUSH_THREADS at any given time
    After reaching the limit, the function attempts to start another thread every RECHECK_INTERVAL seconds

    prints information to the user as it progress
    """

    intial_thread_count = active_count()
    all_threads = []

    while info_list:
        info_list.sort(key=lambda x: (  # * folders first, then less depth first
            not x.isfolder, len(x.path.split("/"))), reverse=True)
        index = len(info_list)-1 
        for _ in range(len(info_list)):
            if active_count() - intial_thread_count >= MAX_PUSH_THREADS:
                time.sleep(RECHECK_INTERVAL)
                break
            item = info_list[index]
            try:
                item.check_possible(path_dict)
                if PRINT_PROGRESS:
                    print(len(info_list), item.action + "ing", item.change_type,  item.path)
                t = Thread(target=item.drive_op, args=(path_dict, drive))
                t.start()
                all_threads.append(t)
                info_list.remove(item)

            except OperationNotReadyError:
                pass

            index -= 1
    print("Waiting for threads to finish")
    [i.join() for i in all_threads]
