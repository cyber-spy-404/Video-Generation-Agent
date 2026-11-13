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
    print("📘 FACEBOOK PAGE REELS & VIDEO SETUP ASSISTANT")
    print("======================================================================")
    print("This script retrieves your Facebook Page ID and generates a permanent")
    print("Page Access Token to auto-publish Reels directly to your Facebook Page.\n")

    print("HOW TO GET YOUR INITIAL TOKEN:")
    print("1. Open Meta Graph API Explorer: https://developers.facebook.com/tools/explorer/")
    print("2. In the top right, select your Meta App.")
    print("3. Under 'Permissions', add:")
    print("   - pages_show_list")
    print("   - pages_read_engagement")
    print("   - pages_manage_posts")
    print("4. Click 'Generate Access Token' and click Continue/Allow.")
    print("----------------------------------------------------------------------\n")

    user_token = input("Enter the User Access Token from Graph API Explorer: ").strip()
    if not user_token:
        print("[!] Token cannot be empty.")
        return

    # 1. Fetch user's managed Facebook Pages
    print("\n[*] Fetching Facebook Pages managed by your account...")
    pages_url = "https://graph.facebook.com/v21.0/me/accounts"
    try:
        resp = requests.get(pages_url, params={"access_token": user_token}, timeout=20)
        data = resp.json()

        if resp.status_code != 200 or "data" not in data:
            print("[!] Error fetching pages:", data)
            return

        pages = data.get("data", [])
        if not pages:
            print("[!] No Facebook Pages found under this account.")
            print("    Please create a Facebook Page at https://www.facebook.com/pages/create")
            return

        print(f"\n[+] Found {len(pages)} Facebook Page(s):")
        for idx, page in enumerate(pages, 1):
            print(f"  [{idx}] {page.get('name')} (Page ID: {page.get('id')})")

        choice = 1
        if len(pages) > 1:
            try:
                choice = int(input(f"\nSelect a page to post to [1-{len(pages)}]: ").strip())
            except ValueError:
                choice = 1

        selected_page = pages[choice - 1]
        page_id = selected_page["id"]
        page_token = selected_page["access_token"]
        page_name = selected_page["name"]

        print(f"\n[+] Selected Page: {page_name} (ID: {page_id})")

        # Save to .env
        update_env_variable("FACEBOOK_PAGE_ID", str(page_id))
        update_env_variable("FACEBOOK_PAGE_ACCESS_TOKEN", str(page_token))
        update_env_variable("FACEBOOK_AUTO_POST", "true")

        print("\n[✔] Updated .env file automatically:")
        print(f"    FACEBOOK_PAGE_ID={page_id}")
        print(f"    FACEBOOK_PAGE_ACCESS_TOKEN={page_token[:15]}...")
        print("    FACEBOOK_AUTO_POST=true")
        print(f"\nYour AI Video Automation is now fully authorized to post Reels directly to '{page_name}' on Facebook!")

    except Exception as e:
        print(f"[!] Request exception: {e}")

if __name__ == "__main__":
    main()

