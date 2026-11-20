"""
Meta Facebook / Instagram Permanent Token Generator
Converts a short-lived Graph API Explorer token into a 60-day or permanent Page Access Token.
"""
import sys
import requests

def exchange_for_permanent_page_token(app_id: str, app_secret: str, short_lived_token: str):
    print("=" * 60)
    print("Meta Graph API Permanent Page Token Generator")
    print("=" * 60)

    # Step 1: Exchange short-lived token for long-lived user token (60 days)
    print("\n[1/2] Exchanging short-lived token for 60-day long-lived user token...")
    exchange_url = "https://graph.facebook.com/v21.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token
    }
    r = requests.get(exchange_url, params=params, timeout=20)
    if r.status_code != 200:
        print(f"[-] Error exchanging token: {r.status_code}")
        print(r.text)
        return

    long_user_token = r.json().get("access_token")
    print("[+] Successfully generated 60-day Long-Lived User Token!")

    # Step 2: Fetch Page Access Token using the long-lived user token
    # Page access tokens obtained from a long-lived user token DO NOT EXPIRE!
    print("\n[2/2] Fetching permanent Page Access Token for your Facebook Page...")
    accounts_url = f"https://graph.facebook.com/v21.0/me/accounts?access_token={long_user_token}"
    r2 = requests.get(accounts_url, timeout=20)
    if r2.status_code != 200:
        print(f"[-] Error fetching accounts: {r2.status_code}")
        print(r2.text)
        return

    data = r2.json().get("data", [])
    if not data:
        print("[-] No Facebook Pages found for this account. Ensure pages_manage_posts and pages_show_list permissions are granted.")
        return

    print("\n" + "=" * 60)
    print("YOUR PERMANENT PAGE ACCESS TOKENS (NEVER EXPIRE):")
    print("=" * 60)
    for p in data:
        name = p.get("name")
        pid = p.get("id")
        ptoken = p.get("access_token")
        print(f"\nPage Name: {name} (ID: {pid})")
        print(f"FACEBOOK_PAGE_ACCESS_TOKEN={ptoken}")
        print(f"INSTAGRAM_ACCESS_TOKEN={ptoken}")
    print("\n" + "=" * 60)
    print("Copy the above token into your .env file on Q-Fi Cloud!")
    print("=" * 60)

if __name__ == "__main__":
    app_id = input("Enter Meta App ID (default: 954612557513274): ").strip() or "954612557513274"
    app_secret = input("Enter Meta App Secret (from App settings -> Basic): ").strip()
    if not app_secret:
        print("Meta App Secret is required.")
        sys.exit(1)
    short_token = input("Enter Short-Lived User Token from Graph API Explorer: ").strip()
    if not short_token:
        print("Short-lived token is required.")
        sys.exit(1)

    exchange_for_permanent_page_token(app_id, app_secret, short_token)
