"""
Meta Graph API Permissions & Health Inspector
Checks whether your current Facebook Page & Instagram tokens are valid, unexpired,
and have the required publishing permissions.
"""
import os
import sys
from dotenv import load_dotenv
import requests

def inspect_meta_credentials():
    load_dotenv()

    fb_page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()
    fb_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    ig_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "").strip()
    ig_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()

    print("=" * 65)
    print("        META GRAPH API CREDENTIAL & PERMISSION CHECK")
    print("=" * 65)

    if not fb_token:
        print("❌ [Facebook] FACEBOOK_PAGE_ACCESS_TOKEN is missing from .env")
    if not fb_page_id:
        print("❌ [Facebook] FACEBOOK_PAGE_ID is missing from .env")
    if not ig_token:
        print("❌ [Instagram] INSTAGRAM_ACCESS_TOKEN is missing from .env")
    if not ig_account_id:
        print("❌ [Instagram] INSTAGRAM_ACCOUNT_ID is missing from .env")

    # 1. Test Facebook Token
    print(f"\n--- [1] Facebook Page Check (Page ID: {fb_page_id}) ---")
    if fb_token:
        r_me = requests.get(f"https://graph.facebook.com/v21.0/me?access_token={fb_token}")
        if r_me.status_code == 200:
            me_data = r_me.json()
            print(f"✅ Token Identity: '{me_data.get('name')}' (ID: {me_data.get('id')})")
            
            # Check permissions
            r_perm = requests.get(f"https://graph.facebook.com/v21.0/me/permissions?access_token={fb_token}")
            if r_perm.status_code == 200:
                perms_data = r_perm.json().get("data", [])
                granted = {p["permission"] for p in perms_data if p.get("status") == "granted"}
                
                print(f"• Active Permissions ({len(granted)}): {', '.join(sorted(granted))}")
                
                required_fb = ["pages_manage_posts", "pages_read_engagement"]
                missing_fb = [p for p in required_fb if p not in granted]
                if missing_fb:
                    print(f"⚠️ MISSING required Facebook permissions: {', '.join(missing_fb)}")
                else:
                    print("✅ All required Facebook publishing permissions are GRANTED!")
            
            # Check Page Access
            r_page = requests.get(f"https://graph.facebook.com/v21.0/{fb_page_id}?fields=id,name,tasks&access_token={fb_token}")
            if r_page.status_code == 200:
                page_data = r_page.json()
                print(f"✅ Access to Page '{page_data.get('name')}' verified! Tasks: {page_data.get('tasks')}")
            else:
                print(f"⚠️ Cannot manage Page {fb_page_id}: {r_page.text[:200]}")
        else:
            err = r_me.json().get("error", {})
            code = err.get("code")
            subcode = err.get("error_subcode")
            msg = err.get("message", "")
            if code == 190 and subcode == 463:
                print(f"❌ TOKEN EXPIRED: {msg}")
                print("   Your Meta Access Token expired. Graph API Explorer tokens only last 1-2 hours.")
            else:
                print(f"❌ Token Validation Failed (Code {code}): {msg}")

    # 2. Test Instagram Account
    print(f"\n--- [2] Instagram Professional Account Check (ID: {ig_account_id}) ---")
    if ig_token:
        r_ig = requests.get(f"https://graph.facebook.com/v21.0/{ig_account_id}?fields=id,username,name&access_token={ig_token}")
        if r_ig.status_code == 200:
            ig_data = r_ig.json()
            print(f"✅ Connected Instagram Account: @{ig_data.get('username')} ({ig_data.get('name', '')})")
            
            # Check permissions for IG
            r_perm = requests.get(f"https://graph.facebook.com/v21.0/me/permissions?access_token={ig_token}")
            if r_perm.status_code == 200:
                perms_data = r_perm.json().get("data", [])
                granted = {p["permission"] for p in perms_data if p.get("status") == "granted"}
                required_ig = ["instagram_basic", "instagram_content_publish"]
                missing_ig = [p for p in required_ig if p not in granted]
                if missing_ig:
                    print(f"⚠️ MISSING required Instagram permissions: {', '.join(missing_ig)}")
                else:
                    print("✅ All required Instagram publishing permissions are GRANTED!")
        else:
            err = r_ig.json().get("error", {})
            code = err.get("code")
            subcode = err.get("error_subcode")
            msg = err.get("message", "")
            if code == 190 and subcode == 463:
                print(f"❌ TOKEN EXPIRED: {msg}")
            else:
                print(f"❌ Instagram Verification Failed (Code {code}): {msg}")

    print("\n" + "=" * 65)

if __name__ == "__main__":
    inspect_meta_credentials()
