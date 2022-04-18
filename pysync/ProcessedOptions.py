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

ideally only __init__ should import from this, but it leads to long chains of args being passed down
"""


assert isinstance(CHECK_MD5, bool)
assert isinstance(MAX_COMPUTE_THREADS, int)
assert isinstance(MAX_PUSH_THREADS, int)
assert isinstance(ALWAYS_PUSH, list)
assert isinstance(ALWAYS_PULL, list)
assert isinstance(ALWAYS_IGNORE, list)
assert isinstance(PRINT_PROGRESS, bool)
assert EXE_SIGNATURE.startswith("#")

# * root as in the directory containing pysync, not the actual root
# * ends with no slah
ROOTPATH = PurePath(__file__).parent.parent

if MAX_PUSH_THREADS > 50:
    print("Warning! MAX_PUSH_THREADS was set to a value higher than 50. This may cause upload to fail")

MAX_COMPUTE_THREADS = psutil.cpu_count(
) if MAX_COMPUTE_THREADS <= 0 else MAX_COMPUTE_THREADS

# * slash removal is vital for a lot of the program
PATH = remove_slash(abs_path(PATH))
ALWAYS_PUSH = [remove_slash(abs_path(i)) for i in ALWAYS_PUSH]
ALWAYS_PULL = [remove_slash(abs_path(i)) for i in ALWAYS_PULL]
ALWAYS_IGNORE = [remove_slash(abs_path(i)) for i in ALWAYS_IGNORE]
# todo add a check to make sure that a file can't be in more than of them

assert os.path.isdir(PATH) # * makes sure PATH is there
assert_start(PATH, ALWAYS_PULL)
assert_start(PATH, ALWAYS_PUSH)

temp = copy.deepcopy(DEFAULT_PULL)
temp.extend(DEFAULT_PUSH)
assert len(temp) == 4
if len(DEFAULT_PUSH) + len(DEFAULT_PULL) + len(DEFAULT_IGNORE) != 4:
    raise AssertionError(
        "Options DEFAULT_PUSH, DEFAULT_PULL DEFAULT_IGNORE must contain exactly 4 items between them")

needed = ["local_new", "content_change", "mtime_change", "remote_new"]
for i in needed:
    if i not in temp:
        raise AssertionError("""Options DEFAULT_PUSH, DEFAULT_PULL and DEFAULT_IGNORE are not set correctly.
Each of the following must be included exactly once:
\t\"local_new\", \"content_change\", \"mtime_change\", \"remote_new\"""")

EMPTY_OUTPUT = {
    "local_new": [], "remote_new": [],  # ! names kinda confusing
    "content_change": [], "mtime_change": [], }
RECHECK_INTERVAL = 0.01

# PRIO_LOCAL_PUSH = ["local_del", "local_new", "both_new",
#                    "local_change", "remote_change", "mtime_change", "remote_del"]
# PRIO_REMOTE_PUSH = ["local_new"]
