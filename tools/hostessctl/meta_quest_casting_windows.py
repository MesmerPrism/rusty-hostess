"""Windows effects for the bounded Meta Quest Casting adapter.

This module treats Meta Quest Developer Hub and Casting.exe as third-party,
locally installed software.  It discovers and observes those programs, but it
does not install, patch, download, or redistribute them.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import winreg
from pathlib import Path
from typing import Any


DEFAULT_MQDH_ROOT = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / (
    "Meta Quest Developer Hub"
)
MQDH_EXE_NAME = "Meta Quest Developer Hub.exe"
CASTING_RELATIVE_PATH = Path("resources") / "bin" / "Casting" / "Casting.exe"
ADB_RELATIVE_PATH = Path("resources") / "bin" / "adb.exe"
ADB_API_RELATIVE_PATH = Path("resources") / "bin" / "AdbWinApi.dll"
ADB_USB_API_RELATIVE_PATH = Path("resources") / "bin" / "AdbWinUsbApi.dll"


def _powershell_json(script: str, *, timeout_seconds: float = 15.0) -> Any:
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    powershell_exe = (
        system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    )
    child_environment = dict(os.environ)
    child_environment["PSModulePath"] = os.pathsep.join(
        (
            str(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WindowsPowerShell" / "Modules"),
            str(system_root / "System32" / "WindowsPowerShell" / "v1.0" / "Modules"),
        )
    )
    completed = subprocess.run(
        [
            str(powershell_exe),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=child_environment,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"PowerShell observation failed: {detail}")
    payload = completed.stdout.strip()
    return json.loads(payload) if payload else None


def _ps_literal(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _root_from_uninstall_string(uninstall_string: str) -> Path | None:
    value = uninstall_string.strip()
    if not value:
        return None
    if value.startswith('"'):
        closing = value.find('"', 1)
        executable = value[1:closing] if closing > 1 else ""
    else:
        executable = value.split(" ", 1)[0]
    if not executable:
        return None
    candidate = Path(executable).parent
    return candidate if candidate.name == "Meta Quest Developer Hub" else None


def discover_mqdh_root() -> Path:
    access_modes = (
        winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
    )
    roots = (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)
    uninstall_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    for registry_root in roots:
        for access in access_modes:
            try:
                with winreg.OpenKey(registry_root, uninstall_path, 0, access) as parent:
                    for index in range(winreg.QueryInfoKey(parent)[0]):
                        try:
                            subkey_name = winreg.EnumKey(parent, index)
                            with winreg.OpenKey(parent, subkey_name) as subkey:
                                display_name = str(
                                    winreg.QueryValueEx(subkey, "DisplayName")[0]
                                )
                                if "Meta Quest Developer Hub" not in display_name:
                                    continue
                                try:
                                    install_location = str(
                                        winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                    ).strip()
                                except FileNotFoundError:
                                    install_location = ""
                                if install_location:
                                    return Path(install_location)
                                try:
                                    uninstall_string = str(
                                        winreg.QueryValueEx(subkey, "UninstallString")[0]
                                    )
                                except FileNotFoundError:
                                    uninstall_string = ""
                                candidate = _root_from_uninstall_string(
                                    uninstall_string
                                )
                                if candidate is not None:
                                    return candidate
                        except (FileNotFoundError, OSError):
                            continue
            except (FileNotFoundError, OSError):
                continue
    return DEFAULT_MQDH_ROOT


class WindowsMetaQuestCastingAdapter:
    """Concrete Windows observation and process-control adapter."""

    def discover_installation(self) -> dict[str, Any]:
        root = Path(os.path.abspath(str(discover_mqdh_root())))
        mqdh_exe = root / MQDH_EXE_NAME
        casting_exe = root / CASTING_RELATIVE_PATH
        adb_exe = root / ADB_RELATIVE_PATH
        adb_api = root / ADB_API_RELATIVE_PATH
        adb_usb_api = root / ADB_USB_API_RELATIVE_PATH
        observation: dict[str, Any] = {
            "root": str(root),
            "canonical_install_root": (
                os.path.normcase(str(root))
                == os.path.normcase(os.path.abspath(str(DEFAULT_MQDH_ROOT)))
            ),
            "mqdh_exe": str(mqdh_exe),
            "casting_exe": str(casting_exe),
            "adb_exe": str(adb_exe),
            "cache_dir": str(
                Path(os.environ["APPDATA"]) / "odh" / "casting"
            ),
            "files_present": all(
                path.is_file()
                for path in (
                    mqdh_exe,
                    casting_exe,
                    adb_exe,
                    adb_api,
                    adb_usb_api,
                )
            ),
            "casting_is_reparse_point": False,
            "adb_is_reparse_point": False,
            "adb_dependency_is_reparse_point": False,
            "install_path_has_reparse_component": False,
        }
        if not observation["files_present"]:
            observation.update(
                {
                    "mqdh_version": "",
                    "mqdh_sha256": "",
                    "mqdh_signature_status": "Missing",
                    "mqdh_signer_subject": "",
                    "mqdh_signer_thumbprint": "",
                    "casting_sha256": "",
                    "signature_status": "Missing",
                    "signer_subject": "",
                    "signer_thumbprint": "",
                    "adb_sha256": "",
                    "adb_api_sha256": "",
                    "adb_usb_api_sha256": "",
                    "adb_signature_status": "Missing",
                    "adb_api_signature_status": "Missing",
                    "adb_usb_api_signature_status": "Missing",
                    "adb_signer_subject": "",
                    "adb_signer_thumbprint": "",
                    "adb_api_signer_thumbprint": "",
                    "adb_usb_api_signer_thumbprint": "",
                }
            )
            return observation

        script = (
            "$ErrorActionPreference='Stop';"
            "Import-Module Microsoft.PowerShell.Security -ErrorAction Stop;"
            "function Test-ReparseAncestry([string]$Path){"
            "$current=Get-Item -LiteralPath $Path -Force;"
            "while($null -ne $current){"
            "if($current.Attributes -band [IO.FileAttributes]::ReparsePoint){"
            "return $true};"
            "$current=$current.Parent};"
            "return $false};"
            f"$mqdh=Get-Item -LiteralPath {_ps_literal(mqdh_exe)};"
            f"$casting=Get-Item -LiteralPath {_ps_literal(casting_exe)};"
            f"$adb=Get-Item -LiteralPath {_ps_literal(adb_exe)};"
            f"$adbApi=Get-Item -LiteralPath {_ps_literal(adb_api)};"
            f"$adbUsbApi=Get-Item -LiteralPath {_ps_literal(adb_usb_api)};"
            f"$mqdhSig=Get-AuthenticodeSignature -LiteralPath {_ps_literal(mqdh_exe)};"
            f"$sig=Get-AuthenticodeSignature -LiteralPath {_ps_literal(casting_exe)};"
            f"$adbSig=Get-AuthenticodeSignature -LiteralPath {_ps_literal(adb_exe)};"
            f"$adbApiSig=Get-AuthenticodeSignature -LiteralPath {_ps_literal(adb_api)};"
            f"$adbUsbApiSig=Get-AuthenticodeSignature -LiteralPath {_ps_literal(adb_usb_api)};"
            f"$mqdhHash=Get-FileHash -Algorithm SHA256 -LiteralPath {_ps_literal(mqdh_exe)};"
            f"$hash=Get-FileHash -Algorithm SHA256 -LiteralPath {_ps_literal(casting_exe)};"
            f"$adbHash=Get-FileHash -Algorithm SHA256 -LiteralPath {_ps_literal(adb_exe)};"
            f"$adbApiHash=Get-FileHash -Algorithm SHA256 -LiteralPath {_ps_literal(adb_api)};"
            f"$adbUsbApiHash=Get-FileHash -Algorithm SHA256 -LiteralPath {_ps_literal(adb_usb_api)};"
            "[pscustomobject]@{"
            "mqdh_version=[string]$mqdh.VersionInfo.FileVersion;"
            "mqdh_sha256=[string]$mqdhHash.Hash;"
            "mqdh_signature_status=[string]$mqdhSig.Status;"
            "mqdh_signer_subject=[string]$mqdhSig.SignerCertificate.Subject;"
            "mqdh_signer_thumbprint=[string]$mqdhSig.SignerCertificate.Thumbprint;"
            "casting_is_reparse_point=[bool]($casting.Attributes -band "
            "[IO.FileAttributes]::ReparsePoint);"
            "adb_is_reparse_point=[bool]($adb.Attributes -band "
            "[IO.FileAttributes]::ReparsePoint);"
            "adb_dependency_is_reparse_point=[bool](($adbApi.Attributes -band "
            "[IO.FileAttributes]::ReparsePoint) -or ($adbUsbApi.Attributes -band "
            "[IO.FileAttributes]::ReparsePoint));"
            "install_path_has_reparse_component=[bool]("
            "(Test-ReparseAncestry $mqdh.FullName) -or "
            "(Test-ReparseAncestry $casting.FullName) -or "
            "(Test-ReparseAncestry $adb.FullName) -or "
            "(Test-ReparseAncestry $adbApi.FullName) -or "
            "(Test-ReparseAncestry $adbUsbApi.FullName));"
            "casting_sha256=[string]$hash.Hash;"
            "signature_status=[string]$sig.Status;"
            "signer_subject=[string]$sig.SignerCertificate.Subject;"
            "signer_thumbprint=[string]$sig.SignerCertificate.Thumbprint;"
            "adb_sha256=[string]$adbHash.Hash;"
            "adb_api_sha256=[string]$adbApiHash.Hash;"
            "adb_usb_api_sha256=[string]$adbUsbApiHash.Hash;"
            "adb_signature_status=[string]$adbSig.Status;"
            "adb_api_signature_status=[string]$adbApiSig.Status;"
            "adb_usb_api_signature_status=[string]$adbUsbApiSig.Status;"
            "adb_signer_subject=[string]$adbSig.SignerCertificate.Subject;"
            "adb_signer_thumbprint=[string]$adbSig.SignerCertificate.Thumbprint;"
            "adb_api_signer_thumbprint=[string]$adbApiSig.SignerCertificate.Thumbprint;"
            "adb_usb_api_signer_thumbprint=[string]$adbUsbApiSig.SignerCertificate.Thumbprint"
            "}|ConvertTo-Json -Compress"
        )
        observation.update(_powershell_json(script))
        return observation

    @staticmethod
    def adb_server_running() -> bool:
        try:
            with socket.create_connection(("127.0.0.1", 5037), timeout=0.25):
                return True
        except OSError:
            return False

    @staticmethod
    def run_adb(
        adb_exe: str,
        arguments: list[str],
        *,
        timeout_seconds: float = 15.0,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [adb_exe, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

    @staticmethod
    def list_casting_processes() -> list[dict[str, Any]]:
        script = (
            "$ErrorActionPreference='Stop';"
            "$rows=@(Get-CimInstance Win32_Process -Filter \"Name='Casting.exe'\" | "
            "ForEach-Object {"
            "$p=Get-Process -Id $_.ProcessId -ErrorAction Stop;"
            "[pscustomobject]@{"
            "pid=[int]$_.ProcessId;"
            "executable_path=[string]$_.ExecutablePath;"
            "creation_time_utc=$p.StartTime.ToUniversalTime().ToString('o');"
            "main_window_handle=[int64]$p.MainWindowHandle;"
            "main_window_title=[string]$p.MainWindowTitle;"
            "command_line=[string]$_.CommandLine"
            "}});"
            "$rows|ConvertTo-Json -Compress"
        )
        payload = _powershell_json(script)
        if payload is None:
            return []
        return payload if isinstance(payload, list) else [payload]

    @staticmethod
    def inspect_process(pid: int) -> dict[str, Any] | None:
        script = (
            "$ErrorActionPreference='Stop';"
            f"$cim=Get-CimInstance Win32_Process -Filter \"ProcessId={int(pid)}\";"
            "if($null -eq $cim){'null';exit 0};"
            f"$p=Get-Process -Id {int(pid)} -ErrorAction Stop;"
            "[pscustomobject]@{"
            "pid=[int]$cim.ProcessId;"
            "executable_path=[string]$cim.ExecutablePath;"
            "creation_time_utc=$p.StartTime.ToUniversalTime().ToString('o');"
            "main_window_handle=[int64]$p.MainWindowHandle;"
            "main_window_title=[string]$p.MainWindowTitle;"
            "command_line=[string]$cim.CommandLine"
            "}|ConvertTo-Json -Compress"
        )
        return _powershell_json(script)

    @staticmethod
    def launch_casting(
        executable: str,
        arguments: list[str],
        *,
        working_directory: str,
        stdout_path: str,
        stderr_path: str,
    ) -> dict[str, Any]:
        stdout_file = Path(stdout_path)
        stderr_file = Path(stderr_path)
        stdout_file.parent.mkdir(parents=True, exist_ok=True)
        stderr_file.parent.mkdir(parents=True, exist_ok=True)
        with stdout_file.open("ab", buffering=0) as stdout_handle, stderr_file.open(
            "ab", buffering=0
        ) as stderr_handle:
            process = subprocess.Popen(
                [executable, *arguments],
                cwd=working_directory,
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                shell=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            identity = WindowsMetaQuestCastingAdapter.inspect_process(
                int(process.pid)
            )
            if identity is not None:
                observed_path = os.path.normcase(
                    os.path.abspath(str(identity.get("executable_path", "")))
                )
                expected_path = os.path.normcase(os.path.abspath(executable))
                if observed_path != expected_path:
                    raise RuntimeError(
                        "Launched Casting process path did not match the reviewed executable."
                    )
                return identity
            if process.poll() is not None:
                raise RuntimeError(
                    "Casting.exe exited before its exact process identity was observed."
                )
            time.sleep(0.05)
        raise RuntimeError(
            "Casting.exe process identity was not observable after launch."
        )

    @staticmethod
    def close_main_window_if_matches(
        pid: int,
        *,
        executable_path: str,
        creation_time_utc: str,
    ) -> dict[str, bool]:
        script = (
            "$ErrorActionPreference='Stop';"
            f"$cim=Get-CimInstance Win32_Process -Filter \"ProcessId={int(pid)}\";"
            "if($null -eq $cim){"
            "[pscustomobject]@{identity_matched=$false;close_requested=$false}"
            "|ConvertTo-Json -Compress;exit 0};"
            f"$p=Get-Process -Id {int(pid)} -ErrorAction Stop;"
            "$created=$p.StartTime.ToUniversalTime().ToString('o');"
            f"$pathMatches=[string]::Equals([string]$cim.ExecutablePath,"
            f"{_ps_literal(executable_path)},"
            "[StringComparison]::OrdinalIgnoreCase);"
            f"$timeMatches=[string]::Equals($created,{_ps_literal(creation_time_utc)},"
            "[StringComparison]::Ordinal);"
            "if(-not ($pathMatches -and $timeMatches)){"
            "[pscustomobject]@{identity_matched=$false;close_requested=$false}"
            "|ConvertTo-Json -Compress;exit 0};"
            "$closed=$p.CloseMainWindow();"
            "[pscustomobject]@{identity_matched=$true;close_requested=[bool]$closed}"
            "|ConvertTo-Json -Compress"
        )
        payload = _powershell_json(script)
        return {
            "identity_matched": bool(
                payload and payload.get("identity_matched")
            ),
            "close_requested": bool(
                payload and payload.get("close_requested")
            ),
        }
