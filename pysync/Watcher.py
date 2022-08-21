
import os
import time

from threading import RLock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirModifiedEvent, FileClosedEvent

LOG_PATH = "/home/kenivia/gdrive/Python/Projects/pysync/data/Internal/test"

ALIVE_TAG = "Alive//"

# TODO run this with nice 19


def get_alive_text():
    return "\n" + str(round(time.time())) + "/" + ALIVE_TAG


class OneLine:
    """Practically a mini LocalFileInfo"""

    def __init__(self, text, line_num):
        self.text = text
        self.line_num = line_num
        self._mtime = None
        self._path = None
        self._type = None
        self._change = None

    @property
    def mtime(self):
        if self._mtime is None:
            self._mtime = int(self.text[0:10])
        return self._mtime

    @property
    def path(self):
        if self._path is None:
            self._path = self.text[self.text.find("/"):]
        return self._path

    @property
    def type(self):
        if self._type is None:
            self._type = self.text[10]
        return self._type

    @property
    def change(self):
        if self._change is None:
            self._change = self.text[11]
        return self._change


class Watcher:

    def __init__(self, drive_path, log_path):
        self.observer = Observer()
        self.handler = MyHandler(log_path, drive_path)
        self.drive_path = drive_path
        self.log_path = log_path

        with open(self.log_path, "a") as f:
            f.writelines(["pysync watcher log file started", get_alive_text()])

    def run(self):
        self.observer.schedule(self.handler, self.drive_path, recursive=True)
        self.observer.start()
        print("\nWatcher Running in {}/\n".format(self.drive_path))
        try:
            while True:
                time.sleep(1)
                with open(self.log_path, "a") as f:
                    f.writelines([get_alive_text()])
                    self.handler.trigger_cleanup(len(get_alive_text()))
        
        except Exception as e:
            self.observer.stop()
            raise e
        self.observer.join()
        print("\nWatcher Terminated\n")


class MyHandler(FileSystemEventHandler):

    def __init__(self, log_path, drive_path):
        super().__init__()
        self.log_path = log_path
        self.drive_path = drive_path
        self.lastsize = 0
        self.nowsize = 0

        self.size_increment_trigger = 1024 * 1
        self.lock = RLock()

    def get_size(self):
        return os.path.getsize(self.log_path)

    def write(self, inp):
        if not isinstance(inp, list):
            inp = [inp]
        with open(self.log_path, "a") as f:
            f.writelines(inp)

    def one_log(self, event, etype, inpath=None):
        with self.lock:
            path = event.src_path if inpath is None else inpath
            if path == LOG_PATH:
                return
            path = path[len(self.drive_path):]
            mtime = str(round(time.time()))
            ftype = "D" if event.is_directory else "F"

            string = "\n" + mtime + ftype + etype + path
            
            self.write(string)
            self.trigger_cleanup(len(string))
            
    def trigger_cleanup(self, length):
        self.nowsize += length
        if self.nowsize - self.lastsize >= self.size_increment_trigger:
            self.cleanup()
            
    def cleanup(self):
        # * 10 is file type (D or F)
        # * 11 is change type (C, D or M)
        # * 0:10 is mtime
        # * 12: is path

        with open(LOG_PATH, "r") as f:
            text = f.read()
        text = text.split("\n")
        starting_line = text[0]
        first_alive = text[1]
        text = text[2:]
        
        out = [first_alive]
        last_alive = first_alive  # * just in case there isn't any alive pings
        for line in reversed(text):
            if line.endswith(ALIVE_TAG):
                last_alive = line
                break
        out.append(last_alive)
        
        path_dict = {}
        for line in text:
            path = line[12:]
            if path not in path_dict:
                path_dict[path] = [line]
            else:
                path_dict[path].append(line)

        for path in path_dict:
            # * Don't need to worry about changing the order because they have timestamps
            temp = []
            all_lines = path_dict[path]
            for line in reversed(all_lines):
                if line[11] == "M": # * only take the last mod
                    temp.append(line)
                    break

            CD_list = []
            last_line = None
            for line in all_lines:
                if line[11] == "C" or line[11] == "D":
                    CD_list.append(line[11])
                    last_line = line

            # * let's assume that it's alternating like C D C D C
            if len(CD_list) % 2 == 1: # * only do something if it's odd
                temp.append(last_line)

            out.extend(temp)
        out.sort()
        out.insert(0, starting_line)
        with open(self.log_path, "w") as f:
            f.write("\n".join(out))
            print("sorted")
            
        self.nowsize = os.path.getsize(self.log_path)
        self.lastsize = self.nowsize

    def on_created(self, event):
        if os.path.exists(event.src_path):
            self.one_log(event, "C")  # * C for create

    def on_deleted(self, event):
        if not os.path.exists(event.src_path):
            self.one_log(event, "D")  # * D for delete

    def on_modified(self, event):
        if event.is_directory:
            return
        self.one_log(event, "M")  # * M for modify

    def on_moved(self, event):
        self.one_log(event, "D", inpath=event.src_path)
        self.one_log(event, "C", inpath=event.dest_path)


if __name__ == "__main__":
    w = Watcher("/home/kenivia/gdrive", LOG_PATH)
    w.run()