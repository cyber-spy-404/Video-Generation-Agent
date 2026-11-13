import os
import re
import sys
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

def update_env_variable(key: str, value: str):
    """Updates or adds an environment variable in the .env file."""
    if not ENV_PATH.exists():
        content = ""
    else:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            content = f.read()

    pattern = rf"^{key}=.*$"
    replacement = f"{key}={value}"

    if re.search(pattern, content, flags=re.MULTILINE):
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        new_content = content.rstrip() + f"\n{replacement}\n"

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

def main():
    print("======================================================================")
    print("📸 INSTAGRAM BUSINESS / CREATOR OAUTH SETUP ASSISTANT")
    print("======================================================================")
    print("This script guides you through exchanging your Meta App authorization code")
    print("for a 60-day Long-Lived Access Token and saves it to your .env automatically.\n")

    app_id = input("1. Enter your Instagram App ID (from Meta App Dashboard): ").strip()
    if not app_id:
        print("[!] App ID cannot be empty.")
        return

    app_secret = input("2. Enter your Instagram App Secret: ").strip()
    if not app_secret:
        print("[!] App Secret cannot be empty.")
        return

    redirect_uri = input("3. Enter your OAuth Redirect URI (configured in App Dashboard, e.g. https://localhost:8000/auth): ").strip()
    if not redirect_uri:
        print("[!] Redirect URI cannot be empty.")
        return

    # Generate Authorization URL
    scopes = "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_messages,instagram_business_manage_comments"
    auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes}"
    )

    print("\n----------------------------------------------------------------------")
    print("STEP 1: Open this authorization link in your browser:")
    print(f"\n{auth_url}\n")
    print("Log in to your Instagram Professional/Creator account and click 'Allow'.")
    print("----------------------------------------------------------------------")

    raw_response = input("STEP 2: Paste the full redirected URL (or the 'code=' value) here:\n").strip()

    # Extract code
    code = raw_response
    if "code=" in raw_response:
        match = re.search(r"code=([^&#]+)", raw_response)
        if match:
            code = match.group(1)

    # Strip any trailing #_ added by Meta
    if code.endswith("#_"):
        code = code[:-2]

    print("\n[*] Exchanging authorization code for short-lived access token...")
    token_url = "https://api.instagram.com/oauth/access_token"
    token_payload = {
        "client_id": app_id,
        "client_secret": app_secret,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code": code
    }

    try:
        resp = requests.post(token_url, data=token_payload, timeout=20)
        data = resp.json()

        if resp.status_code != 200 or "access_token" not in data and "data" not in data:
            print(f"[!] Error getting short-lived token (HTTP {resp.status_code}):", data)
            return

        # Handle both single object and list response
        if "data" in data and isinstance(data["data"], list):
            item = data["data"][0]
            short_token = item.get("access_token")
            user_id = item.get("user_id")
        else:
            short_token = data.get("access_token")
            user_id = data.get("user_id")

        print(f"[+] Short-lived token acquired! User ID: {user_id}")

        # Step 3: Exchange for 60-day Long-Lived Token
        print("[*] Exchanging for 60-Day Long-Lived Access Token...")
        long_lived_url = "https://graph.instagram.com/access_token"
        params = {
            "grant_type": "ig_exchange_token",
            "client_secret": app_secret,
            "access_token": short_token
        }
        ll_resp = requests.get(long_lived_url, params=params, timeout=20)
        ll_data = ll_resp.json()

        if ll_resp.status_code == 200 and "access_token" in ll_data:
            long_token = ll_data["access_token"]
            expires_in = ll_data.get("expires_in", 5184000)
            days = round(expires_in / 86400, 1)

            print(f"[+] SUCCESS! 60-day Long-Lived Token acquired (Valid for {days} days).")

            # Save to .env
            update_env_variable("INSTAGRAM_ACCOUNT_ID", str(user_id))
            update_env_variable("INSTAGRAM_ACCESS_TOKEN", str(long_token))
            update_env_variable("INSTAGRAM_AUTO_POST", "true")

            print("\n[✔] Updated .env file automatically:")
            print(f"    INSTAGRAM_ACCOUNT_ID={user_id}")
            print(f"    INSTAGRAM_ACCESS_TOKEN={long_token[:15]}...")
            print("    INSTAGRAM_AUTO_POST=true")
            print("\nYour AI Video Automation is now fully authorized to post Reels directly to Instagram!")

        else:
            print("[!] Failed to get long-lived token. Falling back to short-lived token:", ll_data)
            update_env_variable("INSTAGRAM_ACCOUNT_ID", str(user_id))
            update_env_variable("INSTAGRAM_ACCESS_TOKEN", str(short_token))
            update_env_variable("INSTAGRAM_AUTO_POST", "true")

    except Exception as e:
        print(f"[!] Request exception: {e}")

if __name__ == "__main__":
    main()

