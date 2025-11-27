import adbutils
from loguru import logger
try:
    import tidevice
except ImportError:
    tidevice = None
    logger.warning("tidevice not installed, iOS support disabled")

class DeviceManager:
    def list_devices(self):
        """List all connected devices with their status."""
        devices = []
        
        # Android Devices
        try:
            for d in adbutils.adb.device_list():
                model = d.prop.get("ro.product.model", "Unknown")
                product = d.prop.get("ro.product.name", "Unknown")
                device_name = d.prop.get("ro.product.device", "Unknown")
                
                info = {
                    "serial": d.serial,
                    "state": d.get_state(),
                    "model": model,
                    "product": product,
                    "device": device_name,
                    "screen_on": self.is_screen_on(d),
                    "unlocked": self.is_unlocked(d),
                    "platform": "android"
                }
                devices.append(info)
        except Exception as e:
            logger.error(f"Error listing Android devices: {e}")

        # iOS Devices
        if tidevice:
            try:
                t = tidevice.Usbmux()
                for d in t.device_list():
                    # d is DeviceInfo(udid='...', name='...', ...)
                    # We need to get more info if possible, but basic list is fine
                    # tidevice doesn't give much info in device_list() other than udid and connection type
                    # We can try to get device name
                    try:
                        dev = tidevice.Device(d.udid)
                        name = dev.name
                        model = dev.get_value(key="ProductType") # e.g. iPhone10,3
                        # Check if locked? tidevice doesn't easily give lock state without pairing/lockdown
                        # We'll assume ready for now or add basic check
                    except:
                        name = "iOS Device"
                        model = "Unknown"

                    info = {
                        "serial": d.udid,
                        "state": "device", # Assume device if listed
                        "model": name, # Use name as model for display
                        "product": model,
                        "device": "iPhone",
                        "screen_on": True, # Hard to detect without more permissions
                        "unlocked": True, # Hard to detect
                        "platform": "ios"
                    }
                    devices.append(info)
            except Exception as e:
                logger.error(f"Error listing iOS devices: {e}")

        return devices

    def get_device(self, serial):
        """Get a specific device by serial."""
        return adbutils.adb.device(serial=serial)

    def is_screen_on(self, device):
        """Check if the device screen is on."""
        try:
            # Method 1: dumpsys power (mWakefulness=Awake)
            output = device.shell("dumpsys power")
            if "mWakefulness=Awake" in output:
                return True
            
            # Method 2: dumpsys deviceidle (mScreenOn=true)
            output2 = device.shell("dumpsys deviceidle")
            if "mScreenOn=true" in output2:
                return True

            # Method 3: dumpsys display (Display Power: state=ON)
            output3 = device.shell("dumpsys display")
            if "state=ON" in output3:
                return True

            logger.debug(f"Screen check failed for {device.serial}. Power output len: {len(output)}")
            return False
        except Exception as e:
            logger.error(f"Error checking screen state: {e}")
            # Fallback to True to avoid blocking if check fails
            return True

    def is_unlocked(self, device):
        """Check if the device is unlocked."""
        try:
            # Method 1: dumpsys window (mShowingLockscreen=false)
            output = device.shell("dumpsys window policy")
            if "mShowingLockscreen=false" in output:
                return True
            
            # Method 2: Check mDreamingLockscreen=false
            if "mDreamingLockscreen=false" in output:
                return True

            # Method 3: dumpsys trust (mDeviceLocked=false) - Android 6+
            output_trust = device.shell("dumpsys trust")
            if "mDeviceLocked=false" in output_trust:
                return True

            # Method 4: Check if keyguard is showing via dumpsys activity
            # mKeyguardShowing=false
            output_activity = device.shell("dumpsys activity activities")
            if "mKeyguardShowing=false" in output_activity:
                return True

            logger.debug(f"Lock check failed for {device.serial}. Window policy output len: {len(output)}")
            # If we can't determine, but screen is on, maybe we should be lenient?
            # But user wants to ensure it's usable.
            # Let's try one more: input_method mInteractive=true usually implies unlocked/usable
            return False
        except Exception as e:
            logger.error(f"Error checking lock state: {e}")
            return True # Fallback to True
    def get_platform(self, serial):
        """Determine platform of the device."""
        # Check Android
        try:
            for d in adbutils.adb.device_list():
                if d.serial == serial:
                    return "android"
        except:
            pass
        
        # Check iOS
        if tidevice:
            try:
                t = tidevice.Usbmux()
                for d in t.device_list():
                    if d.udid == serial:
                        return "ios"
            except:
                pass
        return "unknown"

    def get_ios_device(self, serial):
        """Get tidevice Device object."""
        if tidevice:
            return tidevice.Device(serial)
        return None
