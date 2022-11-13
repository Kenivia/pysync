import os.path
import shutil

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError, TransportError
from json.decoder import JSONDecodeError

from pysync.Exit import exit_with_msg
from pysync.OptionsParser import get_option
from pysync.Commons import check_acknowledgement, get_root


CLIENT_SECRET = "/data/client_secrets.json"
ACK_TEXT = "The prescence of this file indicates that the user has agreed to downloading files marked as 'abuse' from Google drive.\
\nTo disallow this, delete this file."


def process_creds(creds, scopes, user_interact=True):
    if creds and creds.valid:
        print("Token is still valid, no need to refresh")
        return creds

    if creds and creds.refresh_token:  # * the code from the tutorial was bugged
        try:
            creds.refresh(Request())
            print("Old token refreshed successfully")
            return creds

        except RefreshError:
            print("Couldn't refresh old token")

        except TransportError as e:
            exit_with_msg(msg="pysync couldn't refresh your token, please check your internet connection",
                          exception=e)

    if not user_interact:
        exit_with_msg(msg="User interaction was forbidden, will not open a web page",)

    print("Requesting a new token")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(get_root() + CLIENT_SECRET, scopes)
    except FileNotFoundError as e:
        exit_with_msg(msg="The file 'client_secrets.json' is not found at " + get_root() + "/data/",
                      exception=e)

    creds = flow.run_local_server(port=0)
    return creds


def init_drive(user_interact=True):
    """Initializes drive using credentials.json and asks for abuse acknowledgement

    Returns:
        googleapiclient.discovery.Resource: keep in mind this object is unpicklable
                                so it can't be returned by processes(and threads?)
    """

    creds = None
    scopes = ['https://www.googleapis.com/auth/drive']

    token_path = get_root() + "/data/Internal/token.json"
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except JSONDecodeError:
            pass

    creds = process_creds(creds, scopes, user_interact)
    with open(token_path, 'w') as f:
        f.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    print("Google drive token produced successfully")

    if not check_acknowledgement() and get_option("ASK_ABUSE") and user_interact:
        ask_abuse_acknowledge()

    return service.files()


def ask_abuse_acknowledge():

    print("\nGoogle drive marks certain files as 'abuse'. These files are potentially dangerous.\n\
Would you like to download files marked as abuse in the future?")
    inp = input("Type the word 'yes' to confirm(any other input will decline): \n>>> ")
    print("")
    if inp.lower().strip() == "yes":
        with open(get_root() + "/data/Internal/abuse_acknowledged", "w") as f:
            f.write(ACK_TEXT)
        print("pysync will download files marked as 'abuse' in the future.\
\nTo undo this, delete the file " + get_root() + "/data/Internal/abuse_acknowledged")

    else:
        print("pysync will not download files marked as 'abuse'.\
\npysync will continue to list these files but won't actually download them\
\npysync will continue asking you for permission, you may turn this off in Options.json")
    print("")


def copy_client_secret(path):
    if os.path.isfile(path):
        client_secret_path = get_root() + "/data/client_secrets.json"
        shutil.copyfile(path, client_secret_path)
        print(f"Copied FROM {path} TO ==> {client_secret_path}")
    else:
        exit_with_msg(msg=f"Provided path: {path} does not exist or is not a file")
