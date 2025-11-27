import time
import adbutils
from loguru import logger
import os
from fastapi.concurrency import run_in_threadpool

class TestRunner:
    def __init__(self, device_manager, apk_manager):
        self.device_manager = device_manager
        self.apk_manager = apk_manager

    async def install_old_apk(self, serial, old_apk_name, apk_url=None):
        """Step 1: Install Old APK (Async wrapper)"""
        return await run_in_threadpool(self._install_old_sync, serial, old_apk_name, apk_url)

    def _install_old_sync(self, serial, old_apk_name, apk_url=None):
        platform = self.device_manager.get_platform(serial)
        if platform == "ios":
            return self._install_ios_sync(serial, old_apk_name, apk_url, uninstall_first=True)
            
        # Android Logic
        device = self.device_manager.get_device(serial)
        temp_file_path = None 

        try:
            old_apk_path, is_temp = self._get_apk_path(old_apk_name, apk_url)
            if is_temp:
                temp_file_path = old_apk_path

            if not self.device_manager.is_screen_on(device):
                return {"status": "failed", "reason": "Screen is OFF. Please turn it on."}
            if not self.device_manager.is_unlocked(device):
                return {"status": "failed", "reason": "Device is LOCKED. Please unlock it."}

            if not os.path.exists(old_apk_path):
                 return {"status": "failed", "reason": "Old APK file not found."}

            # Use ApkManager to parse
            vn, vc, package_name = self.apk_manager._parse_apk(old_apk_path)
            if package_name == "Unknown":
                 return {"status": "failed", "reason": "Could not parse package name from APK."}

            logger.info(f"Step 1: Installing Old APK {old_apk_name or apk_url} ({package_name} v{vn}) on {serial}")

            logger.info(f"Uninstalling {package_name}...")
            device.uninstall(package_name)
            time.sleep(1)

            logger.info("Installing Old APK...")
            device.install(old_apk_path, nolaunch=True, flags=['-r', '-t'])

            logger.info("Launching Old App...")
            self._launch_android_app(device, package_name)
            time.sleep(5)

            current = device.app_current()
            if current.package != package_name:
                 logger.warning("App might not have started correctly.")

            return {
                "status": "success",
                "message": f"Old APK Installed: {package_name} (v{vn})",
                "package_name": package_name,
                "version_name": vn,
                "version_code": vc
            }

        except Exception as e:
            logger.exception("Install Old APK failed")
            return {"status": "error", "message": str(e)}
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)


    async def install_new_apk(self, serial, new_apk_name=None, package_name=None, apk_url=None):
        """Step 2: Install New APK (Async wrapper)"""
        if not new_apk_name and not apk_url:
            return {"status": "failed", "reason": "Either new_apk_name or apk_url must be provided."}
        if not package_name:
            return {"status": "failed", "reason": "package_name is required for new APK installation."}
        return await run_in_threadpool(self._install_new_sync, serial, new_apk_name, package_name, apk_url)

    def _install_new_sync(self, serial, new_apk_name, package_name, apk_url):
        platform = self.device_manager.get_platform(serial)
        if platform == "ios":
            return self._install_ios_sync(serial, new_apk_name, apk_url, uninstall_first=False, expected_package=package_name)

        # Android Logic
        device = self.device_manager.get_device(serial)
        temp_file_path = None

        try:
            new_apk_path, is_temp = self._get_apk_path(new_apk_name, apk_url)
            if is_temp:
                temp_file_path = new_apk_path

            if not os.path.exists(new_apk_path):
                 return {"status": "failed", "reason": "New APK file not found."}

            # Verify package name
            new_pkg, new_ver, new_code = self.apk_manager._parse_apk(new_apk_path)
            if new_pkg != "Unknown" and new_pkg != package_name:
                return {"status": "failed", "reason": f"Package name mismatch! Old: {package_name}, New: {new_pkg}"}

            logger.info(f"Step 2: Updating to New APK {new_apk_name or apk_url} ({new_pkg} v{new_ver})")

            device.install(new_apk_path, nolaunch=True, flags=['-r'])
            
            logger.info("Launching New App...")
            self._launch_android_app(device, package_name)
            time.sleep(5)

            current = device.app_current()
            if current.package == package_name:
                return {
                    "status": "success", 
                    "message": f"Update Success! App is running. Version: {new_ver} ({new_code})"
                }
            else:
                return {
                    "status": "failed", 
                    "reason": f"App is not in foreground after update. Current: {current.package}"
                }

        except Exception as e:
            logger.exception("Install New APK failed")
            return {"status": "error", "message": str(e)}
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def _install_ios_sync(self, serial, filename, apk_url, uninstall_first=False, expected_package=None):
        device = self.device_manager.get_ios_device(serial)
        if not device:
             return {"status": "failed", "reason": "Device not found or not iOS"}
        
        temp_file_path = None
        try:
            file_path, is_temp = self._get_apk_path(filename, apk_url)
            if is_temp: temp_file_path = file_path
            
            if not os.path.exists(file_path):
                return {"status": "failed", "reason": "File not found"}
                
            # Parse IPA
            vn, vc, pkg = self.apk_manager._parse_ipa(file_path)
            if pkg == "Unknown":
                 return {"status": "failed", "reason": "Could not parse IPA"}
                 
            if expected_package and pkg != expected_package:
                 return {"status": "failed", "reason": f"Package mismatch: {pkg} != {expected_package}"}

            logger.info(f"Installing IPA {pkg} on {serial} (Uninstall first: {uninstall_first})...")
            
            if uninstall_first:
                try:
                    logger.info(f"Uninstalling {pkg}...")
                    device.app_uninstall(pkg)
                except:
                    pass
            
            logger.info("Installing IPA...")
            device.app_install(file_path)
            
            logger.info("Launching App...")
            try:
                device.app_start(pkg)
            except Exception as e:
                logger.warning(f"Failed to launch app: {e}")

            return {
                "status": "success",
                "message": f"Installed {pkg} (v{vn})",
                "package_name": pkg,
                "version_name": vn,
                "version_code": vc
            }
        except Exception as e:
            logger.exception("iOS Install failed")
            return {"status": "error", "message": str(e)}
        finally:
             if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def _get_apk_path(self, apk_name, apk_url):
        if apk_url:
            import requests
            import tempfile
            logger.info(f"Downloading file from {apk_url}...")
            try:
                # Determine suffix
                suffix = ".apk"
                if ".ipa" in apk_url.lower():
                    suffix = ".ipa"
                
                fd, temp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                with requests.get(apk_url, stream=True) as r:
                    r.raise_for_status()
                    with open(temp_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return temp_path, True
            except Exception as e:
                raise Exception(f"Failed to download file: {e}")
                raise Exception(f"Failed to download APK: {e}")
        elif apk_name:
            apk_path = os.path.join("apks", apk_name)
            return apk_path, False
        else:
            raise ValueError("Neither apk_name nor apk_url provided")

    def _launch_android_app(self, device, package_name):
        device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
