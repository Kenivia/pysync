import time
from threading import (
    Thread,
    active_count,
)
from pysync.FileInfo import match_attr

from pysync.Timer import logtime
from pysync.ProcessedOptions import (
    MAX_PUSH_THREADS,
    RECHECK_INTERVAL,
    PRINT_PROGRESS,
)

from pysync.FileInfo import (
    OperationIgnored,
    OperationNotReady,
)


@logtime
def run_drive_ops(all_infos, path_dict, drive):
    """Run drive_op for each push/pull operation in many threads

    Will not exceed MAX_PUSH_THREADS at any given time
    After reaching the limit, the function attempts to start another thread every RECHECK_INTERVAL seconds

    prints information to the user as it progress
    """

    intial_thread_count = active_count()
    all_threads = []
    infos = match_attr(all_infos, action="push") + \
        match_attr(all_infos, action="pull")
    if infos:
        print("Applying {} changes..".format(str(len(infos))))
    else:
        print("No available changes")

    while infos:

        infos.sort(key=lambda x: (  # * folders first, then less depth first
            not x.isfolder, len(x.path.split("/"))), reverse=True)
        # * I go from the back cos i'm removing it 1 by 1, thats why its reversed
        # * sorta like a queue?
        index = len(infos)-1

        for _ in range(len(infos)):
            if active_count() - intial_thread_count >= MAX_PUSH_THREADS:
                time.sleep(RECHECK_INTERVAL)
                break

            item = infos[index]
            try:
                item.check_possible(path_dict)
                if PRINT_PROGRESS:
                    print(len(infos), item.action +
                          "ing", item.change_type,  item.path)
                t = Thread(target=item.drive_op, args=(path_dict, drive))
                t.start()
                all_threads.append(t)
                infos.remove(item)

            except OperationIgnored:
                infos.remove(item)
            except OperationNotReady:
                pass

            finally:
                index -= 1
            # * after each iteration, the leftovers are sorted and ran again
    [i.join() for i in all_threads]
    print("All done")
