import sys

if (__package__ is None or __package__ == "") and not hasattr(sys, 'frozen'):
    # * direct call of __main__.py
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import subprocess as sp
import pkg_resources
import argparse
from argparse import RawTextHelpFormatter


def check_dependencies():
    required = {"json-minify",
                "python-dateutil",
                "send2trash",
                "google-api-python-client",
                "google-auth-oauthlib",
                }
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = list(required - installed)

    if missing:
        missingtext = "\n".join(missing)
        if __name__ == "__main__":

            command_list = [sys.executable, '-m', 'pip', 'install', *missing]
            print("The following packages are required by pysync but are missing:")
            print(missingtext + "\n")
            print("pysync will now try to install the missing packages using the following command:")
            print(" ".join(command_list) + "\n")
            inp = input("Proceed (y/N)? ")
            if inp.lower().strip() == "y":
                print("")
                completed = sp.run(command_list)
                if completed.returncode != 0:
                    print("An error occured while running the command above")
                    sys.exit()
                print("\nInstallation completed successfully")

            else:
                print("Installation was cancelled, exiting")
                sys.exit()
        else:
            print("pysync couldn't initialize because the following packages are missing:" + ", ".join(missing))
            sys.exit()


def init_parser():
    
    COPYRIGHT_TEXT = """pysync Copyright 2022 Kenivia
This program comes with ABSOLUTELY NO WARRANTY. MAKE A BACKUP OF YOUR FILES BEFORE RUNNING THIS!
This is free software, and you are welcome to redistribute it under certain conditions.
For more information, see https://www.gnu.org/licenses/gpl-3.0.html \n\n"""
    parser = argparse.ArgumentParser(prog="pysync",
                                    description="A fast google drive syncing script",
                                    formatter_class=RawTextHelpFormatter,
                                    epilog=COPYRIGHT_TEXT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-w", "--watcher",
                       action="store_true",
                       help="""Run \"fetch\" periodically, and cache it to a file.
This is intended to be ran in the background.\n\n""")

    group.add_argument("-d", "--diff",
                       nargs="*",
                       action="store",
                       help="""Find differences between the local and remote gdrive.
You may specify whether or not to fetch new data using \"-d cache\" or \"-d new\"\n\n""")
    
    group.add_argument("-m","--modify",
                       nargs="*",
                      action="store",
                      help="""Modify the changes proposed by diff using \"push\", \"pull\", \"ignore\"
                      
- `push` means that you want what's on your local storage to replace what's on Google drive.
        This may upload new files, modify remote files or trash remote files
            
- `pull` means that you want what's on Google drive to replace what's on your local storage.
        This may download new files, modify local files or trash local files
        
- `ignore` means that no action will be taken for the chosen file.

Using indices in front of the files, you can specify which files to push, pull or ignore
Use " "(spaces) to separate indices, "-" to specify indices in a range(inclusive on both ends)
Use "all" to represent all indices

Note that "forced" files cannot be modified

Example inputs:
    pysync --modify push 6 5  9
    pysync -m pull 1-4 7 8 (Equivalent to: pull 1 2 3 4 7 8)
    pysync -m ignore 3-5 1 2 (Equivalent to: pull 1 2 3 4 5)
    pysync -m push 7-10 (Equivalent to: push 7 8 9 10)
    pysync -m pull all
\n\n""")
    
    group.add_argument("-c", "--commit",
                       action="store_true",
                       help="""Commit the changes proposed in diff. 
MAKE A BACKUP OF YOUR FILES BEFORE RUNNING THIS! There is no more confirmations\n\n""")

    group.add_argument("-i", "--init",
                       nargs="*",
                       action="store",
                       help="""Initialize gdrive token using the client secret file.
You can provide the path to the client secret file in the command line\n\n""")

    group.add_argument("-f", "--fetch",
                       action="store_true",
                       help="Get metadata of remote files and cache it in a file\n\n")

    group.add_argument("-o", "--option",
                       action="store_true",
                       help="Open options.json\n\n")

    return parser


def check_args(inp):
    count = 0
    for i in vars(inp):
        if vars(inp)[i] or isinstance(vars(inp)[i], list):
            count += 1
    assert count == 1
    return inp



   
if __name__ == "__main__":
    check_dependencies()

    inp_args = init_parser().parse_args()

    from pysync.OptionsParser import parse_options
    from pysync import main
    
    parse_options()

    main(check_args(inp_args))
    
    