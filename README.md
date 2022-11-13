# pysync

pysync is a fast google drive syncing script for Linux

This is not a background sync script - it is currently intended for use with user confirmation

pysync is similar to [drive by odeke-em](https://github.com/odeke-em/drive), but is much faster, thanks mostly to parallelism and(probably) the more recent API used

## Google Credentials

- First and foremost, this app is not yet verified by Google. Therefore, you can't give the code permission to access and modify your drive.
- For the code to access your drive you'll have to create your own credentials.
- **You will make your own "project" and make yourself a test user.**
- Unfortunately, tutorials on this are rather hideous so please follow this step by step guide. This is up to date as of June 2022
  - Go to <https://console.cloud.google.com/>
  - Click on "Select a project" towards the top left(If you already have a project selected, it will say the name of that project instead)
  - Click on "NEW PROJECT"
  - Pick a name(pysync)
  - Select the project
  - In a new tab, go to [this link](https://console.cloud.google.com/apis/library/drive.googleapis.com) to enable Google Drive API for this project
  - Click "ENABLE"
  - Go back to the [previous tab](https://console.cloud.google.com)
  - Click the 3 line burger icon on the top left
  - Under "APIs & Services", click "Credentials"
  - Click "CREATE CREDENTIALS"(towards the top)
  - Click "OAuth client ID"
  - Click "CONFIGURE CONSENT SCREEN"
  - Click "External"
  - Enter any App name(pysync), a user support email and developer email(any email address will do)
  - Click "SAVE AND CONTINUE"
  - Click "ADD OR REMOVE SCOPES"
  - Search for "Google drive API" in the search bar(next to the word "Filter")
  - Now there should be a list of 16 options, each of them representing a certain amount of permission
  - Tick the box on the one that says ".../auth/drive" under "Scope"(the 2nd one, it also says "See, edit, create, and delete all of your Google Drive files")
  - Scroll down a bit and click "UPDATE"
  - There should now be a corresponding entry under "Your sensitive scopes"
  - Click "SAVE AND CONTINUE"
  - Click "ADD USERS"
  - Enter the gmail address **for the google drive that you're trying to sync**
  - Click "SAVE AND CONTINUE"
  - Go back to the Credentials tab on the left
  - Click "CREATE CREDENTIALS" and "OAuth client ID"(just like before)
  - Select "Desktop app" for Application type, and enter any Name(pysync)
  - Click "CREATE"
  - You'll be prompted with a screen, click "DOWNLOAD JSON"
  - Rename the file to `client_secrets.json` and copy this file into `./pysync/data/`
  
## Requirements

- `python3.8+`

- `json-minify`, `python-dateutil`, `send2trash`, `google-api-python-client` and `google-auth-oauthlib`

- pysync will detect missing packages and install them automatically with pip.
  
- a folder at `~/gdrive` to sync with (you can change the location in `./pysync/data/Options.json`)

- `client_secret.json` created using the procedure above and placed in `./pysync/data/`

- `xdg-open`(used for opening gdoc files by double clicking), `gnome-terminal` or `xfce4-terminal`(for a quick restart of the syncing process). These are not essential for other functions of pysync

## Usage

***MAKE A BACKUP OF YOUR GOOGLE DRIVE FOLDER BEFORE RUNNING THIS!***

- `cd ./pysync-master`
- `python3 pysync --diff`
- (optional)`python3 pysync --modify`
- finally: `python3 pysync --commit`

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

## Current plans

- Background syncing and maybe a GUI, similar to [Google's Windows/macOs app](https://www.google.com/drive/download/), is the long term goal

## Contributing

Any feedback or help is greatly appreciated!

Contact me at kenivia.fan@gmail.com
