import os.path

import cv2
import numpy
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from numpy import ndarray


class ADB:
    def __init__(self):
        self._tft_package_name = "com.riotgames.league.teamfighttactics"
        self._tft_activity_name = "com.riotgames.leagueoflegends.RiotNativeActivity"
        self._load_rsa_signer()
        self._connect_to_device()

    def _load_rsa_signer(self) -> None:
        if not os.path.isfile("adb_key"):
            keygen("adb_key")

        with open("adb_key") as adb_key_file:
            private_key = adb_key_file.read()

        with open("adb_key.pub") as adb_key_file:
            public_key = adb_key_file.read()

        self._rsa_signer = PythonRSASigner(pub=public_key, priv=private_key)

    def _connect_to_device(self):
        # TODO Make port configurable (GUI or config.yml) or add port discovery
        device = AdbDeviceTcp(host='127.0.0.1', port=5555, default_transport_timeout_s=9)
        try:
            if device.connect(rsa_keys=[self._rsa_signer], auth_timeout_s=0.1):
                self._device = device
                return
        except OSError:
            self._device = None

    def is_connected(self) -> bool:
        """
        Get if this adb instance is connected.

        Returns:
             True if a device exists and is available. Otherwise, False.
        """
        return self._device is not None and self._device.available

    def get_screen_size(self) -> tuple[int, int] | None:
        """
        Get the screen size.

        Returns:
             A tuple containing the width and height.
        """
        sizes = self._device.shell("wm size | awk '{print $3}'").replace("\n", "").split("x")
        return int(sizes[0]), int(sizes[1])

    def get_memory(self) -> int | None:
        """
        Gets the memory of the device.

        Returns:
            The memory of the device in kB.
        """
        return int(self._device.shell("grep MemTotal /proc/meminfo | awk '{print $2}'"))

    def get_screen(self) -> ndarray | None:
        """
        Gets a ndarray which contains the values of the gray-scaled pixels
        currently on the screen.

        Returns:
            The ndarray containing the gray-scaled pixels.
        """
        image_bytes_str = self._device.shell("screencap -p", decode=False)
        raw_image = numpy.frombuffer(image_bytes_str, dtype=numpy.uint8)
        return cv2.imdecode(raw_image, cv2.IMREAD_GRAYSCALE)

    def click(self, x: int, y: int):
        """
        Tap a specific coordinate.

        Args:
            x: The x coordinate where to tap.
            y: The y coordinate where to tap.
        """
        self._device.shell(f"input tap {x} {y}")

    def go_back(self):
        """
        Utility method to fulfill the action which goes back one screen,
        however the current app might interpret that.
        """
        self._device.shell("input tap keyevent KEYCODE_BACK")

    def is_tft_active(self) -> bool:
        return self._device.shell(
            "dumpsys window | grep -E 'mCurrentFocus' | awk '{print $3}'"
        ).split("/")[0].replace("\n", "") == self._tft_package_name

    def start_tft_app(self):
        self._device.shell(f"am start -n {self._tft_package_name}/{self._tft_activity_name}")
