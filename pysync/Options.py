
"""
This file defines constants that changes some behaviours of the program

"""

# * NO FILES SHOULD IMPORT DIRECTLY FROM THIS FILE OTHER THAN ProcessedOptions.py
# * Necessary checks and transformations are performed to the variables

# * path to the local copy of the gdrive
PATH = "~/gdrive"

ASK_BEFORE_EXIT = True
# * whether or not to hold the process open until a confirmation

HIDE_FORCED_IGNORE = True
# * whether or not to display the ignored files in ALWAYS_IGNORE

# * paths to always push
ALWAYS_PUSH = []
# * paths to always pull
ALWAYS_PULL = ["~/gdrive/Saved", "~/gdrive/Colab Notebooks"]
# * paths to ignore, applies to both pushing and pulling
ALWAYS_IGNORE = ["~/gdrive/.gd"]


# * whether or not to print whenever a thread is started
PRINT_PROGRESS = False

# * if True(recommended), content of the files will be compared(slower)
# * otherwise only the modification time will be compared.
CHECK_MD5 = True

# * max number of files pushed simultanously, limited by google api limits
# * recommend a maximum of 50, increasing beyond 50 may cause google to reject requests
MAX_PUSH_THREADS = 50

# * max number of md5sum being computed simultanously
# * a value of less than 1 will default to the number of cpu cores available
MAX_COMPUTE_THREADS = 0

# * the categories to push, pull or ignore at first
# * this is just what category pysync displays before asking you
# * must include all of the following once:
# * "local_new", "content_change", "mtime_change", "remote_new"
DEFAULT_PUSH = ["local_new", "content_change", "mtime_change", ]
DEFAULT_PULL = ["remote_new"]
DEFAULT_IGNORE = []

# todo take care of cases where the signature is changed
# todo maybe run a function to change it?
# * the signature is designed to be present only in the local gdoc files so that pysync can recognize them
# * it is a hash of the word "pysync" with the word itself inserted arbituarily in it
# * it is written separately like this to prevent FileInfo.islocalgdoc from recognizing this file as a local gdoc file
EXE_SIGNATURE = "#da84f858e8104ca0534138cfa2ea" + "pysync" + "2ccf69e6a9d2b7481882ff1a651ad177a108"
