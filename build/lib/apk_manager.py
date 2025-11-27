import os
import shutil
import json
import time
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

    def list_apks(self):
        """List all APK files with metadata."""
        # Sync with actual files
        existing_files = set(f for f in os.listdir(self.upload_dir) if f.endswith(".apk"))
        
        # Remove metadata for missing files
        for filename in list(self.metadata.keys()):
            if filename not in existing_files:
                del self.metadata[filename]
        self._save_metadata()

        # Build list
        result = []
        for filename in existing_files:
            meta = self.metadata.get(filename, {})
            result.append({
                "filename": filename,
                "custom_name": meta.get("custom_name", ""),
                "version_name": meta.get("version_name", "Unknown"),
                "version_code": meta.get("version_code", "Unknown"),
                "package_name": meta.get("package_name", "Unknown"),
                "upload_time": meta.get("upload_time", datetime.fromtimestamp(os.path.getmtime(os.path.join(self.upload_dir, filename))).strftime("%Y-%m-%d %H:%M:%S"))
            })
        
        # Sort by upload time desc
        result.sort(key=lambda x: x["upload_time"], reverse=True)
        return result

    async def save_apk(self, file: UploadFile, custom_filename: str = None, remark: str = None):
        """Save an uploaded APK file."""
        # If custom_filename provided, use it for filename (sanitize it)
        if custom_filename:
            # Ensure it ends with .apk
            if not custom_filename.endswith(".apk"):
                custom_filename += ".apk"
            filename = custom_filename
        else:
            filename = file.filename

        file_path = os.path.join(self.upload_dir, filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Parse APK info
            try:
                apk = APK(file_path)
                version_name = apk.version_name
                version_code = apk.version_code
                package_name = apk.package
            except Exception as e:
                logger.error(f"Failed to parse APK {filename}: {e}")
                version_name = "Parse Error"
                version_code = "Parse Error"
                package_name = "Unknown"

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
            logger.error(f"Error saving APK: {e}")
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
