import requests
import re
import time
import os
from urllib.parse import unquote
from loguru import logger

class PgyerManager:
    def __init__(self, download_dir="apks"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def decode_data(self, a):
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

    def download_app(self, url):
        """
        Download app from Pgyer URL.
        Returns: {"status": "success/error", "message": "...", "filename": "..."}
        """
        try:
            # Determine if it's likely Android or iOS based on URL or try both
            # For simplicity, we'll try a generic approach or default to Android UA first, 
            # but Pgyer often serves different content based on UA.
            # Let's try to detect from the page content or just try one then the other.
            
            # We'll use a session
            session = requests.Session()
            
            # 1. Visit the page to get keys
            # Use a generic mobile UA to ensure we get the mobile install page
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.181 Mobile Safari/537.36",
                "Referer": url,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            session.headers.update(headers)
            
            logger.info(f"Visiting Pgyer URL: {url}")
            resp = session.get(url)
            resp.raise_for_status()
            text = resp.text

            # Extract keys
            aKey_match = re.search(r"aKey\s*=\s*'([a-zA-Z0-9]+)'", text)
            if not aKey_match:
                return {"status": "error", "message": "Could not find aKey. Page might be invalid or expired."}
            aKey = aKey_match.group(1)

            token_match = re.search(r"installToken\s*=\s*\"([a-zA-Z0-9]+)\"", text)
            install_token = token_match.group(1) if token_match else ""

            timeSign_match = re.search(r"timeSign\s*=\s*'([a-zA-Z0-9]+)'", text)
            timeSign = timeSign_match.group(1) if timeSign_match else ""

            authcode_match = re.search(r"var authcode\s*=\s*\"(\d+)\"", text)
            authcode = authcode_match.group(1) if authcode_match else "0"

            # Generate finalCode
            random_code = int(time.time() * 1000) % 1000000
            final_code = str(int(authcode) ^ random_code) + str(random_code).zfill(6)

            # Construct Install URL
            timestamp = int(time.time() * 1000)
            decoded_timeSign = self.decode_data(timeSign) if timeSign else ""
            
            install_api_url = f"https://www.pgyer.com/app/install/{aKey}?time={timestamp}"
            install_api_url += f"&finalCode={final_code}"
            if decoded_timeSign:
                install_api_url += f"&timeSign={decoded_timeSign}"
            if install_token:
                install_api_url += f"&installToken={install_token}"

            logger.info(f"Requesting Install API: {install_api_url}")
            
            # Request install URL (don't follow redirects yet to check for itms-services)
            install_resp = session.get(install_api_url, allow_redirects=False)
            
            download_url = ""
            location = install_resp.headers.get("Location", "")
            
            if location:
                if location.endswith(".apk") or ".apk?" in location:
                    download_url = location
                    logger.info(f"Found APK URL: {download_url}")
                elif "itms-services://" in location:
                    # Handle iOS Plist
                    logger.info("Found itms-services link, parsing plist...")
                    download_url = self.parse_plist(location)
                    if not download_url:
                        return {"status": "error", "message": "Failed to extract IPA URL from plist."}
                else:
                    # Follow redirect
                    download_url = location
            elif install_resp.status_code == 200:
                # Check JSON
                try:
                    json_resp = install_resp.json()
                    if json_resp.get("code") == 0 and "data" in json_resp:
                        download_url = json_resp['data'].get('downloadURL')
                        if "itms-services://" in download_url:
                             download_url = self.parse_plist(download_url)
                except:
                    pass

            if not download_url:
                 return {"status": "error", "message": "Could not find download URL."}

            # Download the file
            return self.download_file(download_url)

        except Exception as e:
            logger.error(f"Pgyer download failed: {e}")
            return {"status": "error", "message": str(e)}

    def parse_plist(self, itms_url):
        try:
            match = re.search(r"url=([^&]+)", itms_url)
            if not match:
                return None
            plist_url = unquote(match.group(1))
            plist_url = plist_url.replace("install//s.plist", "install/s.plist")
            
            # Fetch plist
            # Use itunesstored UA
            headers = {"User-Agent": "itunesstored/1.0"}
            resp = requests.get(plist_url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch plist: {resp.status_code}")
                return None
            
            ipa_match = re.search(r"<string>(https?://.*?\.ipa)</string>", resp.text)
            if ipa_match:
                return ipa_match.group(1)
            return None
        except Exception as e:
            logger.error(f"Error parsing plist: {e}")
            return None

    def download_file(self, url):
        try:
            local_filename = url.split('/')[-1].split('?')[0]
            if not local_filename:
                local_filename = f"pgyer_app_{int(time.time())}.apk" # Default fallback
            
            # Ensure extension is correct if possible
            if ".ipa" in url and not local_filename.endswith(".ipa"):
                local_filename += ".ipa"
            elif ".apk" in url and not local_filename.endswith(".apk"):
                local_filename += ".apk"

            save_path = os.path.join(self.download_dir, local_filename)
            
            logger.info(f"Downloading to {save_path}...")
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            logger.info("Download complete.")
            return {"status": "success", "message": "Download successful", "filename": local_filename}
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return {"status": "error", "message": f"File download failed: {e}"}
