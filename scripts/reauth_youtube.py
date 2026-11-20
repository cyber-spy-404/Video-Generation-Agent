import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).resolve().parent.parent
CLIENT_SECRETS = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def authenticate_youtube():
    if not CLIENT_SECRETS.exists():
        print(f"❌ Error: {CLIENT_SECRETS} does not exist!")
        return

    print("======================================================================")
    print("🔑 RE-AUTHENTICATING YOUTUBE DATA API (GOOGLE OAUTH)")
    print("======================================================================")
    print("A browser window will open. Sign in to the Google account that owns your YouTube channel.")
    
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    
    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())
        
    print(f"\n✅ Fresh token saved successfully to: {TOKEN_FILE.name}")
    print("Upload this new token.json to your Q-Fi Cloud server root directory!")
    print("======================================================================")

if __name__ == "__main__":
    authenticate_youtube()
