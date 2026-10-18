"""One retained Windows input/namespace binding, never a TTL or path cache.

Files and all logical/volume-path ancestor directories deny write/delete
sharing. Children receive protected DOS paths for explicitly selected inputs. The held
objects and path joins stay alive until the original owner releases them.
"""
from copy import deepcopy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re


class WindowsInputBinding:
    @classmethod
    def from_pins(cls, pins):
        """Bind an explicit complete caller-selected path/hash closure.

        This is byte/namespace proof, not execution authorization. The caller
        keeps actor/lifecycle/effect guards and owns the same returned object.
        """
        binding = cls()
        try:
            if type(pins) is not list or not pins:
                raise ValueError("explicit_input_pin_closure_required")
            seen = set()
            for pin in pins:
                if (type(pin) is not dict or set(pin) != {"path", "sha256"} or
                        type(pin["path"]) is not str or not os.path.isabs(pin["path"]) or
                        type(pin["sha256"]) is not str or not re.fullmatch("[0-9a-f]{64}", pin["sha256"])):
                    raise ValueError("explicit_input_pin_required")
                key = binding.key(pin["path"])
                if key in seen or binding.sha_file(pin["path"]) != pin["sha256"]:
                    raise ValueError("input_pin_duplicate_or_changed")
                seen.add(key)
            binding.assert_current()
            return binding
        except BaseException as error:
            try:
                binding.close()
            except OSError:
                error.immutable_input_binding = binding
            raise

    def __init__(self):
        if os.name != "nt":
            raise ValueError("windows_immutable_binding_unavailable")
        from ctypes import wintypes as w
        class FileInfo(ctypes.Structure):
            _fields_ = [("attributes", w.DWORD), ("created", w.FILETIME), ("accessed", w.FILETIME),
                        ("written", w.FILETIME), ("volume", w.DWORD), ("size_high", w.DWORD),
                        ("size_low", w.DWORD), ("links", w.DWORD), ("index_high", w.DWORD), ("index_low", w.DWORD)]
        self.info_type = FileInfo
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
        self.kernel.CreateFileW.restype = w.HANDLE
        self.kernel.GetFileInformationByHandle.argtypes = [w.HANDLE, ctypes.POINTER(FileInfo)]
        self.kernel.GetFileInformationByHandle.restype = w.BOOL
        self.kernel.GetFinalPathNameByHandleW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD]
        self.kernel.GetFinalPathNameByHandleW.restype = w.DWORD
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CloseHandle.restype = w.BOOL
        self.files, self.directories, self.documents, self.output_roots, self.pins = {}, {}, {}, {}, {}
        self.probes = {}
        self.closing = False
        self.hash_reads = self.bytes_hashed = self.admissions = 0

    @staticmethod
    def key(path):
        # GetFullPathName normalization must not silently select a different
        # object before the native ordinary-name proof can reject it.
        if os.fspath(path).startswith("\\\\?\\"):
            return os.path.normcase(os.fspath(path))
        return os.path.normcase(os.path.abspath(path))

    def _info(self, handle):
        value = self.info_type()
        if not self.kernel.GetFileInformationByHandle(handle, ctypes.byref(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        if value.attributes & 0x400:
            raise ValueError("immutable_reparse_object_refused")
        return (value.volume, value.index_high, value.index_low), (value.size_high << 32) | value.size_low

    def _volume_path(self, handle):
        buffer = ctypes.create_unicode_buffer(32768)
        size = self.kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 1)  # VOLUME_NAME_GUID
        if not 0 < size < len(buffer) or not buffer.value.startswith("\\\\?\\Volume{"):
            raise ValueError("stable_local_volume_path_required")
        return buffer.value

    def _launch_path(self, handle, identity, stable):
        # CreateProcess rejects volume-GUID executable names. Obtain the final
        # local DOS name from the SAME held object; its complete namespace is
        # also held below. UNC/network inputs are unsupported in this mode.
        buffer = ctypes.create_unicode_buffer(32768)
        size = self.kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        if not 0 < size < len(buffer) or not re.match(r"^\\\\\?\\[A-Za-z]:\\", buffer.value):
            raise ValueError("local_dos_launch_namespace_required")
        # PowerShell's AuthorizationManager rejects extended \\?\ script
        # names even when the exact same local script is accepted normally.
        # Keep the canonical DOS name protected, without bypassing host policy.
        launch = buffer.value[4:]
        # Removing the extended prefix changes Win32 normalization (for example
        # trailing dots/spaces). Prove the ordinary child name selects exactly
        # the same object AND volume path; never assume spellings are equivalent.
        probe = self.kernel.CreateFileW(launch, 0x80, 1, None, 3, 0x02000000 | 0x00200000, None)
        if probe == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if self._info(probe)[0] != identity or self._volume_path(probe) != stable:
                raise ValueError("normal_dos_namespace_does_not_bind_selected_object")
        finally:
            if not self.kernel.CloseHandle(probe):
                self.probes[probe] = {"handle": probe, "path": launch}
                error = ctypes.WinError(ctypes.get_last_error())
                error.immutable_input_binding = self
                raise error
        return launch

    def _open(self, path, directory=False):
        handle = self.kernel.CreateFileW(str(path), 0x80 if directory else 0x80000000,
                                         1, None, 3, 0x02000000 | 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            identity, size = self._info(handle)
            stable = self._volume_path(handle)
            launch = self._launch_path(handle, identity, stable)
            if directory:
                return {"handle": handle, "identity": identity, "path": str(path), "stable": stable, "launch": launch}
            import msvcrt
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            try:
                stream = os.fdopen(descriptor, "rb")
            except BaseException:
                os.close(descriptor)
                handle = None
                raise
            return {"handle": handle, "stream": stream, "identity": identity, "size": size,
                    "path": str(path), "stable": stable, "launch": launch}
        except BaseException as error:
            if handle is not None and not self.kernel.CloseHandle(handle):
                self.probes[handle] = {"handle": handle, "path": str(path)}
                error.immutable_input_binding = self
            raise

    def _directory(self, path):
        key = self.key(path)
        if key not in self.directories:
            row = self._open(key, directory=True)
            self.directories[key] = row
        return self.directories[key]

    def protect_directory(self, path):
        if self.closing:
            raise ValueError("input_binding_closed")
        path = Path(self.key(path))
        for parent in reversed((path, *path.parents)):
            self._directory(parent)
        row = self._directory(path)
        # A SUBST drive can hide physical ancestors. Protect their actual
        # namespace too. The final DOS namespace is held as well because fresh
        # child processes require DOS executable paths rather than GUID paths.
        for name in (row["stable"], row["launch"]):
            physical = Path(name)
            for parent in reversed((physical, *physical.parents)):
                self._directory(parent)
        return row["launch"]

    def add(self, path, maximum=536870912):
        if self.closing:
            raise ValueError("input_binding_closed")
        key = self.key(path)
        if key not in self.files:
            self.protect_directory(Path(key).parent)
            row = self._open(key)
            self.files[key] = row  # Constructor cleanup retains every acquired handle.
            if not 0 < row["size"] <= maximum:
                raise ValueError("bounded_immutable_input_required")
            hasher = hashlib.sha256()
            while chunk := row["stream"].read(1048576):
                hasher.update(chunk)
                self.bytes_hashed += len(chunk)
            row["sha256"] = hasher.hexdigest()
            self.pins[key] = {"path": key, "sha256": row["sha256"], "bytes": row["size"],
                              "file_identity": list(row["identity"]), "launch_path": row["launch"],
                              "volume_path": row["stable"]}
            self.hash_reads += 1
        row = self.files[key]
        if row["size"] > maximum:
            raise ValueError("bounded_immutable_input_required")
        return row

    def sha_file(self, path):
        return self.add(path)["sha256"]

    def read_file(self, path, maximum=4194304):
        row = self.add(path, maximum)
        row["stream"].seek(0)
        data = row["stream"].read(maximum+1)
        if len(data) != row["size"]:
            raise ValueError("immutable_input_size_changed")
        return data

    def read_json(self, path):
        key = self.key(path)
        if key not in self.documents:
            def unique(pairs):
                result = {}
                for name, value in pairs:
                    if name in result:
                        raise ValueError("duplicate_json_key")
                    result[name] = value
                return result
            document = json.loads(self.read_file(path).decode("utf-8-sig"), object_pairs_hook=unique)
            if type(document) is not dict:
                raise ValueError("json_object_required")
            self.documents[key] = document
        return deepcopy(self.documents[key])

    def assert_current(self):
        if self.closing:
            raise ValueError("input_binding_closed")
        for row in [*self.directories.values(), *self.files.values()]:
            # Open the selected name again while ALL ancestors remain locked.
            # Identity is additional proof, not a replacement for namespace locks.
            probe = self._open(row["path"], directory="stream" not in row)
            try:
                if (probe["identity"] != row["identity"] or probe["stable"] != row["stable"] or
                        probe["launch"] != row["launch"]):
                    raise ValueError("immutable_input_path_identity_changed")
            finally:
                try:
                    if "stream" in probe:
                        probe["stream"].close()
                    elif not self.kernel.CloseHandle(probe["handle"]):
                        raise ctypes.WinError(ctypes.get_last_error())
                except OSError as error:
                    self.probes[probe["handle"]] = probe
                    error.immutable_input_binding = self
                    raise
        self.admissions += 1

    def path(self, value):
        """Map only one explicitly selected, already held HOST input."""
        key = self.key(value)
        if key in self.files:
            return self.files[key]["launch"]
        raise ValueError("selected_host_input_required")

    def declare_output_root(self, value):
        key = self.key(value)
        self.output_roots[key] = self.protect_directory(value)

    def output_path(self, value):
        # Only an explicitly declared owner output root may supply a namespace;
        # held C:/ and S:/ ancestors never make arbitrary arguments host paths.
        key = self.key(value)
        path = Path(key)
        for root, launch in self.output_roots.items():
            if path.is_relative_to(root):
                return str(Path(launch)/path.relative_to(root))
        raise ValueError("declared_host_output_required")

    def argv(self, values, *, inputs=(0,), outputs=()):
        """Rewrite selected host argument POSITIONS, never arbitrary spelling."""
        result = list(values)
        if set(inputs) & set(outputs) or any(type(i) is not int or not 0 <= i < len(result) for i in (*inputs, *outputs)):
            raise ValueError("explicit_host_argument_positions_required")
        for index in inputs:
            result[index] = self.path(result[index])
        for index in outputs:
            result[index] = self.output_path(result[index])
        return result

    @staticmethod
    def dependency_pins():
        path = Path(__file__).resolve()
        return {"schema": "rusty.hostess.immutable_input_binding.dependencies.v1", "runtime": "Python stdlib; Windows kernel32",
                "files": [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]}

    def report(self):
        return {"mode": "windows-immutable", "files": len(self.files), "namespace_directories": len(self.directories),
                "hash_reads": self.hash_reads, "bytes_hashed": self.bytes_hashed, "admissions": self.admissions,
                "pending_probes": len(self.probes), "released": not self.files and not self.directories and not self.probes}

    def inventory(self):
        """Retained byte/object evidence survives successful handle release."""
        return {"schema": "rusty.hostess.immutable_input_binding.inventory.v1",
                "inputs": deepcopy(list(self.pins.values())), "dependencies": self.dependency_pins(),
                "scope": "selected-files-and-held-namespace-not-all-runtime-or-OS-dependencies"}

    def close(self):
        self.closing = True
        failures = []
        for collection in (self.probes, self.files, self.directories):
            for key, row in reversed(list(collection.items())):
                try:
                    if "stream" in row:
                        row["stream"].close()
                    elif not self.kernel.CloseHandle(row["handle"]):
                        raise ctypes.WinError(ctypes.get_last_error())
                    del collection[key]
                except OSError as error:
                    failures.append(error)
        if failures:
            error = OSError("input_binding_release_incomplete")
            error.immutable_input_binding = self
            raise error from failures[0]
