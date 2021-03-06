import time
from functools import wraps

from pysync.Functions import match_attr


def init_main_timer():
    stages = {"local": FuncTimer("comp", "Loading local files"),
              "init": FuncTimer("user", "Initializing drive"),
              "load_remote": FuncTimer("net", "Getting remote files"),
              "comp_remote": FuncTimer("comp", "Processing remote files"),
              "compare": FuncTimer("comp", "Comparing local and remote files"),
              "choose": FuncTimer("user", "Choosing which types to push & pull"),
              "apply": FuncTimer("net", "Applying changes"),
              }
    # * stages not neccessarily in order
    sequence = ["init", "load_remote", "comp_remote", "compare", "choose", "apply"]
    # * sequence is in order
    concurrent = {"local": (0, 3)}
    # * the key: the beginning and end indexes that it overlaps with
    # * "key" : (A, B) means the thread started just before A and joined before B starts
    # * when B == len(sequence), it means that it joined after the last task finished

    for i in concurrent:
        stages[i].isConcurrent = True

    return Timer(stages, sequence, concurrent, decimal_points=3)


class FuncTimer():
    def __init__(self, category, func_title):
        """Timer for one function
        """
        self.reset()
        self.usertime = None
        self.func_title = func_title
        self.category = category
        self.isConcurrent = False

    def reset(self):
        self.start_time = None
        self.duration = 0

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        if self.start_time is None:
            return self.duration

        self.duration += time.perf_counter() - self.start_time
        self.start_time = None
        return self.duration


class Timer():
    def __init__(self, stages, sequence, concurrent, decimal_points=2):
        self.dp = decimal_points
        self.sequence = sequence
        self.concurrent = concurrent
        self.stages = stages

    def time(self, event):
        return self.stages[event]

    @property
    def max_len(self):
        return max([len(i.func_title) if not i.isConcurrent else
                    len("  - started: " + i.func_title)
                    for i in self.stages.values()])

    def sum_time(self, category):
        sumtime = sum([i.duration for i in match_attr(self.stages.values(), category=category)
                       if not i.isConcurrent])
        for i in self.concurrent:
            if self.stages[i].category == category:
                main_time = sum([self.stages[i].duration for i in self.stages]
                                [self.concurrent[i][0]:self.concurrent[i][1] + 1])
                thread_time = self.stages[i].duration
                if thread_time > main_time:
                    sumtime += thread_time - main_time
        return sumtime

    def print_times(self):

        max_len = max(20, self.max_len)
        max_len += 5
        for index, event in enumerate(self.sequence):
            timer = self.stages[event]

            for key in self.concurrent:
                if index == self.concurrent[key][0]:
                    ctimer = self.stages[key]
                    print(("- started: " + ctimer.func_title).ljust(max_len),
                          round(ctimer.duration, self.dp))

                elif index == self.concurrent[key][1]:
                    ctimer = self.stages[key]
                    print(("- joined: " + ctimer.func_title).ljust(max_len),
                          round(ctimer.duration, self.dp))

            print(timer.func_title.ljust(max_len), round(timer.duration, self.dp))

        for key in self.concurrent:
            if len(self.sequence) == self.concurrent[key][1]:
                ctimer = self.stages[key]
                print(("  - joined: " + ctimer.func_title).ljust(max_len),
                      round(ctimer.duration, self.dp))

        usersum = self.sum_time("user")
        compsum = self.sum_time("comp")
        netsum = self.sum_time("net")
        label_str = "Categories"
        label_content = "Times taken"
        usr_str = "User input"
        comp_str = "Computations"
        net_str = "Uploads & downloads"
        total_str = "Total time"
        total = usersum + compsum + netsum
        print("\n" + "-" * (max_len + 20))
        print(label_str.ljust(max_len), label_content)
        print(usr_str.ljust(max_len), round(usersum, self.dp))
        print(comp_str.ljust(max_len), round(compsum, self.dp))
        print(net_str.ljust(max_len), round(netsum, self.dp))
        print(total_str.ljust(max_len), round(total, self.dp))


def logtime(func):
    @ wraps(func)
    def wrap(*args, **kwargs):
        if "timer" in kwargs:
            timer = kwargs["timer"]
            del kwargs["timer"]
            timer.start()
            result = func(*args, **kwargs)
            timer.stop()

        else:
            result = func(*args, **kwargs)
        return result
    return wrap
