import sys

if (__package__ is None or __package__ == "") and not hasattr(sys, 'frozen'):
    # * direct call of __main__.py
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import subprocess as sp
import pkg_resources


required = {"python-dateutil",
            "send2trash",
            "google-api-python-client",
            "google-auth-oauthlib",
            }
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = list(required - installed)

if missing:
    missingtext = ", ".join(missing)
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
            print("Installation was cancelled")
            sys.exit()
    else:
        print("pysync couldn't initialize because the following packages are missing:" + ", ".join(missing))
        sys.exit()

if __name__ == "__main__":
    import pysync
    pysync.main()
