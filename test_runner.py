import time
import adbutils
from loguru import logger
import os

class TestRunner:
    def __init__(self, device_manager):
        self.device_manager = device_manager

    async def install_old_apk(self, serial, old_apk_name):
        """
        Step 1: Install Old APK (Async wrapper)
        """
        from fastapi.concurrency import run_in_threadpool
        return await run_in_threadpool(self._install_old_sync, serial, old_apk_name)

    def _install_old_sync(self, serial, old_apk_name, apk_url=None):
        """
        Synchronous implementation of Step 1
        """
        device = self.device_manager.get_device(serial)
        temp_file_path = None # To store path of temporary downloaded APK

        try:
            old_apk_path, is_temp = self._get_apk_path(old_apk_name, apk_url)
            if is_temp:
                temp_file_path = old_apk_path

            # 1. Check Device State
            if not self.device_manager.is_screen_on(device):
                return {"status": "failed", "reason": "Screen is OFF. Please turn it on."}
            if not self.device_manager.is_unlocked(device):
                return {"status": "failed", "reason": "Device is LOCKED. Please unlock it."}

            if not os.path.exists(old_apk_path):
                 return {"status": "failed", "reason": "Old APK file not found."}

            try:
                package_name, version_name, version_code = self._get_apk_info(old_apk_path)
                if not package_name:
                     return {"status": "failed", "reason": "Could not parse package name from APK."}

                logger.info(f"Step 1: Installing Old APK {old_apk_name or apk_url} ({package_name} v{version_name}) on {serial}")

                # Uninstall first
                logger.info(f"Uninstalling {package_name}...")
                device.uninstall(package_name)
                time.sleep(1)

                # Install Old APK
                logger.info("Installing Old APK...")
                # Use -r to replace if exists (though we uninstalled), and -t to allow test APKs just in case.
                # Explicitly setting flags to control behavior.
                device.install(old_apk_path, nolaunch=True, flags=['-r', '-t'])

                # Launch
                logger.info("Launching Old App...")
                self._launch_app(device, package_name)
                time.sleep(5)

                # Verify
                current = device.app_current()
                if current.package != package_name:
                     logger.warning("App might not have started correctly.")

                return {
                    "status": "success",
                    "message": f"Old APK Installed: {package_name} (v{version_name})",
                    "package_name": package_name,
                    "version_name": version_name,
                    "version_code": version_code
                }

            except Exception as e:
                logger.exception("Install Old APK failed")
                return {"status": "error", "message": str(e)}
        except Exception as e:
             return {"status": "error", "message": f"Setup failed: {str(e)}"}
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                logger.info(f"Cleaning up temporary APK file: {temp_file_path}")
                os.remove(temp_file_path)


    async def install_new_apk(self, serial, new_apk_name=None, package_name=None, apk_url=None):
        """
        Step 2: Install New APK (Async wrapper)
        """
        if not new_apk_name and not apk_url:
            return {"status": "failed", "reason": "Either new_apk_name or apk_url must be provided."}
        if not package_name:
            return {"status": "failed", "reason": "package_name is required for new APK installation."}
        return await run_in_threadpool(self._install_new_sync, serial, new_apk_name, package_name, apk_url)

    def _install_new_sync(self, serial, new_apk_name, package_name, apk_url):
        """
        Synchronous implementation of Step 2
        """
        device = self.device_manager.get_device(serial)
        temp_file_path = None

        try:
            new_apk_path, is_temp = self._get_apk_path(new_apk_name, apk_url)
            if is_temp:
                temp_file_path = new_apk_path

            if not os.path.exists(new_apk_path):
                 return {"status": "failed", "reason": "New APK file not found."}

            # Verify new apk package name matches old one?
            new_pkg, new_ver, new_code = self._get_apk_info(new_apk_path)
            if new_pkg and new_pkg != package_name:
                return {"status": "failed", "reason": f"Package name mismatch! Old: {package_name}, New: {new_pkg}"}

            logger.info(f"Step 2: Updating to New APK {new_apk_name or apk_url} ({new_pkg} v{new_ver})")

            # Install Update
            device.install(new_apk_path, nolaunch=True, flags=['-r'])
            
            # Launch
            logger.info("Launching New App...")
            self._launch_app(device, package_name)
            time.sleep(5)

            # Verify
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
                logger.info(f"Cleaning up temporary APK file: {temp_file_path}")
                os.remove(temp_file_path)

    def _get_apk_info(self, apk_path):
        try:
            from pyaxmlparser import APK
            apk = APK(apk_path)
            return apk.package, apk.version_name, apk.version_code
        except Exception as e:
            logger.error(f"Failed to parse APK with pyaxmlparser: {e}")
            return None, None, None

    def _launch_app(self, device, package_name):
        device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
