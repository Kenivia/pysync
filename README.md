# pysync

pysync syncs the content of a Google Drive folder and a local folder. Only Linux is supported, there is an app by Google for Windows and macOS 

This is not a background sync script - it is currently intended for use with user confirmation

pysync is similar to [drive](https://github.com/odeke-em/drive) with a few differences:
  - detects changes much faster - ~150s -> ~40s total for ~5400 files
  - hopefully a bit more user friendly
 


## Google stuff

- First and foremost, this app is not yet verified by Google. Therefore, you can't easily give the code permission to access and modify your drive.
- In order for the code to access your drive you'll have to create your own credentials.
- The idea is that you make your own personal project and make yourself a test user.
- The alternative is that I put your email down as a tester in my project, but that is slow and has a limit of 100 testers
- Unfortunately, tutorials on this are rather hidious so please follow this step by step guide. This is up to date as of April 2022
  -   go to https://console.cloud.google.com/
  -   click on "Select a project" towards the top left
  -   click on "NEW PROJECT"
  -   pick a name
  -   select the project
  -   click the 3 line burger icon on the top left
  -   under APIs & Services, click Credentials
  -   click CREATE CREDENTIALS
  -   click OAuth client ID
  -   click CONFIGURE CONSENT SCREEN
  -   click External
  -   enter any App name(pysync), your own User support email and the developer email(any email address will do)
  -   click Save and continue
  -   Click ADD OR REMOVE SCOPES
  -   there will be a link that says [Google API Library](https://console.cloud.google.com/apis/library), open this in a new tab
  -   search for Google drive api, or use [this link](https://console.cloud.google.com/apis/library/drive.googleapis.com)
  -   click Enable
  -   now go back to the earlier tab with the search bar, you might have to refresh the page and go back to where you were
  -   enter google drive in the search bar, click the first one(Google Drive API)
  -   now there should be a list of 16 options, each of them represent a certain amount of permission
  -   tick the box on the one that says .../auth/drive under Scope, which should also say "See, edit, create, and delete all of your Google Drive files"
  -   scroll down a bit and click UPDATE
  -   there should now be a corresponding entry under "Your sensitive scopes"
  -   click SAVE AND CONTINUE
  -   click ADD USERS
  -   enter the gmail address for the google drive that you're trying to sync
  -   click SAVE AND CONTINUE
  -   go back to the Credentials tab on the left
  -   click CREATE CREDENTIALS and OAuth client ID(just like before)
  -   select Desktop app for Application type, and enter any Name(pysync)
  -   click CREATE
  -   you'll be prompted with a screen, click DOWNLOAD JSON
  -   rename the file to `client_secrets.json` and place this file in `./pysync/data`, replacing the dummy file that's already in there
  -   and you're done!
- I totally understand if you feel skeptical giving me your credentials, but the code is right here and you're welcome to have a look
  
## Requirements:

- `python3`: `sudo apt install python3`

- `pydrive2`, `send2trash`: `pip install pydrive2 send2trash`
  
- `xdg-open`: present on most Linux desktop environments(used for opening gdoc files by double clicking, other than that everything will work fine)
   
- Either `gnome-terminal` or `xfce4-terminal` for quick restart of the syncing process

- a folder at `~/gdrive` to sync with (you can change the location in `./pysync/options.py`)

This is tested on Linux Mint with python3.8.5 and Cinnamon 5.0. 

## Usage

MAKE A BACKUP OF YOUR GOOGLE DRIVE FOLDER BEFORE YOU RUN THIS!
- `python3 ./pysync/pysync`  

You'll(hopefully) be prompted by a google page asking for permission to your google files


## Current features

- Compares the remote google drive with the local drive
- Detects 4 types of changes:
  - local_new: the file is only found in the local copy. This can also mean that it was deleted remotely
  - remote_new: the file is only found in the remote copy. This can also mean that it was deleted locally
  - content_change: the md5sum of the local and remote files don't match
  - mtime_change: the modification times of the local file is newer than the remote file.
- The user can then choose whether to push or pull each type
- Applies the chosen operations
- For Google Docs, Google Sheets and Google Slides files, downloads an executable text file that links to the file
- Ext3/4 don't allow folders and files with the same name, but is fine on Google drive. This is checked and prevented by the script. You can avoid this problem with Capitalizations.


## Known issues/plans

- Google Docs files are currently download and delete only 
  - moving the text file locally won't move the remote copy
- The always_push and always_pull settings don't override until after user inputs(confusing for the user but works)
- pydrive is not exactly reliable - planning on switching to the original Google API

## Contributing
This is in an early stage of development, feedback & help is greatly appreciated!
