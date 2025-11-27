import os
import shutil
import json
import time
import zipfile
import plistlib
from datetime import datetime
from fastapi import UploadFile
from loguru import logger
from pyaxmlparser import APK

class ApkManager:
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        self.metadata_file = os.path.join(upload_dir, "metadata.json")
        os.makedirs(self.upload_dir, exist_ok=True)
        self.metadata = self._load_metadata()

    def _load_metadata(self):
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_metadata(self):
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=4)

    def _parse_ipa(self, file_path):
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                # Find Info.plist
                plist_path = None
                for name in z.namelist():
                    if name.startswith('Payload/') and name.endswith('.app/Info.plist'):
                        plist_path = name
                        break
                
                if not plist_path:
                    return "Unknown", "Unknown", "Unknown"

                with z.open(plist_path) as f:
                    plist = plistlib.load(f)
                    version_name = plist.get('CFBundleShortVersionString', 'Unknown')
                    version_code = plist.get('CFBundleVersion', 'Unknown')
                    package_name = plist.get('CFBundleIdentifier', 'Unknown')
                    return version_name, version_code, package_name
        except Exception as e:
            logger.error(f"Error parsing IPA {file_path}: {e}")
            return "Parse Error", "Parse Error", "Unknown"

    def list_apks(self):
        """List all APK and IPA files with metadata."""
        # Sync with actual files
        all_files = os.listdir(self.upload_dir)
        existing_apks = set(f for f in all_files if f.endswith(".apk"))
        existing_ipas = set(f for f in all_files if f.endswith(".ipa"))
        existing_files = existing_apks.union(existing_ipas)
        
        # Remove metadata for missing files
        for filename in list(self.metadata.keys()):
            if filename not in existing_files:
                del self.metadata[filename]
        self._save_metadata()

        # Build lists
        android_list = []
        ios_list = []
        
        for filename in existing_files:
            meta = self.metadata.get(filename, {})
            # Try to parse if unknown (auto-repair metadata)
            if meta.get("version_name") == "Unknown" or meta.get("version_name") == "IPA File":
                 if filename.endswith(".ipa"):
                     vn, vc, pkg = self._parse_ipa(os.path.join(self.upload_dir, filename))
                     if vn != "Unknown" and vn != "Parse Error":
                         meta["version_name"] = str(vn)
                         meta["version_code"] = str(vc)
                         meta["package_name"] = pkg
                         self.metadata[filename] = meta
                         self._save_metadata()

            file_info = {
                "filename": filename,
                "custom_name": meta.get("custom_name", ""),
                "version_name": meta.get("version_name", "Unknown"),
                "version_code": meta.get("version_code", "Unknown"),
                "package_name": meta.get("package_name", "Unknown"),
                "upload_time": meta.get("upload_time", datetime.fromtimestamp(os.path.getmtime(os.path.join(self.upload_dir, filename))).strftime("%Y-%m-%d %H:%M:%S"))
            }
            
            if filename.endswith(".apk"):
                android_list.append(file_info)
            elif filename.endswith(".ipa"):
                ios_list.append(file_info)
        
        # Sort by upload time desc
        android_list.sort(key=lambda x: x["upload_time"], reverse=True)
        ios_list.sort(key=lambda x: x["upload_time"], reverse=True)
        
        return {
            "android": android_list,
            "ios": ios_list
        }

    async def save_apk(self, file: UploadFile, custom_filename: str = None, remark: str = None):
        """Save an uploaded APK or IPA file."""
        original_filename = file.filename
        is_ipa = original_filename.lower().endswith(".ipa")
        
        # If custom_filename provided, use it for filename (sanitize it)
        if custom_filename:
            filename = custom_filename
            # Ensure extension matches original type if not provided
            if is_ipa and not filename.lower().endswith(".ipa"):
                filename += ".ipa"
            elif not is_ipa and not filename.lower().endswith(".apk"):
                filename += ".apk"
        else:
            filename = original_filename

        file_path = os.path.join(self.upload_dir, filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            version_name = "Unknown"
            version_code = "Unknown"
            package_name = "Unknown"

            # Parse APK/IPA info
            if filename.lower().endswith(".apk"):
                try:
                    apk = APK(file_path)
                    version_name = apk.version_name
                    version_code = apk.version_code
                    package_name = apk.package
                except Exception as e:
                    logger.error(f"Failed to parse APK {filename}: {e}")
                    version_name = "Parse Error"
            elif filename.lower().endswith(".ipa"):
                version_name, version_code, package_name = self._parse_ipa(file_path)

            self.metadata[filename] = {
                "custom_name": remark if remark else "", # Use remark as custom_name (display name)
                "version_name": str(version_name),
                "version_code": str(version_code),
                "package_name": package_name,
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_metadata()

            return {"filename": filename, "status": "success"}
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return {"status": "error", "message": str(e)}

    def delete_apk(self, filename):
        """Delete an APK file and its metadata."""
        file_path = os.path.join(self.upload_dir, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            
            if filename in self.metadata:
                del self.metadata[filename]
                self._save_metadata()
            
            return {"status": "success", "filename": filename}
        except Exception as e:
            logger.error(f"Error deleting APK: {e}")
            return {"error": str(e)}

    def get_apk_path(self, filename):
        """Get the full path of an APK file."""
        return os.path.join(self.upload_dir, filename)
