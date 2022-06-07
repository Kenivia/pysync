# pysync

pysync is a Linux script that uploads & download files to and from Google drive.

This is not a background sync script - it is currently intended for use with user confirmation

pysync is similar to [drive](https://github.com/odeke-em/drive), but is much faster (150s -> <30s for comparing ~5400 files), thanks mostly to parallelism and(probably) the more recent API used

## Google Credentials

- First and foremost, this app is not yet verified by Google. Therefore, you can't easily give the code permission to access and modify your drive.
- For the code to access your drive you'll have to create your own credentials.
- The idea is that you make your own personal project and make yourself a test user.
- Unfortunately, tutorials on this are rather hideous so please follow this step by step guide. This is up to date as of April 2022
  - go to <https://console.cloud.google.com/>
  - click on "Select a project" towards the top left
  - click on "NEW PROJECT"
  - pick a name
  - select the project
  - click the 3 line burger icon on the top left
  - under APIs & Services, click Credentials
  - click CREATE CREDENTIALS
  - click OAuth client ID
  - click CONFIGURE CONSENT SCREEN
  - click External
  - enter any App name(pysync), your own User support email and the developer email(any email address will do)
  - click Save and continue
  - click ADD OR REMOVE SCOPES
  - there will be a link that says [Google API Library](https://console.cloud.google.com/apis/library), open this in a new tab
  - search for Google drive API, or use [this link](https://console.cloud.google.com/apis/library/drive.googleapis.com)
  - click Enable
  - now go back to the earlier tab with the search bar, you might have to refresh the page and go back to where you were
  - enter google drive in the search bar, click the first one(Google Drive API)
  - now there should be a list of 16 options, each of them representing a certain amount of permission
  - tick the box on the one that says .../auth/drive under Scope, which should also say "See, edit, create, and delete all of your Google Drive files"
  - scroll down a bit and click UPDATE
  - there should now be a corresponding entry under "Your sensitive scopes"
  - click SAVE AND CONTINUE
  - click ADD USERS
  - enter the gmail address for the google drive that you're trying to sync
  - click SAVE AND CONTINUE
  - go back to the Credentials tab on the left
  - click CREATE CREDENTIALS and OAuth client ID(just like before)
  - select Desktop app for Application type, and enter any Name(pysync)
  - click CREATE
  - you'll be prompted with a screen, click DOWNLOAD JSON
  - rename the file to `client_secrets.json` and place this file in `./pysync/data`
  
## Requirements

- `python3.6+`

- `python-dateutil`, `send2trash`, `google-api-python-client` and `google-auth-oauthlib`

- pysync will detect missing packages and install them automatically using `pip`.
  
- a folder at `~/gdrive` to sync with (you can change the location in `./pysync-master/data/Options.json`)

- `client_secret.json` created using the procedure above and placed in `./pysync-master/data/`

- `xdg-open`(used for opening gdoc files by double clicking)

- Either `gnome-terminal` or `xfce4-terminal` for a quick restart of the syncing process. Other than this function, any terminal will do

## Usage

- **MAKE A BACKUP OF YOUR GOOGLE DRIVE FOLDER BEFORE RUNNING THIS!**

- `python3 ./pysync-master/pysync`

You will be prompted by a google page asking for permission to your google files. Then, follow the instructions

Options can be specified using ./pysync-master/data/Option.json

Typing `help` before applying changes will display the following message:

    pysync has detected some differences between the local files and the files on Google drive.
    the changes above are proposed, the following commands are available:


    apply
        `apply` or simply submitting no input(pressing Enter) will commit these changes

        MAKE A BACKUP OF YOUR FILES BEFORE RUNNING THIS! pysync comes with ABSOLUTELY NO WARRANTY

        pysync creates many(40 by default) processes to upload/download changes. This speeds up
        the process for small files. However, this means that cancelling the process will require
        the user to press Ctrl+C a few times quickly.


    push, pull, ignore
        - `push` means that you want what's on your local storage to replace what's on Google drive.
                This may upload new files, modify remote files or trash remote files
        - `pull` means that you want what's on Google drive to replace what's on your local storage.
                This may download new files, modify local files or trash local files
        - `ignore` means that no action will be taken for the chosen file.

        Using their index printed above, you can specify which paths to push, pull or ignore
        Use `,` or ` `(space) to separate indices
        Use `-` to specify indices in a range(inclusive)
        Use `all` to specify all indices
        
        Example inputs:
            push 6 5
            pull 4
            ignore 1,  3,2 
            push 7-10(This will be the same as: push 7, 8, 9, 10)
            pull all

    restart
        Terminate this process and use the same python interpreter to start another pysync instance

        This will not apply the pending changes


    exit
        Terminate this process without applying the pending changes


    help
        Display this help message

## Current features

- Detect differences quickly, depending mostly on the size of the google drive and someties the disk read speed
- The user can then choose which files to push/pull(upload/download)
- Applies the chosen operations in parallel
- For Google Docs, Google Sheets and Google Slides etc, download an executable text file that links to the file
- Ext3/4 file systems don't allow folders and files with the same name but it is allowed on Google drive. You can avoid this problem with Capitalizations.
- Keeps track of how long each stage of the program took

## Known issues/plans

- Forced paths(specified in Options.json) don't behave correctly when a forced path contains another forced path
- When a folder fails to upload after retrying, its children files won't give up and will hang indefinitely
- Google Docs files are currently download and delete only(moving the text file locally won't move the remote copy)
- Implementation of background syncing and maybe a GUI, similar to [Google's Windows/macOs app](https://www.google.com/drive/download/), is the long term goal

## Contributing

Any feedback & help are greatly appreciated!
