"""Real Windows namespace/child tests for the generic explicit input binder."""
import hashlib
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.hostessctl.immutable_input_binding import WindowsInputBinding


@unittest.skipUnless(os.name == "nt", "Windows sharing semantics")
class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.parent = self.root/"inputs"
        self.parent.mkdir()
        self.file = self.parent/"input.dat"
        self.file.write_bytes(b"complete selected bytes")
        self.binding = WindowsInputBinding.from_pins([
            {"path": str(self.file), "sha256": hashlib.sha256(self.file.read_bytes()).hexdigest()}])
        self.addCleanup(self.binding.close)

    def test_real_write_delete_replace_and_parent_rename_denied_then_released(self):
        replacement = self.root/"replacement"
        replacement.write_bytes(b"other")
        for action in (lambda: self.file.write_bytes(b"overwrite"), self.file.unlink,
                       lambda: os.replace(replacement, self.file),
                       lambda: self.parent.rename(self.root/"moved")):
            with self.subTest(action=action), self.assertRaises(OSError):
                action()
        self.binding.assert_current()
        self.binding.close()
        self.file.write_bytes(b"after release")
        self.parent.rename(self.root/"moved")
        self.assertTrue(self.binding.report()["released"])

    def test_fresh_real_child_host_arguments_selected_remote_arguments_preserved(self):
        script = self.parent/"peer.py"
        script.write_text("import json,sys; print(json.dumps(sys.argv[1:]))")
        self.binding.add(sys.executable)
        self.binding.add(script)
        remote = ["/proc/41/stat", "/sdcard/Android/data/example/files/a", "content://example.probe", "/arbitrary/remote"]
        argv = self.binding.argv([sys.executable, str(script), *remote], inputs=(0, 1))
        self.binding.assert_current()
        process = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(process.stdout), remote)
        self.assertEqual(argv[2:], remote)
        self.assertTrue(all(a.startswith("\\\\?\\") for a in argv[:2]))
        with self.assertRaises(ValueError):
            self.binding.path(remote[0])
        with self.assertRaises(ValueError):
            self.binding.output_path(str(self.root/"unselected-output"))

    def test_explicit_output_root_fresh_child_and_no_repeat_hashes(self):
        self.binding.add(sys.executable)
        script = self.parent/"write.py"
        script.write_text("import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('actual child')")
        self.binding.add(script)
        output = self.root/"output"
        output.mkdir()
        self.binding.declare_output_root(output)
        before = self.binding.report()
        for index in range(2):
            self.binding.assert_current()
            subprocess.run(self.binding.argv([sys.executable, str(script), str(output/str(index))],
                                            inputs=(0, 1), outputs=(2,)), check=True)
        self.assertEqual((output/"1").read_text(), "actual child")
        self.assertEqual(self.binding.report()["bytes_hashed"], before["bytes_hashed"])
        self.assertEqual(self.binding.report()["hash_reads"], before["hash_reads"])

    def test_incorrect_pin_and_partial_constructor_release_every_acquired_handle(self):
        other = self.root/"other"
        other.write_bytes(b"other")
        with self.assertRaises(ValueError):
            WindowsInputBinding.from_pins([{"path": str(other), "sha256": "0"*64}])
        other.write_bytes(b"released after failed qualification")

    def test_close_continues_after_failure_and_same_owner_can_complete_release(self):
        row = self.binding.files[self.binding.key(self.file)]
        original = row["stream"]
        class FailsOnce:
            def close(wrapper):
                row["stream"] = original
                raise OSError("injected close failure")
        row["stream"] = FailsOnce()
        with self.assertRaisesRegex(OSError, "release_incomplete") as caught:
            self.binding.close()
        self.assertIs(caught.exception.immutable_input_binding, self.binding)
        self.assertEqual(len(self.binding.directories), 0)
        self.assertFalse(self.binding.report()["released"])
        self.binding.close()
        self.file.write_bytes(b"after same-owner release")

    def test_probe_close_failure_retains_exact_handle_for_same_owner_release(self):
        with patch.object(self.binding.kernel, "CloseHandle", return_value=False):
            with self.assertRaises(OSError) as caught:
                self.binding.assert_current()
        self.assertIs(caught.exception.immutable_input_binding, self.binding)
        self.assertEqual(self.binding.report()["pending_probes"], 1)
        self.binding.close()
        self.assertTrue(self.binding.report()["released"])

    def test_file_probe_close_failure_keeps_the_actual_stream_reachable(self):
        original_open = self.binding._open
        actual = []
        def open_probe(path, directory=False):
            row = original_open(path, directory)
            if not directory:
                stream = row["stream"]
                actual.append(stream)
                class FailsClose:
                    def close(wrapper):
                        row["stream"] = stream
                        raise OSError("probe stream close")
                row["stream"] = FailsClose()
            return row
        with patch.object(self.binding, "_open", side_effect=open_probe):
            with self.assertRaises(OSError):
                self.binding.assert_current()
        self.assertEqual(len(actual), 1)
        self.assertFalse(actual[0].closed)
        self.assertEqual(self.binding.report()["pending_probes"], 1)
        self.binding.close()
        self.assertTrue(actual[0].closed)
        self.assertTrue(self.binding.report()["released"])

    def test_open_qualification_and_close_failure_retain_original_native_handle(self):
        with patch.object(self.binding, "_info", side_effect=ValueError("qualification failure")), \
                patch.object(self.binding.kernel, "CloseHandle", return_value=False):
            with self.assertRaises(ValueError) as caught:
                self.binding._open(self.file)
        self.assertIs(caught.exception.immutable_input_binding, self.binding)
        self.assertEqual(self.binding.report()["pending_probes"], 1)
        self.binding.close()
        self.assertTrue(self.binding.report()["released"])

    def test_preexisting_native_writable_mapped_view_refuses_binding(self):
        from ctypes import wintypes as w
        path = self.root/"mapped"
        path.write_bytes(b"original bytes")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
        kernel.CreateFileW.restype = w.HANDLE
        kernel.CreateFileMappingW.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD, w.DWORD, w.DWORD, w.LPCWSTR]
        kernel.CreateFileMappingW.restype = w.HANDLE
        kernel.MapViewOfFile.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, ctypes.c_size_t]
        kernel.MapViewOfFile.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [w.HANDLE]
        kernel.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        file = kernel.CreateFileW(str(path), 0xc0000000, 7, None, 3, 0, None)
        self.assertNotEqual(file, ctypes.c_void_p(-1).value)
        try:
            section = kernel.CreateFileMappingW(file, None, 4, 0, 0, None)
            self.assertTrue(section)
            try:
                view = kernel.MapViewOfFile(section, 2, 0, 0, 0)
                self.assertTrue(view)
            finally:
                kernel.CloseHandle(section)
        finally:
            kernel.CloseHandle(file)
        try:
            with self.assertRaises(PermissionError):
                WindowsInputBinding.from_pins([{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}])
        finally:
            self.assertTrue(kernel.UnmapViewOfFile(view))
        path.write_bytes(b"mapped view closed")

    def test_reparse_input_and_junction_namespace_refused(self):
        junction = self.root/"junction"
        created = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(self.parent)], capture_output=True)
        self.assertEqual(created.returncode, 0, created.stderr)
        try:
            with self.assertRaisesRegex(ValueError, "reparse"):
                WindowsInputBinding.from_pins([{"path": str(junction/self.file.name),
                                               "sha256": hashlib.sha256(self.file.read_bytes()).hexdigest()}])
        finally:
            os.rmdir(junction)

    def test_dependency_inventory_is_generic_explicit_and_current(self):
        inventory = self.binding.dependency_pins()
        self.assertEqual(len(inventory["files"]), 1)
        for row in inventory["files"]:
            self.assertEqual(hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest(), row["sha256"])
        selected = self.binding.inventory()["inputs"]
        self.binding.close()
        self.assertEqual(self.binding.inventory()["inputs"], selected)


if __name__ == "__main__":
    unittest.main()
