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

def spoof_pgyer_android():
    url = "https://www.pgyer.com/2CzX"
    # Android User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        "Referer": "https://www.pgyer.com/2CzX",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
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
    random_code = int(time.time() * 1000) % 1000000
    final_code = str(int(authcode) ^ random_code) + str(random_code).zfill(6)
    print(f"[-] Generated finalCode: {final_code}")

    # Construct Install URL
    timestamp = int(time.time() * 1000)
    decoded_timeSign = decode_data(timeSign) if timeSign else ""
    
    install_url = f"https://www.pgyer.com/app/install/{aKey}?time={timestamp}"
    install_url += f"&finalCode={final_code}"
    if decoded_timeSign:
        install_url += f"&timeSign={decoded_timeSign}"
    if install_token:
        install_url += f"&installToken={install_token}"
    
    print(f"[-] Requesting Install URL: {install_url}")
    try:
        # allow_redirects=False to see where it sends us
        install_resp = session.get(install_url, allow_redirects=False)
    except Exception as e:
        print(f"[!] Failed to request install: {e}")
        return

    print(f"[-] Install Response Code: {install_resp.status_code}")
    location = install_resp.headers.get("Location", "")
    print(f"[-] Redirect Location: {location}")

    if location.endswith(".apk") or ".apk?" in location:
        print(f"[+] FOUND APK URL: {location}")
    elif install_resp.status_code == 200:
        # Sometimes it might return JSON or HTML if not redirecting
        print("[-] Response content (first 500 chars):")
        print(install_resp.text[:500])
        # Check for JSON response with download URL
        try:
            json_resp = install_resp.json()
            if json_resp.get("code") == 0 and "data" in json_resp:
                 print(f"[+] FOUND APK URL in JSON: {json_resp['data'].get('downloadURL')}")
        except:
            pass
    else:
        print("[!] Unexpected response.")

if __name__ == "__main__":
    spoof_pgyer_android()
