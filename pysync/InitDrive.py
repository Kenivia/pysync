import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError, TransportError
from json.decoder import JSONDecodeError

from pysync.Exit import exc_with_message
from pysync.Timer import logtime
from pysync.Functions import get_root


CLIENT_SECRET = "/data/client_secrets.json"

def process_creds(creds, scopes):
    if creds and creds.valid:
        return creds

    if creds and creds.refresh_token:  # * this was bugged from the tutorial..
        try:
            creds.refresh(Request())
            print("Old token refreshed successfully")
            return creds

        except RefreshError:
            print("Couldn't refresh old token")

        except TransportError:
            exc_with_message(
                "pysync couldn't refresh your token, please check your internet connectio")

    print("Requesting a new token")
    flow = InstalledAppFlow.from_client_secrets_file(
        get_root() + CLIENT_SECRET, scopes)
    creds = flow.run_local_server(port=0)
    return creds


@logtime
def init_drive():
    """Initializes the google drive and returns an UNPICKLABLE object"""

    creds = None
    scopes = ['https://www.googleapis.com/auth/drive']

    token_path = get_root() + "/data/Internal/token.json"
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except JSONDecodeError:
            pass

    creds = process_creds(creds, scopes)
    with open(token_path, 'w') as f:
        f.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    return service.files()
