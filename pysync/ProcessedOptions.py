import copy
import psutil
import os
from pathlib import PurePath

from pysync.Functions import (
    remove_slash,
    abs_path,
    assert_start,
)
from pysync.Options import *


"""
This file processes options defined in Options 
also defines some constants that are not intended to be modified.

THIS IS THE ONLY FILE THAT CAN IMPORT DIRECTLY FROM Options.py
Other files should import from this file
"""


assert isinstance(CHECK_MD5, bool)
assert isinstance(MAX_COMPUTE_THREADS, int)
assert isinstance(MAX_PUSH_THREADS, int)
assert isinstance(ALWAYS_PUSH, list)
assert isinstance(ALWAYS_PULL, list)
assert isinstance(IGNORE, list)
assert isinstance(PRINT_PROGRESS, bool)
assert EXE_SIGNATURE.startswith("#")

# * root as in the directory containing pysync, not the actual root
ROOTPATH = PurePath(__file__).parent.parent

if MAX_PUSH_THREADS > 50:
    print("Warning! MAX_PUSH_THREADS was set to a value higher than 50. This may cause upload to fail")

MAX_COMPUTE_THREADS = psutil.cpu_count(
) if MAX_COMPUTE_THREADS <= 0 else MAX_COMPUTE_THREADS

# * slash removal is vital for a lot of the program
PATH = remove_slash(abs_path(PATH))
ALWAYS_PUSH = [remove_slash(abs_path(i)) for i in ALWAYS_PUSH]
ALWAYS_PULL = [remove_slash(abs_path(i)) for i in ALWAYS_PULL]
IGNORE = [remove_slash(abs_path(i)) for i in IGNORE]

assert os.path.isdir(PATH)
assert_start(PATH, ALWAYS_PULL)
assert_start(PATH, ALWAYS_PUSH)

temp = copy.deepcopy(DEFAULT_PULL)
temp.extend(DEFAULT_PUSH)
assert len(temp) == 4
if len(DEFAULT_PUSH) + len(DEFAULT_PULL) != 4:
    raise AssertionError(
        "Options DEFAULT_PUSH and DEFAULT_PULL must contain exactly 4 items between them")

needed = ["local_new", "content_change", "mtime_change", "remote_new"]
for i in needed:
    if i not in temp:
        raise AssertionError("""Options DEFAULT_PUSH and DEFAULT_PULL are not set correctly.
Each of the following must be included exactly once:
\t\"local_new\", \"content_change\", \"mtime_change\", \"remote_new\"""")

EMPTY_OUTPUT = {
    "local_new": [], "remote_new": [],  # ! names kinda confusing
    "content_change": [], "mtime_change": [], }
RECHECK_INTERVAL = 0.01

# PRIO_LOCAL_PUSH = ["local_del", "local_new", "both_new",
#                    "local_change", "remote_change", "mtime_change", "remote_del"]
# PRIO_REMOTE_PUSH = ["local_new"]
