import copy
import psutil
import os
import json
from functools import lru_cache
from pathlib import PurePath

from pysync.Functions import (
    remove_slash,
    abs_path,
    assert_start,
)


def check_options():

    expected_types = {
        "Local path": str,
        "Ask before exit": bool,
        "Hide forced ignore": bool,
        "Print upload progress": bool,
        "Compare md5sum": bool,

        "Max upload threads": int,
        "Max compute threads": int,

        "Always pull": list,
        "Always push": list,
        "Always ignore": list,

        "Default pull": list,
        "Default push": list,
        "Default ignore": list,
    }

    with open(str(PurePath(__file__).parent.parent) + "/data/Options.json", "r") as f:
        options = json.load(f)

    seen_keys = []

    for key in options:
        if key not in expected_types:
            print("Unknown key: \"{}\" in Options.json, ignored".format(key))

        assert isinstance(options[key], expected_types[key])
        seen_keys.append(key)

    if len(seen_keys) < len(options):
        missing = options.keys() - seen_keys
        raise ValueError("The following keys are missing from Options.json: " + ", ".join(missing))

    if options["Max upload threads"] > 50:
        print("Warning! \"Max upload threads\" was set to a value higher than 50. This may cause upload to fail")

    assert os.path.isdir(remove_slash(abs_path(options["Local path"])))

    assert_start(options["Local path"], options["Always pull"])
    assert_start(options["Local path"], options["Always push"])
    assert_start(options["Local path"], options["Always ignore"])

    dpull = options["Default pull"]
    dpush = options["Default push"]
    dignore = options["Default ignore"]
    temp = copy.deepcopy(dpull)
    temp.extend(dpush)
    temp.extend(dignore)
    if len(dpull) + len(dpush) + len(dignore) != 4:
        raise AssertionError(
            "Options Default pull, Default push Default ignore must contain exactly 4 items between them")

    needed = ["local_new", "content_change", "mtime_change", "remote_new"]
    for i in needed:
        if temp.count(i) != 1:
            raise AssertionError("""Options DEFAULT_PUSH, DEFAULT_PULL and DEFAULT_IGNORE are not set correctly.
Each of the following must be included exactly once:
\t\"local_new\", \"content_change\", \"mtime_change\", \"remote_new\"""")

    for i in expected_types:
        load_options(i)


def replace_alias(inp):
    """The purpose of these aliases are to make Option.json more readable,
    so only keys in present in Options.json will have aliases

    Args:
        inp (str): input key

    Returns:
        str: if it matches an alias, return the human readable version, otherwise don't touch it
    """
    alias = {
        "Local path": ["PATH"],
        "Ask before exit": ["ASK_AT_EXIT"],
        "Hide forced ignore": ["HIDE_FIGNORE"],
        "Print upload progress": ["PRINT_UPLOAD"],
        "Compare md5sum": ["CHECK_SUM", "CHECK_MD5", "CHECKSUM"],

        "Max upload threads": ["MAX_UPLOAD"],
        "Max compute threads": ["MAX_COMPUTE"],

        "Always pull": ["APULL"],
        "Always push": ["APUSH"],
        "Always ignore": ["AIGNORE"],

        "Default pull": ["DPULL"],
        "Default push": ["DPUSH"],
        "Default ignore": ["DIGNORE"],

    }

    for key in alias:
        if inp == key or inp in alias[key]:
            return key
    return inp


@lru_cache
def load_options(*keys):

    if len(keys) > 1:
        # * doing this in this weird way to take advantage of cache
        return tuple([load_options(i) for i in keys])
    else:
        root_path = str(PurePath(__file__).parent.parent)
        with open(root_path + "/data/Options.json", "r") as f:
            options = json.load(f)

        key = replace_alias(keys[0])
        if key == "Max compute threads":
            temp = options[key]
            return psutil.cpu_count() if temp < 1 else temp

        elif key == "Local path":
            # * slash removal is vital for a lot of the program
            return remove_slash(abs_path(options[key]))

        elif key == "Always push" or key == "Always pull" or key == "Always ignore":
            return [remove_slash(abs_path(i)) for i in options[key]]

        elif key == "RECHECK_TIME":
            return 0.01

        elif key == "ROOT":
            # * root as in the directory containing the folder pysync & data
            # * ends with no slash
            return root_path

        elif key == "SIGNATURE":
            # todo take care of cases where the signature is changed?
            return "#da84f858e8104ca0534138cfa2ea" + "pysync" + "2ccf69e6a9d2b7481882ff1a651ad177a108"

        else:
            return options[key]
