import copy
import multiprocessing
import os
import json
import platform
import shutil
import sys
from json_minify import json_minify

from functools import lru_cache

from pysync.Commons import get_root
from pysync.Exit import exit_with_msg


OPTIONS_PATH = "/data/Options.json"
DEFAULT_OPTIONS_PATH = "/data/Internal/Default Options.json"
# * These are needed to find Options.json in the first place
# * so they are not configurable


alias = {
    "Local path": "PATH",
    "Ask before exit": "ASK_AT_EXIT",
    "Hide forced ignore": "HIDE_FIGNORE",
    "Print commit progress": "PRINT_UPLOAD",
    "Compare all md5sum": "CHECK_MD5",
    "Ask for abuse acknowledgement on startup": "ASK_ABUSE",
    "Print absolute path": "FULL_PATH",

    "Max upload threads": "MAX_UPLOAD",
    "Max compute threads": "MAX_COMPUTE",

    "Max retry count": "MAX_RETRY",

    "Always pull": "APULL",
    "Always push": "APUSH",
    "Always ignore": "AIGNORE",

    "Default pull": "DPULL",
    "Default push": "DPUSH",
    "Default ignore": "DIGNORE",

    "Get remote cache interval": "CACHE_INTERVAL",

}

expected_types = {
    "Local path": str,
    "Ask before exit": bool,
    "Hide forced ignore": bool,
    "Print commit progress": bool,
    "Compare all md5sum": bool,
    "Ask for abuse acknowledgement on startup": bool,
    "Print absolute path": bool,

    "Max upload threads": int,
    "Max compute threads": int,
    "Max retry count": int,

    "Always pull": list,
    "Always push": list,
    "Always ignore": list,

    "Default pull": list,
    "Default push": list,
    "Default ignore": list,

    "Get remote cache interval": int,

}


def remove_slash(path):
    return path[:-1] if path.endswith("/") else path


def abs_path(inp):
    """Converts inp into an absolute path

    takes care of: "..", ".", "~" and when there's no prefix
    the path will behave just like in terminals
    This is different to os.path.abspath, which just adds cwd to the front
    """
    if inp.startswith(".."):
        return "/".join(os.getcwd().split("/")[0:-1]) + inp[2:]
    elif inp.startswith("."):
        return os.getcwd() + inp[1:]

    elif inp.startswith("~"):
        return str(os.path.expanduser("~")) + inp[1:]

    elif not inp.startswith("/"):
        return os.getcwd() + "/" + inp
    else:
        return inp


def assert_list_start(start, inp_list):
    for i in inp_list:
        assert i.startswith(start)


def code_to_alias(alias, inp):
    for i in alias:
        if alias[i] == inp:
            return i
    raise ValueError


def alias_to_code(raw_options):

    options = {}
    for raw_key in raw_options:
        options[alias[raw_key]] = raw_options[raw_key]
    return options


def load_json_file(path):
    return json.loads(json_minify(open(path, "r").read()))


def real_parse_options():

    if platform.system() != "Linux":
        print("Warning! pysync is intended to run only on Linux")

    options_path = get_root() + OPTIONS_PATH
    defaults_path = get_root() + DEFAULT_OPTIONS_PATH

    if not os.path.isfile(options_path):
        print("Options not found at " + options_path + ", using default options")
        shutil.copyfile(defaults_path, options_path)

    raw_options = load_json_file(options_path)
    default_options = load_json_file(defaults_path)
    seen_keys = []

    for raw_key in raw_options:
        if raw_key not in expected_types:
            print(f"Unknown key: \"{raw_key}\" in {OPTIONS_PATH}, ignored")

        assert isinstance(raw_options[raw_key], expected_types[raw_key])
        seen_keys.append(raw_key)

    if len(seen_keys) < len(default_options):
        missing = default_options.keys() - seen_keys
        raise ValueError(
            f"The following keys are missing from {OPTIONS_PATH}: " + ", ".join(missing))

    options = alias_to_code(raw_options)

    if options["MAX_UPLOAD"] > 50:
        print("Warning! \"Max upload threads\" was set to a value higher than 50. This may cause uploads to fail")

    options["PATH"] = remove_slash(abs_path(options["PATH"]))
    options["APULL"] = [remove_slash(abs_path(i)) for i in options["APULL"]]
    options["APUSH"] = [remove_slash(abs_path(i)) for i in options["APUSH"]]
    options["AIGNORE"] = [remove_slash(abs_path(i)) for i in options["AIGNORE"]]

    assert os.path.isdir(options["PATH"])
    assert_list_start(options["PATH"], options["APULL"])
    assert_list_start(options["PATH"], options["APUSH"])
    assert_list_start(options["PATH"], options["AIGNORE"])

    dpull = options["DPULL"]
    dpush = options["DPUSH"]
    dignore = options["DIGNORE"]

    temp = copy.deepcopy(dpull)
    temp.extend(dpush)
    temp.extend(dignore)

    if len(dpull) + len(dpush) + len(dignore) != 3:
        raise AssertionError(
            "The options: Default pull, Default push and Default ignore must contain exactly 3 items between them")

    needed = ["local_new", "content_change", "remote_new"]
    for i in needed:
        if temp.count(i) != 1:
            raise AssertionError("""The options: DEFAULT_PUSH, DEFAULT_PULL and DEFAULT_IGNORE are not set correctly.
Each of the following must be included exactly once:
\t\"local_new\", \"content_change\", \"remote_new\"""")

    assert options["CACHE_INTERVAL"] > 0

    print("Options parsed successfully")


@lru_cache(None)
def get_option(*keys):

    if len(keys) > 1:
        # * doing this in this weird way to take advantage of cache
        return tuple([get_option(i) for i in keys])
    else:

        options_path = get_root() + OPTIONS_PATH
        raw_options = load_json_file(options_path)

        options = alias_to_code(raw_options)
        key = keys[0]
        if key == "MAX_COMPUTE":
            temp = options[key]
            return multiprocessing.cpu_count() if temp < 1 else temp

        elif key == "PATH":
            # * slash removal is vital for a lot of the program
            return remove_slash(abs_path(options[key]))

        elif key == "APUSH" or key == "APULL" or key == "AIGNORE":
            return [remove_slash(abs_path(i)) for i in options[key]]

        elif key == "RETRY_TIME":
            return 0

        elif key == "SIGNATURE":
            return "#da84f858e8104ca0534138cfa2ea" + "pysync" + "2ccf69e6a9d2b7481882ff1a651ad177a108"

        else:
            return options[key]


def parse_options():
    try:
        real_parse_options()

    except Exception as e:
        message = "pysync failed to parse " + get_root() + OPTIONS_PATH +\
            ", A copy of default options can be found at " + get_root() + DEFAULT_OPTIONS_PATH
        exit_with_msg(msg=message, exception=e, raise_silent=False)
        sys.exit()
