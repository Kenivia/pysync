# pysync

pysync is a fast google drive syncing script for Linux. It was last known to work in 2022, I havn't tested it thoroughly since then so it may run into issues.

Note that this sohuld not be used as a background sync script - it cannot tell which copy it should keep (Local "last modified" is not reliable). Use as an interactive commandline tool instead.

pysync was inspired by [drive by odeke-em](https://github.com/odeke-em/drive), it is much faster by initiating multiple queries at once.

## Google Credentials

- First and foremost, this app is not verified by Google. Therefore, you can't give the code permission to access and modify your drive like usual apps.
- **You will make your own "project" and make yourself a test user.**
- Tutorials on this are rather hideous so please follow this step by step guide. This is up to date as of April 2026
  - Go to <https://console.cloud.google.com/>
  - Click on "Select a project" towards the top left(If you already have a project selected, it will say the name of that project instead)
  - Click on "New Project"
  - Pick a name(pysync), leave "Parent resource" as "No organisations"
  - Select the project on the top left, or via the button in the notification once it's done spinning
  - In a new tab, go to <https://console.cloud.google.com/apis/library/drive.googleapis.com> to enable Google Drive API for this project
  - Click "ENABLE"
  - Go back to the previous tab (<https://console.cloud.google.com>)
  - Click the 3 line burger icon on the top left
  - Under "APIs & Services", click "Credentials"
  - Click "Create Credentials"(towards the top)
  - Pick any API key name, select "Google Drive API" from the dropdown
  - Leave everything else unchanged, click "Create"
  - Click "OAuth Consent Screen"
  - Click "Get started"
  - Enter any App name(pysync), a user support email and developer email(any email address will do)
  - Agree to the terms and click "Create"
  - Towards the top left, click "Audience"
  - Click "Add users"
  - Enter the gmail address **for the google drive that you're trying to sync**, click "Save"
  - Click "Data access", below "Audience"
  - Click "Add or remove scopes"
  - Search "Google Drive API" in the search bar, tick the one that says ".../auth/drive" (should be second one from the top). It should say "See, edit, create and delete all of your Google Drive files".
  - Click "Save"
  - Click "Clients", again below "Audience"
  - Click "Create client"
  - Select "Desktop app" for Application type, and enter any Name(pysync)
  - Click "CREATE"
  - You'll be prompted with a screen, click "Download JSON"
  - Rename the file to `client_secrets.json` (note the extra 's') and copy this file into `./pysync/data/`
  
## Requirements

- `python3.8+`

- `json-minify`, `python-dateutil`, `send2trash`, `google-api-python-client` and `google-auth-oauthlib`

- pysync will detect missing packages and try to install them automatically with pip.
  
- a folder at `~/gdrive` to sync with (you can change the location in `./pysync/data/Options.json`)

- `client_secrets.json` created using the procedure above and placed in `./pysync/data/`

- `xdg-open`(used for opening gdoc files by double clicking), `gnome-terminal` or `xfce4-terminal`(for a quick restart of the syncing process). These are not essential for other functions of pysync

## Usage

***MAKE A BACKUP OF YOUR GOOGLE DRIVE FOLDER BEFORE RUNNING THIS!***

- `cd ./pysync-master`
- `python3 pysync --diff`, on first use this will prompt you to open a link to grant permission.
- (optional)`python3 pysync --modify`
- finally: `python3 pysync --commit`

Run `python3 pysync -h` for a more comprehensive usage guide:

```text
  -h, --help            show this help message and exit
  -w, --watcher         Run "fetch" periodically, and cache it to a file.
                        This is intended to be ran in the background.

  -d [DIFF ...], --diff [DIFF ...]
                        Find differences between the local and remote gdrive.
                        You may specify whether or not to fetch new data using "-d cache" or "-d new"

  -m [MODIFY ...], --modify [MODIFY ...]
                        Modify the changes proposed by diff using "push", "pull", "ignore"

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


  -c, --commit          Commit the changes proposed in diff.
                        MAKE A BACKUP OF YOUR FILES BEFORE RUNNING THIS! There is no more confirmations

  -i [INIT ...], --init [INIT ...]
                        Initialize gdrive token using the client secret file.
                        You can provide the path to the client secret file in the command line

  -f, --fetch           Get metadata of remote files and cache it in a file

  -o, --option          Open options.json

```

Some settings can be configured in Options.json.

## Current features

- Detect differences quickly, depending mostly on the size of the google drive and sometimes the disk read speed(15-20 seconds for ~6000 files)
- The user can then choose which files to push/pull(upload/download)
- Applies the chosen operations in parallel(40 at the same time by default)
- For Google Docs, Google Sheets and Google Slides etc, download an executable text file that links to the file

## Known issues

- Ext3/4 file systems don't allow folders and files with the same name but it is allowed on Google drive. pysync will reject these files. You can avoid this problem with Capitalizations.
- Forced paths(specified in Options.json) don't behave correctly when a forced path contains another forced path
- Having multiple copies of local files corresponding to the same Google doc file may cause issues

## Contributing

Any feedback or help is greatly appreciated!
