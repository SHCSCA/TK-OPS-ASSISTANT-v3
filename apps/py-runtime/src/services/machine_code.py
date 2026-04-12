from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import winreg


class MachineCodeError(RuntimeError):
    pass


class MachineCodeService:
    def get_machine_code(self) -> str:
        override = os.getenv("TK_OPS_MACHINE_CODE_OVERRIDE", "").strip()
        if override:
            return override.upper()

        fingerprint_parts = [
            self._read_machine_guid(),
            self._read_device_uuid(),
            self._read_system_drive_serial(),
        ]
        normalized = "|".join(part.strip().upper() for part in fingerprint_parts if part)
        if not normalized:
            raise MachineCodeError("无法生成机器码，请联系技术支持")

        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()
        groups = [digest[index : index + 5] for index in range(0, 25, 5)]
        return f"TKOPS-{'-'.join(groups)}"

    def _read_machine_guid(self) -> str:
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
        except OSError as exc:
            raise MachineCodeError("无法读取本机注册信息，无法生成机器码") from exc

        return str(value)

    def _read_device_uuid(self) -> str:
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_ComputerSystemProduct).UUID",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=True,
                text=True,
                encoding="utf-8",
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise MachineCodeError("无法读取设备标识，无法生成机器码") from exc

        value = result.stdout.strip()
        if not value:
            raise MachineCodeError("设备标识为空，无法生成机器码")
        return value

    def _read_system_drive_serial(self) -> str:
        drive = os.getenv("SystemDrive", "C:").strip() or "C:"
        serial_number = ctypes.c_uint32()
        maximum_component_length = ctypes.c_uint32()
        file_system_flags = ctypes.c_uint32()
        success = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(f"{drive}\\"),
            None,
            0,
            ctypes.byref(serial_number),
            ctypes.byref(maximum_component_length),
            ctypes.byref(file_system_flags),
            None,
            0,
        )
        if not success:
            raise MachineCodeError("无法读取系统盘序列号，无法生成机器码")

        return f"{serial_number.value:08X}"
