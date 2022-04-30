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


def code_to_alias(alias, inp):
    for i in alias:
        if alias[i] == inp:
            return i
    raise ValueError


def alias_to_code(raw_options):
    alias = {
        "Local path": "PATH",
        "Ask before exit": "ASK_AT_EXIT",
        "Hide forced ignore": "HIDE_FIGNORE",
        "Print upload progress": "PRINT_UPLOAD",
        "Compare md5sum": "CHECK_MD5",

        "Max upload threads": "MAX_UPLOAD",
        "Max compute threads": "MAX_COMPUTE",
        "Max retry count": "MAX_RETRY",

        "Always pull": "APULL",
        "Always push": "APUSH",
        "Always ignore": "AIGNORE",

        "Default pull": "DPULL",
        "Default push": "DPUSH",
        "Default ignore": "DIGNORE",

    }
    options = {}
    for raw_key in raw_options:
        options[alias[raw_key]] = raw_options[raw_key]
    return options


def cache_options():
    all_available_code = [
        "PATH", "ASK_AT_EXIT", "HIDE_FIGNORE", "PRINT_UPLOAD", "CHECK_MD5",
        "MAX_UPLOAD", "MAX_COMPUTE",
        "APULL", "APUSH", "AIGNORE",
        "DPULL", "DPUSH", "DIGNORE",
        "ROOT", "RECHECK_TIME", "SIGNATURE", "MAX_RETRY"
    ]
    load_options(*all_available_code)  # * to load all the cache


def get_active_path():

    options_path = str(PurePath(__file__).parent.parent) + "/data/Options.json"
    default_options_path = str(PurePath(__file__).parent.parent) + "/data/Default Options.json"

    return options_path if os.path.exists(options_path) else default_options_path


def check_options():

    expected_types = {
        "Local path": str,
        "Ask before exit": bool,
        "Hide forced ignore": bool,
        "Print upload progress": bool,
        "Compare md5sum": bool,

        "Max upload threads": int,
        "Max compute threads": int,
        "Max retry count": int,

        "Always pull": list,
        "Always push": list,
        "Always ignore": list,

        "Default pull": list,
        "Default push": list,
        "Default ignore": list,
    }

    active_path = get_active_path()
    active_name = active_path.split("/"[-1])

    with open(active_path, "r") as f:
        raw_options = json.load(f)
        seen_keys = []

        for raw_key in raw_options:
            if raw_key not in expected_types:

                print(f"Unknown key: \"{raw_key}\" in {active_name}, ignored")

            assert isinstance(raw_options[raw_key], expected_types[raw_key])
            seen_keys.append(raw_key)

        if len(seen_keys) < len(raw_options):
            missing = raw_options.keys() - seen_keys
            raise ValueError(
                f"The following keys are missing from {active_name}: " +
                ", ".join(missing))

    options = alias_to_code(raw_options)

    if options["MAX_UPLOAD"] > 50:
        print("Warning! \"Max upload threads\" was set to a value higher than 50. This may cause upload to fail")

    assert os.path.isdir(remove_slash(abs_path(options["PATH"])))

    assert_start(options["PATH"], options["APULL"])
    assert_start(options["PATH"], options["APUSH"])
    assert_start(options["PATH"], options["AIGNORE"])

    dpull = options["DPULL"]
    dpush = options["DPUSH"]
    dignore = options["DIGNORE"]
    temp = copy.deepcopy(dpull)
    temp.extend(dpush)
    temp.extend(dignore)
    if len(dpull) + len(dpush) + len(dignore) != 4:
        raise AssertionError(
            "The options: Default pull, Default push Default ignore must contain exactly 4 items between them")

    needed = ["local_new", "content_change", "mtime_change", "remote_new"]
    for i in needed:
        if temp.count(i) != 1:
            raise AssertionError("""The options: DEFAULT_PUSH, DEFAULT_PULL and DEFAULT_IGNORE are not set correctly.
Each of the following must be included exactly once:
\t\"local_new\", \"content_change\", \"mtime_change\", \"remote_new\"""")

    cache_options()


@lru_cache
def load_options(*keys):

    if len(keys) > 1:
        # * doing this in this weird way to take advantage of cache
        return tuple([load_options(i) for i in keys])
    else:
        root_path = str(PurePath(__file__).parent.parent)
        active_path = get_active_path()
        with open(active_path, "r") as f:
            raw_options = json.load(f)
        options = alias_to_code(raw_options)
        key = keys[0]
        if key == "MAX_COMPUTE":
            temp = options[key]
            return psutil.cpu_count() if temp < 1 else temp

        elif key == "PATH":
            # * slash removal is vital for a lot of the program
            return remove_slash(abs_path(options[key]))

        elif key == "APUSH" or key == "APULL" or key == "AIGNORE":
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
