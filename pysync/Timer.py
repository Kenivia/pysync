import time
from functools import wraps


class FuncTimer():

    def __init__(self,  func_title, time_type):
        """Timer for one function
        """

        self.reset()
        self.usertime = None
        self.func_title = func_title
        self.time_type = time_type

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


class TimeLogger():
    def __init__(self, decimal=2):
        self.dp = decimal
        self.times = []

    def comp(self, func_title=None):
        self.times.append(FuncTimer(func_title, "comp"))
        return self

    def user(self, func_title=None):
        self.times.append(FuncTimer(func_title, "user"))
        return self

    def load(self, func_title=None):
        self.times.append(FuncTimer(func_title, "load"))
        return self

    def print_times(self):
        usersum, compsum, loadsum = 0, 0, 0
        label_str = "Stages"
        usr_str = "User inputs"
        comp_str = "Computations"
        load_str = "Uploads & downloads"
        total_str = "Total time"
        all_len = [len(i.func_title if i.func_title is not None else "")
                   for i in self.times]
        all_len.extend([len(i)
                        for i in [usr_str, comp_str, load_str, total_str, label_str]])
        max_len = max(all_len) + 3
        print()
        for i in self.times:
            if i.func_title is not None:
                print(i.func_title.ljust(max_len, " "),
                      round(i.duration, self.dp))
            if i.time_type == "user":
                usersum += i.duration
            elif i.time_type == "comp":
                compsum += i.duration
            elif i.time_type == "load":
                loadsum += i.duration

        total = usersum + compsum + loadsum
        print("-"*(max_len+12))
        print(label_str.ljust(max_len, " "), "Time taken")
        print(usr_str.ljust(max_len, " "), round(usersum, self.dp))
        print(comp_str.ljust(max_len, " "), round(compsum, self.dp))
        print(load_str.ljust(max_len, " "), round(loadsum, self.dp))
        print(total_str.ljust(max_len, " "), round(total, self.dp))


def logtime(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if "timer" in kwargs:
            timer = kwargs["timer"]
            del kwargs["timer"]
            timer.times[-1].start()

            result = func(*args, **kwargs)
            timer.times[-1].stop()
        else:
            result = func(*args, **kwargs)
        return result
    return wrap
