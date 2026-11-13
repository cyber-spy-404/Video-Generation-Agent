import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def main():
    print("======================================================================")
    print("📺 YOUTUBE STUDIO OAUTH AUTHENTICATION SETUP")
    print("======================================================================")

    base_dir = Path(__file__).resolve().parent.parent
    client_secrets = base_dir / "client_secrets.json"
    token_file = base_dir / "token.json"

    if not client_secrets.exists():
        print(f"\n[!] Error: '{client_secrets.name}' was not found in {base_dir}")
        print("\nHow to get client_secrets.json:")
        print("1. Open Google Cloud Console: https://console.cloud.google.com/")
        print("2. Create a project and enable 'YouTube Data API v3'")
        print("3. Go to 'APIs & Services' -> 'Credentials' -> 'Create Credentials' -> 'OAuth client ID'")
        print("4. Application type: 'Desktop app' or 'Web application'")
        print("5. Download the JSON and place it in this folder named 'client_secrets.json'")
        return

    print("\nStarting OAuth flow...")
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)

    try:
        # Try local server first (works if browser available or port forwarded)
        creds = flow.run_local_server(port=8080, open_browser=True)
    except Exception as e:
        print(f"\nLocal server could not open browser automatically ({e}).")
        print("Switching to console URL mode...")
        # Fallback URL mode
        flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        auth_url, _ = flow.authorization_url(prompt="consent")
        print("\n1. Visit this URL in any browser:")
        print(f"\n   {auth_url}\n")
        code = input("2. Enter the authorization code from that page: ").strip()
        flow.fetch_token(code=code)
        creds = flow.credentials

    with open(token_file, "w") as f:
        f.write(creds.to_json())

    print(f"\n[+] Success! Credentials saved to '{token_file.name}'.")
    print("[+] YouTube Studio upload is now authenticated and ready for 24/7 automation!")

if __name__ == "__main__":
    main()

