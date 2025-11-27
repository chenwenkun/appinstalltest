import requests
import re
import time
import random
from urllib.parse import unquote

def decode_data(a):
    # JS: for (var b = "", c = "", d = 0; 12 > d; d++) b += String.fromCharCode(parseInt(a.substring(2 * d, 2 * d + 2), 16)).toLowerCase();
    b = ""
    for d in range(12):
        try:
            hex_val = a[2*d : 2*d+2]
            b += chr(int(hex_val, 16)).lower()
        except:
            pass
    
    # JS: for (var d = 0; d < b.length; d++) c += b.charCodeAt(d).toString(16).padStart(2, "0");
    c = ""
    for char in b:
        c += hex(ord(char))[2:].zfill(2)
    return c

def spoof_pgyer():
    url = "https://www.pgyer.com/2XDm6i"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Referer": "https://www.pgyer.com/2XDm6i",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9"
    }

    session = requests.Session()
    session.headers.update(headers)

    print(f"[-] Visiting {url}...")
    try:
        resp = session.get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f"[!] Failed to visit page: {e}")
        return

    text = resp.text

    # Extract aKey
    aKey_match = re.search(r"aKey\s*=\s*'([a-zA-Z0-9]+)'", text)
    if not aKey_match:
        print("[!] Could not find aKey")
        return
    aKey = aKey_match.group(1)
    print(f"[-] Found aKey: {aKey}")

    # Extract installToken
    token_match = re.search(r"installToken\s*=\s*\"([a-zA-Z0-9]+)\"", text)
    install_token = token_match.group(1) if token_match else ""
    print(f"[-] Found installToken: {install_token}")

    # Extract timeSign
    timeSign_match = re.search(r"timeSign\s*=\s*'([a-zA-Z0-9]+)'", text)
    timeSign = timeSign_match.group(1) if timeSign_match else ""
    print(f"[-] Found timeSign: {timeSign}")

    # Extract authcode for finalCode
    authcode_match = re.search(r"var authcode\s*=\s*\"(\d+)\"", text)
    authcode = authcode_match.group(1) if authcode_match else "0"
    print(f"[-] Found authcode: {authcode}")

    # Generate finalCode
    # var randomCode = new Date().getTime() % 1E6;
    # var finalCode = (parseInt(authcode) ^ randomCode).toString() + randomCode.toString().padStart(6, '0');
    random_code = int(time.time() * 1000) % 1000000
    final_code = str(int(authcode) ^ random_code) + str(random_code).zfill(6)
    print(f"[-] Generated finalCode: {final_code}")

    # Construct Install URL (GET request based on JS)
    # url = httpDomain + "/app/install/" + aKey + ...
    # b += "?time=" + (new Date).getTime()
    # b += "&finalCode=" + finalCode
    # b += "&timeSign=" + decodeData(timeSign)
    # b += "&installToken=" + installToken (if autoInstallSuccess or ad displayed)
    
    timestamp = int(time.time() * 1000)
    decoded_timeSign = decode_data(timeSign) if timeSign else ""
    
    install_url = f"https://www.pgyer.com/app/install/{aKey}?time={timestamp}"
    install_url += f"&finalCode={final_code}"
    if decoded_timeSign:
        install_url += f"&timeSign={decoded_timeSign}"
    if install_token:
        install_url += f"&installToken={install_token}"
    
    # Add other potential params from JS if needed, but these seem to be the main ones
    # traffic=true, etc.

    print(f"[-] Requesting Install URL: {install_url}")
    try:
        # allow_redirects=False to catch the itms-services link
        install_resp = session.get(install_url, allow_redirects=False)
    except Exception as e:
        print(f"[!] Failed to request install: {e}")
        return

    print(f"[-] Install Response Code: {install_resp.status_code}")
    print(f"[-] Install Response Cookies: {install_resp.cookies.get_dict()}")
    location = install_resp.headers.get("Location", "")
    print(f"[-] Redirect Location: {location}")

    if "itms-services://" in location:
        match = re.search(r"url=([^&]+)", location)
        if match:
            plist_url_encoded = match.group(1)
            plist_url = unquote(plist_url_encoded)
            # Fix double slash if present
            plist_url = plist_url.replace("install//s.plist", "install/s.plist")
            print(f"[-] Found Plist URL: {plist_url}")

            print(f"[-] Fetching Plist with itunesstored UA...")
            try:
                # The OS fetches the plist, so it uses a different UA and typically NO cookies from the browser session
                # But we can try both. First, try with empty cookies and itunesstored UA.
                plist_headers = {
                    "User-Agent": "itunesstored/1.0",
                    "Accept": "*/*",
                    "Connection": "keep-alive"
                }
                # Create a new session for the plist fetch to simulate OS behavior (no shared cookies)
                plist_session = requests.Session()
                plist_session.headers.update(plist_headers)
                
                plist_resp = plist_session.get(plist_url)
                if plist_resp.status_code == 200 and "xml" in plist_resp.headers.get("Content-Type", ""):
                    print("[-] Plist content fetched successfully.")
                    ipa_match = re.search(r"<string>(https?://.*?\.ipa)</string>", plist_resp.text)
                    if ipa_match:
                        print(f"[+] FOUND IPA URL: {ipa_match.group(1)}")
                        return
                    else:
                        print("[!] Could not find .ipa URL in plist content.")
                        print(plist_resp.text)
                else:
                    print(f"[!] Failed to fetch plist with clean session. Status: {plist_resp.status_code}")
                    # Retry with original session (cookies) but new UA
                    print("[-] Retrying with session cookies...")
                    session.headers.update({"User-Agent": "itunesstored/1.0"})
                    plist_resp = session.get(plist_url)
                    if plist_resp.status_code == 200:
                         print("[-] Plist content fetched successfully (with cookies).")
                         ipa_match = re.search(r"<string>(https?://.*?\.ipa)</string>", plist_resp.text)
                         if ipa_match:
                            print(f"[+] FOUND IPA URL: {ipa_match.group(1)}")
                         else:
                            print("[!] Could not find .ipa URL in plist content.")
                    else:
                        print(f"[!] Failed with cookies too. Status: {plist_resp.status_code}")
                        print(plist_resp.text[:500])

            except Exception as e:
                print(f"[!] Error fetching plist: {e}")
        else:
            print("[!] Could not extract plist URL from itms-services link")
    else:
        print("[!] Did not get itms-services redirect.")
        print(install_resp.text[:500])

if __name__ == "__main__":
    spoof_pgyer()
